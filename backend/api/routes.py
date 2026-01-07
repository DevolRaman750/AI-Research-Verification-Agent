from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Generator, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy.exc import OperationalError, SQLAlchemyError


def _validate_uuid(session_id: str) -> bool:
    """Validate that session_id is a valid UUID."""
    try:
        uuid.UUID(session_id)
        return True
    except (ValueError, AttributeError):
        return False
from sqlalchemy.orm import Session

# Allow existing modules to import using the historical layout (e.g. `verification.*`, `planner.*`)
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.api.schemas import (
    QueryResultResponse,
    QueryStatusResponse,
    QuerySubmitRequest,
    QuerySubmitResponse,
    QueryTraceResponse,
)
from backend.agents.VerificationAgent import VerificationAgent
from backend.agents.research_agent import ResearchAgent
from backend.confidence.confidence_scorer import ConfidenceScorer
from backend.environments.web.environment import WebEnvironment
from backend.environments.web.search import WebSearch
from backend.planner.planner_agent import PlannerAgent
from backend.storage.db import SessionLocal
from backend.storage.repositories.answer_repo import AnswerSnapshotRepository
from backend.storage.repositories.evidence_repo import EvidenceRepository
from backend.storage.repositories.planner_trace_repo import PlannerTraceRepository
from backend.storage.repositories.query_session_repo import QuerySessionRepository
from backend.storage.repositories.search_log_repo import SearchLogRepository
from backend.verification.claim_extractor import ClaimExtractor
from backend.verification.verifier import VerificationEngine
from backend.synthesis.answer_synthesizer import AnswerSynthesizer


router = APIRouter(prefix="/api")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _build_planner(db: Session) -> PlannerAgent:
    # Web search configuration
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY", "")
    endpoint = os.getenv("GOOGLE_SEARCH_ENDPOINT", "https://www.googleapis.com/customsearch/v1")
    cx = os.getenv("GOOGLE_SEARCH_CX", "")

    web_search = WebSearch(api_key=api_key, endpoint=endpoint, cx=cx)
    web_env = WebEnvironment(search_client=web_search)

    research_agent = ResearchAgent(
        web_environment=web_env,
        claim_extractor=ClaimExtractor(),
        verification_engine=VerificationEngine(),
        confidence_scorer=ConfidenceScorer(),
        answer_synthesizer=AnswerSynthesizer(),
    )

    verification_agent = VerificationAgent()

    return PlannerAgent(
        research_agent=research_agent,
        verification_agent=verification_agent,
        db=db,
    )


def _run_planner_background(session_id: str, question: str) -> None:
    db = SessionLocal()
    try:
        planner = _build_planner(db)
        planner.session_id = session_id
        planner.run(question)
    except Exception as exc:
        # Best-effort failure mark; no reasoning returned.
        try:
            QuerySessionRepository.update_final_status(
                db=db,
                session_id=session_id,
                status="FAILED",
                confidence_level="LOW",
                confidence_reason=f"Planner execution failed: {type(exc).__name__}",
            )
        except Exception:
            pass
    finally:
        db.close()


@router.post("/query", response_model=QuerySubmitResponse)
def submit_query(
    payload: QuerySubmitRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> QuerySubmitResponse:
    try:
        session = QuerySessionRepository.create(db=db, question=payload.question)
    except (OperationalError, SQLAlchemyError) as exc:
        # DB unavailable - rollback any partial transaction and return 503
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please retry later."
        )

    background_tasks.add_task(_run_planner_background, str(session.id), payload.question)

    return QuerySubmitResponse(session_id=session.id, status="PROCESSING")


@router.get("/query/{session_id}/status", response_model=QueryStatusResponse)
def poll_status(session_id: str, db: Session = Depends(get_db)) -> QueryStatusResponse:
    if not _validate_uuid(session_id):
        raise HTTPException(status_code=404, detail="Invalid session_id format")
    try:
        session = QuerySessionRepository.get(db=db, session_id=session_id)
    except (OperationalError, SQLAlchemyError):
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please retry later."
        )
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    return QueryStatusResponse(status=session.status)


@router.get("/query/{session_id}/result", response_model=QueryResultResponse)
def fetch_result(session_id: str, db: Session = Depends(get_db)) -> QueryResultResponse:
    if not _validate_uuid(session_id):
        raise HTTPException(status_code=404, detail="Invalid session_id format")
    try:
        session = QuerySessionRepository.get(db=db, session_id=session_id)
    except (OperationalError, SQLAlchemyError):
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please retry later."
        )
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    if session.status not in {"DONE", "FAILED"}:
        raise HTTPException(status_code=409, detail="Result not ready")

    snapshot = AnswerSnapshotRepository.get_latest_by_session(db=db, session_id=session_id)
    evidence_rows = EvidenceRepository.list_by_session(db=db, session_id=session_id)

    answer_text = snapshot.answer_text if snapshot is not None else ""
    confidence_level = (
        snapshot.confidence_level if snapshot is not None else (session.final_confidence_level or "LOW")
    )
    confidence_reason = (
        snapshot.confidence_reason if snapshot is not None else (session.final_confidence_reason or "")
    )

    evidence = [
        {
            "claim": ev.claim_text,
            "status": ev.verification_status,
            "sources": ev.source_urls,
        }
        for ev in evidence_rows
    ]

    notes: Optional[str] = None
    if session.status == "FAILED":
        notes = session.final_confidence_reason

    return QueryResultResponse(
        answer=answer_text,
        confidence_level=confidence_level,
        confidence_reason=confidence_reason,
        evidence=evidence,
        notes=notes,
    )


@router.get("/query/{session_id}/trace", response_model=QueryTraceResponse)
def fetch_trace(
    session_id: str,
    db: Session = Depends(get_db),
    x_internal_token: Optional[str] = Header(default=None, alias="X-Internal-Token"),
) -> QueryTraceResponse:
    required = os.getenv("INTERNAL_TRACE_TOKEN")
    if required and x_internal_token != required:
        raise HTTPException(status_code=403, detail="Forbidden")

    if not _validate_uuid(session_id):
        raise HTTPException(status_code=404, detail="Invalid session_id format")
    session = QuerySessionRepository.get(db=db, session_id=session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    traces = PlannerTraceRepository.list_by_session(db=db, session_id=session_id)
    logs = SearchLogRepository.list_by_session(db=db, session_id=session_id)

    # TEA-safe: return only decisions/metadata (no prompts, no hidden reasoning)
    planner_traces = [
        {
            "attempt_number": t.attempt_number,
            "planner_state": t.planner_state,
            "verification_decision": t.verification_decision,
            "strategy_used": t.strategy_used,
            "num_docs": t.num_docs,
            "created_at": getattr(t, "created_at", None),
        }
        for t in traces
    ]

    search_logs = [
        {
            "attempt_number": l.attempt_number,
            "query_used": l.query_used,
            "num_docs": l.num_docs,
            "success": l.success,
            "created_at": getattr(l, "created_at", None),
        }
        for l in logs
    ]

    return QueryTraceResponse(planner_traces=planner_traces, search_logs=search_logs)
