from enum import Enum
import hashlib
import re
from typing import Dict, List, Optional
from agents.VerificationAgent import VerificationAgent, VerificationDecision
from storage.repositories.query_session_repo import QuerySessionRepository
from storage.repositories.planner_trace_repo import PlannerTraceRepository
from storage.repositories.search_log_repo import SearchLogRepository
from storage.repositories.answer_repo import AnswerSnapshotRepository
from storage.repositories.query_cache_repo import QueryCacheRepository
from sqlalchemy.orm import Session
from storage.repositories.evidence_repo import EvidenceRepository



class PlannerState(Enum):
    INIT = "INIT"
    RESEARCH = "RESEARCH"
    VERIFY = "VERIFY"
    SYNTHESIZE = "SYNTHESIZE"
    DONE = "DONE"
    FAILED = "FAILED"


class SearchStrategy(Enum):
    BASE = "BASE"
    BROADEN_QUERY = "BROADEN_QUERY"
    AUTHORITATIVE_SITES = "AUTHORITATIVE_SITES"
    RESEARCH_FOCUSED = "RESEARCH_FOCUSED"

class PlannerContext:
    """
    Tracks planner execution state and history.
    Budget constraints removed for unlimited research capability.
    """

    def __init__(self, max_attempts: int = 10):
        self.current_state: PlannerState = PlannerState.INIT
        self.attempt_count: int = 0
        self.max_attempts: int = max_attempts  # Increased from 3 to 10

        self.confidence_history: List[str] = []
        self.decision_history: List[str] = []

        self.strategy_history: List[SearchStrategy] = []
        self.current_strategy: SearchStrategy = SearchStrategy.BASE

        self.last_confidence: Optional[str] = None
       

        

        self.final_result: Optional[Dict] = None
        self.no_progress_count: int = 0
        self.last_decision: Optional[str] = None

        self.num_docs: int = 10  # Increased from 5 to 10
        self.max_docs: int = 50  # Increased from 20 to 50
        self.search_count: int = 0
        self.max_searches: int = 50  # Increased from 5 to 50 (effectively unlimited)
        self.budget_exhausted_reason: Optional[str] = None


    def record_confidence(self, confidence: str):
        self.confidence_history.append(confidence)

        

        

    def record_decision(self, decision: str):
        self.decision_history.append(decision)

    def record_strategy(self, strategy: SearchStrategy):
        self.strategy_history.append(strategy)
        self.current_strategy = strategy

    def record_progress(self, confidence: str, decision: str):
        if (
            confidence == self.last_confidence
            and decision == self.last_decision
        ):
            self.no_progress_count += 1
        else:
            self.no_progress_count = 0

        self.last_confidence = confidence
        self.last_decision = decision


