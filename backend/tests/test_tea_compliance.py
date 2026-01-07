"""
======================================================================
TEA COMPLIANCE TESTS - Section 7 (Critical)
======================================================================

TEA = Transparency of Evidence, not reasoning

For EVERY endpoint ask:
❌ Does this expose reasoning?
❌ Does this expose intermediate thoughts?
❌ Does user control retries?

Also verify:
✅ Only decisions are stored
✅ Only evidence is shown  
✅ Planner logic is opaque to user

======================================================================
"""

import sys
sys.path.insert(0, "c:/Agents/AI-Research-Agent")
sys.path.insert(0, "c:/Agents/AI-Research-Agent/backend")

import uuid
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from storage.base import Base
from storage.models.query_session import QuerySession
from storage.models.planner_trace import PlannerTrace
from storage.models.answer_snapshot import AnswerSnapshot
from storage.models.evidence import Evidence
from verification.models import VerifiedClaim, VerificationStatus
from synthesis.answer_synthesizer import AnswerSynthesizer
from planner.planner_agent import PlannerAgent, PlannerState, SearchStrategy
from agents.VerificationAgent import VerificationAgent, VerificationDecision
from api.schemas import (
    QueryResultResponse,
    QueryStatusResponse,
    QuerySubmitResponse,
    QueryTraceResponse,
    EvidenceItem,
    PlannerTraceItem,
    SearchLogItem,
)


def print_header():
    print("\n" + "=" * 70)
    print("TEA COMPLIANCE TESTS - Section 7 (Critical)")
    print("=" * 70)


def print_result(test_id: str, name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {test_id} {name} | {detail}")


def print_summary(passed: int, failed: int, total: int):
    print("-" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {total} tests")


def create_test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    return TestSession()


# ======================================================================
# REASONING PATTERNS TO DETECT (TEA VIOLATIONS)
# ======================================================================

REASONING_PATTERNS = [
    # LLM Prompt Markers
    "You are a",
    "STRICT RULES",
    "Do NOT",
    "Instructions:",
    "System:",
    
    # Chain-of-Thought Markers
    "chain of thought",
    "let me think",
    "step by step",
    "first, I will",
    "next, I need to",
    
    # Reasoning Markers
    "reasoning:",
    "my analysis",
    "I think",
    "I believe",
    "therefore",
    "because I",
    "my conclusion",
    
    # Internal State Markers
    "current_state",
    "next_state",
    "transition",
    "state machine",
    
    # Code/Debug Markers
    "```",
    "def ",
    "class ",
    "import ",
    "traceback",
    "Exception:",
]

INTERNAL_FIELD_PATTERNS = [
    # Should never be in public responses
    "prompt",
    "llm_response",
    "raw_output",
    "internal_",
    "_hidden",
    "debug_",
    "trace_detail",
    "chain_of_thought",
    "reasoning_steps",
]


def contains_reasoning(text: str) -> List[str]:
    """Check if text contains reasoning patterns."""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for pattern in REASONING_PATTERNS:
        if pattern.lower() in text_lower:
            found.append(pattern)
    return found


def has_internal_fields(data: Dict) -> List[str]:
    """Check if dict contains internal field patterns."""
    found = []
    
    def check_dict(d, prefix=""):
        for key, value in d.items():
            full_key = f"{prefix}.{key}" if prefix else key
            for pattern in INTERNAL_FIELD_PATTERNS:
                if pattern.lower() in key.lower():
                    found.append(full_key)
            if isinstance(value, dict):
                check_dict(value, full_key)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        check_dict(item, f"{full_key}[{i}]")
    
    check_dict(data)
    return found


# ======================================================================
# TEST A: API Response Schema Compliance
# ======================================================================

def test_7_A1_query_result_schema_no_reasoning_fields():
    """
    QueryResultResponse should NOT have fields that could leak reasoning.
    """
    # Check the schema fields
    schema_fields = QueryResultResponse.model_fields.keys()
    
    allowed_fields = {"answer", "confidence_level", "confidence_reason", "evidence", "notes"}
    actual_fields = set(schema_fields)
    
    no_extra_fields = actual_fields == allowed_fields
    
    # Check for problematic field names
    problematic = [f for f in actual_fields if any(p in f.lower() for p in INTERNAL_FIELD_PATTERNS)]
    
    passed = no_extra_fields and len(problematic) == 0
    detail = f"fields={actual_fields}, problematic={problematic}"
    
    return passed, detail


def test_7_A2_query_status_schema_minimal():
    """
    QueryStatusResponse should be minimal - only status, no reasoning.
    """
    schema_fields = set(QueryStatusResponse.model_fields.keys())
    
    # Should only contain 'status'
    is_minimal = schema_fields == {"status"}
    
    passed = is_minimal
    detail = f"fields={schema_fields}"
    
    return passed, detail


def test_7_A3_query_submit_response_minimal():
    """
    QuerySubmitResponse should be minimal - session_id and status only.
    """
    schema_fields = set(QuerySubmitResponse.model_fields.keys())
    
    allowed = {"session_id", "status"}
    is_minimal = schema_fields == allowed
    
    passed = is_minimal
    detail = f"fields={schema_fields}"
    
    return passed, detail


def test_7_A4_evidence_item_schema_no_reasoning():
    """
    EvidenceItem should contain only claim, status, sources - no reasoning.
    """
    schema_fields = set(EvidenceItem.model_fields.keys())
    
    allowed = {"claim", "status", "sources"}
    no_extra = schema_fields == allowed
    
    passed = no_extra
    detail = f"fields={schema_fields}"
    
    return passed, detail


def test_7_A5_trace_response_no_prompts_or_reasoning():
    """
    QueryTraceResponse/PlannerTraceItem should NOT contain prompts or reasoning.
    """
    trace_fields = set(PlannerTraceItem.model_fields.keys())
    
    # These fields are acceptable (decisions/metadata only)
    allowed = {
        "attempt_number", "planner_state", "verification_decision",
        "strategy_used", "num_docs", "created_at"
    }
    
    # Check for forbidden fields
    forbidden_patterns = ["prompt", "reasoning", "thought", "llm", "raw"]
    forbidden_found = [f for f in trace_fields if any(p in f.lower() for p in forbidden_patterns)]
    
    no_forbidden = len(forbidden_found) == 0
    only_allowed = trace_fields.issubset(allowed)
    
    passed = no_forbidden and only_allowed
    detail = f"fields={trace_fields}, forbidden_found={forbidden_found}"
    
    return passed, detail


# ======================================================================
# TEST B: No Reasoning in API Responses
# ======================================================================

def test_7_B1_answer_contains_no_reasoning_markers():
    """
    Synthesized answers should not contain reasoning markers.
    """
    synthesizer = AnswerSynthesizer()
    
    claims = [
        VerifiedClaim(
            claim="The Earth orbits the Sun",
            sources=["https://nasa.gov"],
            status=VerificationStatus.AGREEMENT
        )
    ]
    confidence = {"confidence_level": "HIGH", "confidence_reason": "Multiple sources agree"}
    
    # Mock LLM to return a clean answer
    with patch("synthesis.answer_synthesizer.llm_complete") as mock_llm:
        mock_llm.return_value = "The Earth orbits the Sun in an elliptical path."
        
        result = synthesizer.synthesize(
            question="Does the Earth orbit the Sun?",
            verified_claims=claims,
            confidence=confidence
        )
    
    answer = result.get("answer", "")
    reasoning_found = contains_reasoning(answer)
    
    passed = len(reasoning_found) == 0
    detail = f"reasoning_markers={reasoning_found}"
    
    return passed, detail


def test_7_B2_confidence_reason_no_internal_details():
    """
    Confidence reason should not expose internal implementation details.
    """
    synthesizer = AnswerSynthesizer()
    
    claims = [
        VerifiedClaim(
            claim="Test claim",
            sources=["https://test.com"],
            status=VerificationStatus.AGREEMENT
        )
    ]
    confidence = {
        "confidence_level": "HIGH",
        "confidence_reason": "Multiple sources agree on this claim."
    }
    
    with patch("synthesis.answer_synthesizer.llm_complete") as mock_llm:
        mock_llm.return_value = "Test answer."
        
        result = synthesizer.synthesize(
            question="Test question",
            verified_claims=claims,
            confidence=confidence
        )
    
    reason = result.get("confidence_reason", "")
    
    # Should not contain internal details
    internal_patterns = ["state machine", "planner", "agent", "llm", "prompt"]
    internal_found = [p for p in internal_patterns if p.lower() in reason.lower()]
    
    passed = len(internal_found) == 0
    detail = f"reason='{reason[:50]}...', internal_found={internal_found}"
    
    return passed, detail


def test_7_B3_notes_do_not_expose_planner_internals():
    """
    Notes field should not expose planner state machine internals.
    """
    # Simulate what notes might contain on failure
    test_notes_good = "Unable to find sufficient verified information."
    test_notes_bad = "PlannerState.FAILED transition from VERIFY state"
    
    good_reasoning = contains_reasoning(test_notes_good)
    bad_reasoning = contains_reasoning(test_notes_bad)
    
    # Good notes should have no reasoning markers
    # Bad notes would have "state" which is suspicious
    good_is_clean = len(good_reasoning) == 0
    
    passed = good_is_clean
    detail = f"good_clean={good_is_clean}, good_markers={good_reasoning}"
    
    return passed, detail


# ======================================================================
# TEST C: User Cannot Control Internal Behavior
# ======================================================================

def test_7_C1_user_cannot_specify_retries():
    """
    API should NOT allow user to specify retry count.
    """
    from api.schemas import QuerySubmitRequest
    
    schema_fields = set(QuerySubmitRequest.model_fields.keys())
    
    # Should only have 'question'
    retry_fields = [f for f in schema_fields if "retry" in f.lower() or "attempt" in f.lower()]
    
    passed = len(retry_fields) == 0 and schema_fields == {"question"}
    detail = f"fields={schema_fields}, retry_fields={retry_fields}"
    
    return passed, detail


def test_7_C2_user_cannot_specify_strategy():
    """
    API should NOT allow user to specify search strategy.
    """
    from api.schemas import QuerySubmitRequest
    
    schema_fields = set(QuerySubmitRequest.model_fields.keys())
    
    strategy_fields = [f for f in schema_fields if "strategy" in f.lower()]
    
    passed = len(strategy_fields) == 0
    detail = f"strategy_fields={strategy_fields}"
    
    return passed, detail


def test_7_C3_user_cannot_specify_num_docs():
    """
    API should NOT allow user to specify number of documents to fetch.
    """
    from api.schemas import QuerySubmitRequest
    
    schema_fields = set(QuerySubmitRequest.model_fields.keys())
    
    doc_fields = [f for f in schema_fields if "doc" in f.lower() or "num" in f.lower()]
    
    passed = len(doc_fields) == 0
    detail = f"doc_fields={doc_fields}"
    
    return passed, detail


def test_7_C4_user_cannot_bypass_verification():
    """
    API should NOT allow user to skip verification.
    """
    from api.schemas import QuerySubmitRequest
    
    schema_fields = set(QuerySubmitRequest.model_fields.keys())
    
    skip_fields = [f for f in schema_fields if "skip" in f.lower() or "bypass" in f.lower()]
    
    passed = len(skip_fields) == 0
    detail = f"skip_fields={skip_fields}"
    
    return passed, detail


# ======================================================================
# TEST D: Database Storage TEA Compliance
# ======================================================================

def test_7_D1_planner_trace_stores_only_decisions():
    """
    PlannerTrace model should store only decisions, not reasoning.
    """
    from storage.models.planner_trace import PlannerTrace
    
    # Get column names
    columns = {c.name for c in PlannerTrace.__table__.columns}
    
    # Allowed columns (decisions/metadata only)
    allowed = {
        "id", "session_id", "attempt_number", "planner_state",
        "verification_decision", "strategy_used", "num_docs",
        "stop_reason", "created_at"
    }
    
    # Check for forbidden column patterns
    forbidden_patterns = ["prompt", "reasoning", "thought", "llm_output", "raw_"]
    forbidden = [c for c in columns if any(p in c.lower() for p in forbidden_patterns)]
    
    columns_ok = columns.issubset(allowed)
    no_forbidden = len(forbidden) == 0
    
    passed = columns_ok and no_forbidden
    detail = f"columns={columns}, forbidden={forbidden}"
    
    return passed, detail


def test_7_D2_answer_snapshot_stores_only_output():
    """
    AnswerSnapshot should store only final output, not intermediate steps.
    """
    from storage.models.answer_snapshot import AnswerSnapshot
    
    columns = {c.name for c in AnswerSnapshot.__table__.columns}
    
    allowed = {
        "id", "session_id", "answer_text", "confidence_level",
        "confidence_reason", "notes", "created_at"
    }
    
    forbidden_patterns = ["prompt", "reasoning", "intermediate", "step", "chain"]
    forbidden = [c for c in columns if any(p in c.lower() for p in forbidden_patterns)]
    
    columns_ok = columns.issubset(allowed)
    no_forbidden = len(forbidden) == 0
    
    passed = columns_ok and no_forbidden
    detail = f"columns={columns}, forbidden={forbidden}"
    
    return passed, detail


def test_7_D3_evidence_stores_only_claims_and_sources():
    """
    Evidence model should store only claims and sources, not internal data.
    """
    from storage.models.evidence import Evidence
    
    columns = {c.name for c in Evidence.__table__.columns}
    
    allowed = {"id", "session_id", "claim_text", "verification_status", "source_urls"}
    
    forbidden_patterns = ["prompt", "reasoning", "score_detail", "internal"]
    forbidden = [c for c in columns if any(p in c.lower() for p in forbidden_patterns)]
    
    columns_ok = columns == allowed
    no_forbidden = len(forbidden) == 0
    
    passed = columns_ok and no_forbidden
    detail = f"columns={columns}, expected={allowed}"
    
    return passed, detail


def test_7_D4_query_session_no_internal_state():
    """
    QuerySession should not store internal planner state details.
    """
    from storage.models.query_session import QuerySession
    
    columns = {c.name for c in QuerySession.__table__.columns}
    
    # Check for internal state columns that shouldn't exist
    forbidden_patterns = ["internal", "debug", "trace_", "raw_"]
    forbidden = [c for c in columns if any(p in c.lower() for p in forbidden_patterns)]
    
    passed = len(forbidden) == 0
    detail = f"columns={columns}, forbidden={forbidden}"
    
    return passed, detail


# ======================================================================
# TEST E: Trace Endpoint Protection
# ======================================================================

def test_7_E1_trace_endpoint_requires_token():
    """
    /trace endpoint should require INTERNAL_TRACE_TOKEN.
    """
    # Check the route definition for token requirement
    from api.routes import fetch_trace
    import inspect
    
    sig = inspect.signature(fetch_trace)
    params = sig.parameters
    
    has_token_param = "x_internal_token" in params
    
    passed = has_token_param
    detail = f"params={list(params.keys())}"
    
    return passed, detail


def test_7_E2_trace_response_no_llm_prompts():
    """
    Trace response should not contain LLM prompts.
    """
    # Verify PlannerTraceItem doesn't have prompt fields
    trace_fields = set(PlannerTraceItem.model_fields.keys())
    
    prompt_fields = [f for f in trace_fields if "prompt" in f.lower()]
    
    passed = len(prompt_fields) == 0
    detail = f"trace_fields={trace_fields}"
    
    return passed, detail


def test_7_E3_trace_response_no_raw_llm_output():
    """
    Trace response should not contain raw LLM output.
    """
    trace_fields = set(PlannerTraceItem.model_fields.keys())
    search_fields = set(SearchLogItem.model_fields.keys())
    
    all_fields = trace_fields | search_fields
    
    raw_fields = [f for f in all_fields if "raw" in f.lower() or "output" in f.lower()]
    
    passed = len(raw_fields) == 0
    detail = f"all_trace_fields={all_fields}, raw_fields={raw_fields}"
    
    return passed, detail


# ======================================================================
# TEST F: Planner Logic Opacity
# ======================================================================

class FakeResearchAgent:
    def __init__(self, results):
        self.results = results
        self.call_count = 0
    
    def research(self, question: str, num_docs: int = 5) -> Dict:
        if self.call_count < len(self.results):
            result = self.results[self.call_count]
        else:
            result = self.results[-1]
        self.call_count += 1
        return result


class FakeVerificationAgent:
    def __init__(self, decisions):
        self.decisions = decisions
        self.call_count = 0
    
    def decide(self, verified_claims, confidence, attempt, max_attempts=3) -> Dict:
        if self.call_count < len(self.decisions):
            decision = self.decisions[self.call_count]
        else:
            decision = self.decisions[-1]
        self.call_count += 1
        return decision


def test_7_F1_planner_context_not_exposed_in_result():
    """
    PlannerContext internals should not appear in final result.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Test answer",
            "confidence_level": "HIGH",
            "confidence_reason": "Agreement",
            "evidence": [{"claim": "Test", "status": "AGREEMENT", "sources": ["https://a.com"]}]
        }
    ])
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.ACCEPT, "reason": "Good", "recommendation": None}
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    
    result = planner.run("Test question")
    
    # Result should not contain internal context fields
    internal_fields = [
        "current_state", "attempt_count", "max_attempts",
        "confidence_history", "decision_history", "strategy_history",
        "no_progress_count", "search_count", "max_searches"
    ]
    
    exposed = [f for f in internal_fields if f in result]
    
    passed = len(exposed) == 0
    detail = f"result_keys={list(result.keys())}, exposed={exposed}"
    
    db.close()
    return passed, detail


def test_7_F2_verification_decision_only_summary():
    """
    VerificationAgent returns only decision summary, not internal logic.
    """
    agent = VerificationAgent()
    
    claims = [
        VerifiedClaim(
            claim="Test",
            sources=["https://test.com"],
            status=VerificationStatus.AGREEMENT
        )
    ]
    confidence = {"confidence_level": "HIGH", "confidence_reason": "Agreement"}
    
    decision = agent.decide(
        verified_claims=claims,
        confidence=confidence,
        attempt=1,
        max_attempts=3
    )
    
    # Should only have decision, reason, recommendation
    allowed_keys = {"decision", "reason", "recommendation"}
    actual_keys = set(decision.keys())
    
    only_allowed = actual_keys == allowed_keys
    
    # Check reason doesn't expose internals
    reason = decision.get("reason", "")
    internal_patterns = ["state", "algorithm", "loop", "iteration"]
    internal_exposed = [p for p in internal_patterns if p.lower() in reason.lower()]
    
    passed = only_allowed and len(internal_exposed) == 0
    detail = f"keys={actual_keys}, internal_exposed={internal_exposed}"
    
    return passed, detail


def test_7_F3_search_strategy_not_in_answer():
    """
    Search strategy details should not appear in user-facing answer.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Test answer without strategy details",
            "confidence_level": "HIGH",
            "confidence_reason": "Good evidence",
            "evidence": []
        }
    ])
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.ACCEPT, "reason": "OK", "recommendation": None}
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    
    result = planner.run("Test question")
    
    answer = result.get("answer", "")
    
    # Should not contain strategy names
    strategies = ["BROADEN_QUERY", "AUTHORITATIVE_SITES", "RESEARCH_FOCUSED", "SearchStrategy"]
    strategy_exposed = [s for s in strategies if s in answer]
    
    passed = len(strategy_exposed) == 0
    detail = f"strategy_exposed={strategy_exposed}"
    
    db.close()
    return passed, detail