class PlannerAgent:
    STRATEGY_ORDER = [
        SearchStrategy.BASE,
        SearchStrategy.BROADEN_QUERY,
        SearchStrategy.AUTHORITATIVE_SITES,
        SearchStrategy.RESEARCH_FOCUSED,
]

  

    def __init__(
        self,
        research_agent,
        verification_agent: VerificationAgent,
        db: Optional[Session] = None,
        max_attempts: int = 3
    ):
        self.research_agent = research_agent
        self.verification_agent = verification_agent
        self.db = db

        self.query_repo = QuerySessionRepository
        self.trace_repo = PlannerTraceRepository
        self.search_repo = SearchLogRepository
        self.answer_repo = AnswerSnapshotRepository
        self.cache_repo = QueryCacheRepository
        self.context = PlannerContext(max_attempts=max_attempts)
        self.evidence_repo = EvidenceRepository
        self.session_id = None
        self._research_result: Optional[Dict] = None
        self._last_query_hash: Optional[str] = None

    def _compute_query_hash(self, question: str, strategy: str, num_docs: int) -> str:
        normalized_question = re.sub(r"\s+", " ", question.strip().lower())
        key = f"{normalized_question}|{strategy}|{num_docs}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def run(self, question: str) -> Dict:
        while True:
            if self.context.current_state == PlannerState.INIT:
                self._handle_init(question)

            elif self.context.current_state == PlannerState.RESEARCH:
                self._handle_research(question)

            elif self.context.current_state == PlannerState.VERIFY:
                self._handle_verify(question)

            elif self.context.current_state == PlannerState.SYNTHESIZE:
                self._handle_synthesize()

            elif self.context.current_state == PlannerState.DONE:
                return self.context.final_result

            elif self.context.current_state == PlannerState.FAILED:

                # 🔹 Persist partial evidence if available
                if (
                    self.db is not None
                    and self.session_id is not None
                    and self._research_result
                    and "evidence" in self._research_result
                ):
                    self.evidence_repo.bulk_create(
                        db=self.db,
                        session_id=self.session_id,
                        evidence_items=self._research_result["evidence"],
                    )

                if self.db is not None and self.session_id is not None:
                    self.query_repo.update_final_status(
                        db=self.db,
                        session_id=self.session_id,
                        status="FAILED",
                        confidence_level="LOW",
                        confidence_reason=self.context.budget_exhausted_reason
                            or "Planner terminated execution safely."
                        )

                return {
                    "answer": "The system could not confidently answer the question.",
                    "confidence_level": "LOW",
                    "confidence_reason": "Planner stopped after repeated unsuccessful attempts.",
                    "evidence": (self._research_result or {}).get("evidence", []),
                    "notes": self.context.budget_exhausted_reason or "Planner stopped safely."
                }
    def _handle_init(self, question: str):
        # If API already created a QuerySession, reuse it.
        if self.db is not None and self.session_id is None:
            session = self.query_repo.create(
                db=self.db,
                question=question
            )
            self.session_id = session.id
        self.context.attempt_count = 1
        self.context.current_strategy = SearchStrategy.BASE
        self.context.current_state = PlannerState.RESEARCH
        if self.db is not None and self.session_id is not None:
            self.query_repo.update_status(
                db=self.db,
                session_id=self.session_id,
                status=PlannerState.RESEARCH.value,
            )

    def _handle_research(self, question: str):
        if self.db is not None and self.session_id is not None:
            self.query_repo.update_status(
                db=self.db,
                session_id=self.session_id,
                status=PlannerState.RESEARCH.value,
            )
        self._last_query_hash = self._compute_query_hash(
            question=question,
            strategy=self.context.current_strategy.value,
            num_docs=self.context.num_docs,
        )

        # Cache lookup happens only on retries (not first attempt)
        if self.db is not None and self.context.attempt_count > 1:
            cache = self.cache_repo.get_valid(
                db=self.db,
                query_hash=self._last_query_hash,
            )
            if cache is not None:
                cached_snapshot = self.answer_repo.get_latest_by_session(
                    db=self.db,
                    session_id=cache.session_id,
                )
                if cached_snapshot is not None:
                    cached_evidence = self.evidence_repo.list_by_session(
                        db=self.db,
                        session_id=cache.session_id,
                    )
                    self._research_result = {
                        "answer": cached_snapshot.answer_text,
                        "confidence_level": cached_snapshot.confidence_level,
                        "confidence_reason": cached_snapshot.confidence_reason,
                        "evidence": [
                            {
                                "claim": ev.claim_text,
                                "status": ev.verification_status,
                                "sources": ev.source_urls,
                            }
                            for ev in cached_evidence
                        ],
                    }
                    self.context.current_state = PlannerState.VERIFY
                    if self.db is not None and self.session_id is not None:
                        self.query_repo.update_status(
                            db=self.db,
                            session_id=self.session_id,
                            status=PlannerState.VERIFY.value,
                        )
                    return

        # No cache hit -> proceed with normal research
        self.context.search_count += 1
        # Budget check removed - allow unlimited searches
        
        query_used = self._modify_query(question)
        

        self._research_result = self.research_agent.research(
            question=query_used,        
            num_docs=self.context.num_docs
    )  
        if self.db is not None and self.session_id is not None:
            self.search_repo.log(
                db=self.db,
                session_id=self.session_id,
                attempt_number=self.context.attempt_count,
                query_used=query_used,
                num_docs=self.context.num_docs,
                success=True
            )
        self.context.current_state = PlannerState.VERIFY
        if self.db is not None and self.session_id is not None:
            self.query_repo.update_status(
                db=self.db,
                session_id=self.session_id,
                status=PlannerState.VERIFY.value,
            )


    # VERIFY → SYNTHESIZE
    def _handle_verify(self, question: str):
        if self.db is not None and self.session_id is not None:
            self.query_repo.update_status(
                db=self.db,
                session_id=self.session_id,
                status=PlannerState.VERIFY.value,
            )
        confidence_level = self._research_result.get("confidence_level", "LOW")
        confidence_reason = self._research_result.get("confidence_reason", "")

        self.context.record_confidence(confidence_level)

        decision = self.verification_agent.decide(
            verified_claims=self._research_result.get("evidence", []),
            confidence={
                "confidence_level": confidence_level,
                "confidence_reason": confidence_reason,
            },
            attempt=self.context.attempt_count,
            max_attempts=self.context.max_attempts
        )
        if self.db is not None and self.session_id is not None:
            self.trace_repo.log(
                db=self.db,
                session_id=self.session_id,
                attempt_number=self.context.attempt_count,
                planner_state=self.context.current_state.value,
                verification_decision=decision["decision"],
                strategy_used=self.context.current_strategy.value,
                num_docs=self.context.num_docs,
                stop_reason=decision.get("reason")
            )

        self.context.record_decision(decision["decision"])
        self.context.record_progress(confidence_level, decision["decision"])


        # ACCEPT → SYNTHESIZE
        if decision["decision"] == VerificationDecision.ACCEPT:
            self.context.current_state = PlannerState.SYNTHESIZE
            if self.db is not None and self.session_id is not None:
                self.query_repo.update_status(
                    db=self.db,
                    session_id=self.session_id,
                    status=PlannerState.SYNTHESIZE.value,
                )
            return

        # STOP → SYNTHESIZE (low confidence)
        if decision["decision"] == VerificationDecision.STOP:
            self.context.current_state = PlannerState.SYNTHESIZE
            if self._research_result:
                self._research_result["notes"] = decision["reason"]
            if self.db is not None and self.session_id is not None:
                self.query_repo.update_status(
                    db=self.db,
                    session_id=self.session_id,
                    status=PlannerState.SYNTHESIZE.value,
                )
            return

        # RETRY → modify strategy and loop
        
        if decision["decision"] == VerificationDecision.RETRY:
            # Stop BEFORE incrementing so attempt_count reflects attempts actually executed.
            if self._should_stop():
                self.context.current_state = PlannerState.FAILED
                return

            self.context.attempt_count += 1

            # Escalate docs
            if self.context.num_docs < self.context.max_docs:
                self.context.num_docs = min(
                    self.context.num_docs * 2,
                    self.context.max_docs
                )
           
            self._update_strategy(confidence_reason, decision.get("recommendation"))
            self.context.current_state = PlannerState.RESEARCH
            if self.db is not None and self.session_id is not None:
                self.query_repo.update_status(
                    db=self.db,
                    session_id=self.session_id,
                    status=PlannerState.RESEARCH.value,
                )
            return
        


    #SYNTHESIZE → DONE
    def _handle_synthesize(self):
        result = self._research_result

        if self.db is not None and self.session_id is not None:
            self.query_repo.update_status(
                db=self.db,
                session_id=self.session_id,
                status=PlannerState.SYNTHESIZE.value,
            )

        if result is None:
            self.context.budget_exhausted_reason = "No research result available to synthesize."
            self.context.current_state = PlannerState.FAILED
            return

        if self.db is not None and self.session_id is not None:
            self.answer_repo.create(
                db=self.db,
                session_id=self.session_id,
                answer_text=result["answer"],
                confidence_level=result["confidence_level"],
                confidence_reason=result["confidence_reason"]
            )

        if self.db is not None and self.session_id is not None and result.get("evidence"):
            self.evidence_repo.bulk_create(
                db=self.db,
                session_id=self.session_id,
                evidence_items=result["evidence"],
            )

        if self.db is not None and self.session_id is not None:
            self.query_repo.update_final_status(
                db=self.db,
                session_id=self.session_id,
                status="DONE",
                confidence_level=result["confidence_level"],
                confidence_reason=result["confidence_reason"]
            )

        # Store cache only on ACCEPT (never on STOP)
        if (
            self.db is not None
            and self.session_id is not None
            and self.context.last_decision == VerificationDecision.ACCEPT
            and self._last_query_hash
        ):
            self.cache_repo.store(
                db=self.db,
                query_hash=self._last_query_hash,
                session_id=self.session_id,
                ttl_seconds=60 * 60 * 24,
            )

        self.context.final_result = self._research_result
        self.context.current_state = PlannerState.DONE

    def _update_strategy(
    self,
    confidence_reason: str,
    recommendation: Optional[str]
):
        used = set(self.context.strategy_history)

        #  Primary selection (intent-based)
        if "single source" in confidence_reason.lower():
            preferred = SearchStrategy.BROADEN_QUERY

        elif "conflict" in confidence_reason.lower():
            preferred = SearchStrategy.AUTHORITATIVE_SITES

        elif recommendation:
            preferred = SearchStrategy.RESEARCH_FOCUSED

        else:
            preferred = SearchStrategy.BROADEN_QUERY

        #  If preferred already used → rotate
        if preferred not in used:
            self.context.record_strategy(preferred)
            return

        #  Fallback: first unused strategy in order
        for strategy in self.STRATEGY_ORDER:
            if strategy not in used:
                self.context.record_strategy(strategy)
                return

        # All strategies exhausted → mark failure
        self.context.current_state = PlannerState.FAILED

    def _modify_query(self, question: str) -> str:
        strategy = self.context.current_strategy

        if strategy == SearchStrategy.BROADEN_QUERY:
            return f"{question} explanation overview"

        if strategy == SearchStrategy.AUTHORITATIVE_SITES:
            return f"{question} site:gov OR site:edu"

        if strategy == SearchStrategy.RESEARCH_FOCUSED:
            return f"{question} research report policy"

        return question
    
    def _should_stop(self) -> bool:
        # Only stop on max attempts or no progress - no search budget limit
        if self.context.attempt_count >= self.context.max_attempts:
            self.context.budget_exhausted_reason = "Maximum retry attempts reached."
            return True

        if self.context.no_progress_count >= 3:  # Increased from 2 to 3
            self.context.budget_exhausted_reason = "No progress across multiple attempts."
            return True

        return False