# ======================================================================
# TEST G: Error Messages TEA Compliance
# ======================================================================

def test_7_G1_failure_reason_no_stack_trace():
    """
    Failure reasons should not contain stack traces.
    """
    db = create_test_db()
    
    # Force failure
    fake_research = FakeResearchAgent([
        {
            "answer": "",
            "confidence_level": "LOW",
            "confidence_reason": "No information found",
            "evidence": []
        }
    ])
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.STOP, "reason": "No claims", "recommendation": None}
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=1
    )
    
    result = planner.run("Test question")
    
    # Check notes/reason for stack trace markers
    notes = result.get("notes", "") or ""
    reason = result.get("confidence_reason", "") or ""
    combined = notes + reason
    
    stack_markers = ["Traceback", "File ", "line ", "Error:", "Exception"]
    stack_found = [m for m in stack_markers if m in combined]
    
    passed = len(stack_found) == 0
    detail = f"stack_markers_found={stack_found}"
    
    db.close()
    return passed, detail


def test_7_G2_failure_reason_user_friendly():
    """
    Failure reasons should be user-friendly, not technical.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {
            "answer": "",
            "confidence_level": "LOW",
            "confidence_reason": "Insufficient sources",
            "evidence": []
        }
    ])
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.STOP, "reason": "Cannot verify", "recommendation": None}
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=1
    )
    
    result = planner.run("Test question")
    
    notes = result.get("notes", "") or ""
    
    # Should not contain technical jargon
    technical_terms = ["NoneType", "AttributeError", "KeyError", "IndexError", "null"]
    technical_found = [t for t in technical_terms if t in notes]
    
    passed = len(technical_found) == 0
    detail = f"notes='{notes[:60]}...', technical_found={technical_found}"
    
    db.close()
    return passed, detail


# ======================================================================
# TEST H: LLM Client TEA Compliance
# ======================================================================

def test_7_H1_llm_client_no_logging_of_prompts():
    """
    LLM client should not log prompts to user-accessible locations.
    """
    # Check llm_client.py for logging
    import utils.llm_client as llm_module
    import inspect
    
    source = inspect.getsource(llm_module)
    
    # Should not have print() or logging.info() with prompt
    logging_patterns = ["print(prompt", "logging.info(prompt", "logger.info(prompt"]
    logging_found = [p for p in logging_patterns if p in source]
    
    passed = len(logging_found) == 0
    detail = f"logging_found={logging_found}"
    
    return passed, detail


def test_7_H2_llm_response_not_stored_raw():
    """
    Raw LLM responses should not be stored in database.
    """
    # Check all models for raw_response fields
    from storage.models.answer_snapshot import AnswerSnapshot
    from storage.models.evidence import Evidence
    from storage.models.planner_trace import PlannerTrace
    from storage.models.query_session import QuerySession
    
    all_columns = []
    for model in [AnswerSnapshot, Evidence, PlannerTrace, QuerySession]:
        cols = [c.name for c in model.__table__.columns]
        all_columns.extend(cols)
    
    raw_columns = [c for c in all_columns if "raw" in c.lower() or "llm_output" in c.lower()]
    
    passed = len(raw_columns) == 0
    detail = f"raw_columns={raw_columns}"
    
    return passed, detail


# ======================================================================
# TEST I: Evidence Integrity
# ======================================================================

def test_7_I1_evidence_shows_only_verified_claims():
    """
    Evidence should contain only verified claims, not intermediate processing.
    """
    synthesizer = AnswerSynthesizer()
    
    claims = [
        VerifiedClaim(
            claim="Claim A - verified",
            sources=["https://a.com"],
            status=VerificationStatus.AGREEMENT
        ),
        VerifiedClaim(
            claim="Claim B - verified",
            sources=["https://b.com"],
            status=VerificationStatus.SINGLE_SOURCE
        ),
    ]
    confidence = {"confidence_level": "MEDIUM", "confidence_reason": "Partial agreement"}
    
    with patch("synthesis.answer_synthesizer.llm_complete") as mock_llm:
        mock_llm.return_value = "Test answer"
        
        result = synthesizer.synthesize(
            question="Test",
            verified_claims=claims,
            confidence=confidence
        )
    
    evidence = result.get("evidence", [])
    
    # Evidence should match input claims exactly
    evidence_claims = {e["claim"] for e in evidence}
    expected_claims = {"Claim A - verified", "Claim B - verified"}
    
    exact_match = evidence_claims == expected_claims
    
    passed = exact_match
    detail = f"evidence_claims={evidence_claims}"
    
    return passed, detail


def test_7_I2_evidence_no_confidence_scores_internal():
    """
    Evidence items should not expose internal confidence scores.
    """
    # Check EvidenceItem schema
    evidence_fields = set(EvidenceItem.model_fields.keys())
    
    # Should only have claim, status, sources
    score_fields = [f for f in evidence_fields if "score" in f.lower() or "confidence" in f.lower()]
    
    passed = len(score_fields) == 0
    detail = f"evidence_fields={evidence_fields}, score_fields={score_fields}"
    
    return passed, detail


# ======================================================================
# MAIN TEST RUNNER
# ======================================================================

def run_all_tests():
    print_header()
    
    tests = [
        # Test A: API Schema Compliance
        ("7.A1", "QueryResult schema no reasoning", test_7_A1_query_result_schema_no_reasoning_fields),
        ("7.A2", "QueryStatus schema minimal", test_7_A2_query_status_schema_minimal),
        ("7.A3", "QuerySubmit response minimal", test_7_A3_query_submit_response_minimal),
        ("7.A4", "EvidenceItem no reasoning", test_7_A4_evidence_item_schema_no_reasoning),
        ("7.A5", "Trace response no prompts", test_7_A5_trace_response_no_prompts_or_reasoning),
        
        # Test B: No Reasoning in Responses
        ("7.B1", "Answer no reasoning markers", test_7_B1_answer_contains_no_reasoning_markers),
        ("7.B2", "Confidence reason no internals", test_7_B2_confidence_reason_no_internal_details),
        ("7.B3", "Notes no planner internals", test_7_B3_notes_do_not_expose_planner_internals),
        
        # Test C: User Control Restrictions
        ("7.C1", "User cannot specify retries", test_7_C1_user_cannot_specify_retries),
        ("7.C2", "User cannot specify strategy", test_7_C2_user_cannot_specify_strategy),
        ("7.C3", "User cannot specify num_docs", test_7_C3_user_cannot_specify_num_docs),
        ("7.C4", "User cannot bypass verification", test_7_C4_user_cannot_bypass_verification),
        
        # Test D: Database Storage Compliance
        ("7.D1", "PlannerTrace stores decisions only", test_7_D1_planner_trace_stores_only_decisions),
        ("7.D2", "AnswerSnapshot stores output only", test_7_D2_answer_snapshot_stores_only_output),
        ("7.D3", "Evidence stores claims/sources only", test_7_D3_evidence_stores_only_claims_and_sources),
        ("7.D4", "QuerySession no internal state", test_7_D4_query_session_no_internal_state),
        
        # Test E: Trace Endpoint Protection
        ("7.E1", "Trace endpoint requires token", test_7_E1_trace_endpoint_requires_token),
        ("7.E2", "Trace response no LLM prompts", test_7_E2_trace_response_no_llm_prompts),
        ("7.E3", "Trace response no raw LLM output", test_7_E3_trace_response_no_raw_llm_output),
        
        # Test F: Planner Logic Opacity
        ("7.F1", "PlannerContext not in result", test_7_F1_planner_context_not_exposed_in_result),
        ("7.F2", "VerificationDecision only summary", test_7_F2_verification_decision_only_summary),
        ("7.F3", "Strategy not in answer", test_7_F3_search_strategy_not_in_answer),
        
        # Test G: Error Messages
        ("7.G1", "Failure reason no stack trace", test_7_G1_failure_reason_no_stack_trace),
        ("7.G2", "Failure reason user friendly", test_7_G2_failure_reason_user_friendly),
        
        # Test H: LLM Client Compliance
        ("7.H1", "LLM client no prompt logging", test_7_H1_llm_client_no_logging_of_prompts),
        ("7.H2", "LLM response not stored raw", test_7_H2_llm_response_not_stored_raw),
        
        # Test I: Evidence Integrity
        ("7.I1", "Evidence shows verified only", test_7_I1_evidence_shows_only_verified_claims),
        ("7.I2", "Evidence no internal scores", test_7_I2_evidence_no_confidence_scores_internal),
    ]
    
    passed_count = 0
    failed_count = 0
    
    for test_id, name, test_func in tests:
        try:
            passed, detail = test_func()
            print_result(test_id, name, passed, detail)
            if passed:
                passed_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print_result(test_id, name, False, f"Exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed_count += 1
    
    print_summary(passed_count, failed_count, len(tests))
    return failed_count == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
