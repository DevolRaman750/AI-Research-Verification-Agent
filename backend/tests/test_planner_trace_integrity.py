"""
======================================================================
DATABASE CONSISTENCY & AUDIT TESTS - 4.2 Planner Trace Integrity
======================================================================

Tests for planner trace database integrity:
- One trace per attempt
- Correct planner_state transitions
- Correct strategy_used
- stop_reason populated on failure
- No trace should contain: raw reasoning, LLM prompt text, chain-of-thought

Uses in-memory SQLite for test isolation.
"""

import sys
sys.path.insert(0, "c:/Agents/AI-Research-Agent/backend")

import uuid
from typing import Dict, List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from storage.base import Base
from storage.models.query_session import QuerySession
from storage.models.planner_trace import PlannerTrace
from storage.repositories.planner_trace_repo import PlannerTraceRepository
from planner.planner_agent import PlannerAgent, PlannerState, SearchStrategy
from agents.VerificationAgent import VerificationDecision


# ======================================================================
# TEST DATABASE SETUP
# ======================================================================

def create_test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    return TestSession()


# ======================================================================
# FAKE AGENTS FOR DETERMINISTIC TESTING
# ======================================================================

class FakeResearchAgent:
    """Returns predetermined research results."""
    
    def __init__(self, results: List[Dict]):
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
    """Returns predetermined verification decisions."""
    
    def __init__(self, decisions: List[Dict]):
        self.decisions = decisions
        self.call_count = 0
    
    def decide(self, verified_claims, confidence, attempt, max_attempts=3) -> Dict:
        if self.call_count < len(self.decisions):
            decision = self.decisions[self.call_count]
        else:
            decision = self.decisions[-1]
        self.call_count += 1
        return decision


# ======================================================================
# TEST UTILITIES
# ======================================================================

def print_header():
    print("\n" + "=" * 70)
    print("DATABASE CONSISTENCY & AUDIT TESTS - 4.2 Planner Trace Integrity")
    print("=" * 70)


def print_result(test_id: str, name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {test_id} {name} | {detail}")


def print_summary(passed: int, failed: int, total: int):
    print("-" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {total} tests")


# Forbidden patterns that should NEVER appear in traces
FORBIDDEN_PATTERNS = [
    "You are a",           # LLM system prompt
    "STRICT RULES",        # Prompt instructions
    "Do NOT",              # Prompt instructions
    "chain of thought",    # CoT marker
    "let me think",        # Reasoning marker
    "step by step",        # Reasoning marker
    "reasoning:",          # Explicit reasoning
    "my analysis",         # Explicit reasoning
    "I think",             # First person reasoning
    "I believe",           # First person reasoning
    "therefore",           # Logical chain marker (in reasoning context)
    "```",                 # Code blocks from prompts
    "USER:",               # Chat format
    "ASSISTANT:",          # Chat format
    "SYSTEM:",             # Chat format
]


def contains_forbidden_content(text: str) -> tuple[bool, str]:
    """Check if text contains any forbidden patterns."""
    if not text:
        return False, ""
    text_lower = text.lower()
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in text_lower:
            return True, pattern
    return False, ""


# ======================================================================
# 4.2.1 TEST: Exactly one trace per attempt (single attempt)
# ======================================================================

def test_4_2_1_one_trace_per_attempt_single():
    """
    A single successful attempt should produce exactly one trace.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Paris",
            "confidence_level": "HIGH",
            "confidence_reason": "Multiple sources agree",
            "evidence": [{"claim": "Paris is capital", "status": "AGREEMENT", "sources": ["a.com", "b.com"]}]
        }
    ])
    
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.ACCEPT, "reason": "High confidence", "recommendation": None}
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    
    planner.run("What is the capital of France?")
    
    traces = PlannerTraceRepository.list_by_session(db, planner.session_id)
    
    passed = len(traces) == 1
    detail = f"trace_count={len(traces)}, expected=1"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.2.2 TEST: One trace per attempt (multiple attempts)
# ======================================================================

def test_4_2_2_one_trace_per_attempt_multiple():
    """
    Multiple retry attempts should produce one trace per attempt.
    3 attempts = 3 traces.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {"answer": "A1", "confidence_level": "LOW", "confidence_reason": "Single source", "evidence": []},
        {"answer": "A2", "confidence_level": "LOW", "confidence_reason": "Single source", "evidence": []},
        {"answer": "A3", "confidence_level": "HIGH", "confidence_reason": "Agreement", "evidence": []},
    ])
    
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.RETRY, "reason": "Low confidence", "recommendation": "More sources"},
        {"decision": VerificationDecision.RETRY, "reason": "Still low", "recommendation": "Try again"},
        {"decision": VerificationDecision.ACCEPT, "reason": "High confidence", "recommendation": None},
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    
    planner.run("Test question?")
    
    traces = PlannerTraceRepository.list_by_session(db, planner.session_id)
    attempt_numbers = [t.attempt_number for t in traces]
    
    passed = len(traces) == 3 and attempt_numbers == [1, 2, 3]
    detail = f"trace_count={len(traces)}, attempts={attempt_numbers}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.2.3 TEST: Correct planner_state in trace (should be VERIFY)
# ======================================================================

def test_4_2_3_correct_planner_state():
    """
    Traces are logged during VERIFY state, so planner_state should be VERIFY.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {"answer": "Test", "confidence_level": "HIGH", "confidence_reason": "OK", "evidence": []}
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
    
    planner.run("Test question?")
    
    traces = PlannerTraceRepository.list_by_session(db, planner.session_id)
    
    all_verify = all(t.planner_state == "VERIFY" for t in traces)
    states = [t.planner_state for t in traces]
    
    passed = all_verify
    detail = f"states={states}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.2.4 TEST: Correct strategy_used recorded
# ======================================================================

def test_4_2_4_correct_strategy_used():
    """
    The strategy_used should match the strategy actually used for that attempt.
    First attempt uses BASE strategy.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {"answer": "Test", "confidence_level": "HIGH", "confidence_reason": "OK", "evidence": []}
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
    
    planner.run("Test question?")
    
    traces = PlannerTraceRepository.list_by_session(db, planner.session_id)
    
    first_strategy = traces[0].strategy_used if traces else None
    
    passed = first_strategy == "BASE"
    detail = f"strategy_used={first_strategy}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.2.5 TEST: Strategy rotation recorded in traces
# ======================================================================

def test_4_2_5_strategy_rotation_recorded():
    """
    When strategy rotates across attempts, each trace should show the correct strategy.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {"answer": "A1", "confidence_level": "LOW", "confidence_reason": "Single source", "evidence": []},
        {"answer": "A2", "confidence_level": "LOW", "confidence_reason": "Single source", "evidence": []},
        {"answer": "A3", "confidence_level": "HIGH", "confidence_reason": "Agreement", "evidence": []},
    ])
    
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.RETRY, "reason": "Low - single source", "recommendation": "Broaden"},
        {"decision": VerificationDecision.RETRY, "reason": "Still low", "recommendation": "More"},
        {"decision": VerificationDecision.ACCEPT, "reason": "OK", "recommendation": None},
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    
    planner.run("Test question?")
    
    traces = PlannerTraceRepository.list_by_session(db, planner.session_id)
    strategies = [t.strategy_used for t in traces]
    
    # First should be BASE, then rotated strategies
    first_is_base = strategies[0] == "BASE" if strategies else False
    all_valid_strategies = all(
        s in ["BASE", "BROADEN_QUERY", "AUTHORITATIVE_SITES", "RESEARCH_FOCUSED"]
        for s in strategies
    )
    
    passed = first_is_base and all_valid_strategies and len(set(strategies)) >= 2
    detail = f"strategies={strategies}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.2.6 TEST: stop_reason populated on STOP decision
# ======================================================================

def test_4_2_6_stop_reason_on_stop():
    """
    When verification returns STOP, the stop_reason should be populated.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {"answer": "Test", "confidence_level": "LOW", "confidence_reason": "Conflict", "evidence": []}
    ])
    
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.STOP, "reason": "Conflicting evidence persists", "recommendation": None}
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    
    planner.run("Controversial question?")
    
    traces = PlannerTraceRepository.list_by_session(db, planner.session_id)
    
    has_stop_reason = traces[0].stop_reason is not None and len(traces[0].stop_reason) > 0
    stop_reason = traces[0].stop_reason if traces else None
    
    passed = has_stop_reason
    detail = f"stop_reason='{stop_reason}'"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.2.7 TEST: stop_reason populated on RETRY decisions too (reason field)
# ======================================================================

def test_4_2_7_reason_on_retry():
    """
    Even RETRY decisions should have a reason recorded in stop_reason field.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {"answer": "A1", "confidence_level": "LOW", "confidence_reason": "Weak", "evidence": []},
        {"answer": "A2", "confidence_level": "HIGH", "confidence_reason": "OK", "evidence": []},
    ])
    
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.RETRY, "reason": "Need more sources for confidence", "recommendation": "Search broader"},
        {"decision": VerificationDecision.ACCEPT, "reason": "Now confident", "recommendation": None},
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    
    planner.run("Test question?")
    
    traces = PlannerTraceRepository.list_by_session(db, planner.session_id)
    
    # First trace (RETRY) should have reason
    first_reason = traces[0].stop_reason if traces else None
    has_reason = first_reason is not None and len(first_reason) > 0
    
    passed = has_reason
    detail = f"retry_reason='{first_reason}'"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.2.8 TEST: verification_decision correctly recorded
# ======================================================================

def test_4_2_8_verification_decision_recorded():
    """
    The verification_decision field should correctly record ACCEPT/RETRY/STOP.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {"answer": "A1", "confidence_level": "LOW", "confidence_reason": "Weak", "evidence": []},
        {"answer": "A2", "confidence_level": "HIGH", "confidence_reason": "OK", "evidence": []},
    ])
    
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.RETRY, "reason": "Low", "recommendation": "More"},
        {"decision": VerificationDecision.ACCEPT, "reason": "OK", "recommendation": None},
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    
    planner.run("Test?")
    
    traces = PlannerTraceRepository.list_by_session(db, planner.session_id)
    decisions = [t.verification_decision for t in traces]
    
    expected = ["RETRY", "ACCEPT"]
    passed = decisions == expected
    detail = f"decisions={decisions}, expected={expected}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.2.9 TEST: num_docs recorded in trace
# ======================================================================

def test_4_2_9_num_docs_recorded():
    """
    The num_docs field should show document count used for each attempt.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {"answer": "Test", "confidence_level": "HIGH", "confidence_reason": "OK", "evidence": []}
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
    
    planner.run("Test?")
    
    traces = PlannerTraceRepository.list_by_session(db, planner.session_id)
    
    num_docs = traces[0].num_docs if traces else None
    
    # First attempt should use default num_docs (5)
    passed = num_docs == 5
    detail = f"num_docs={num_docs}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.2.10 TEST: No raw reasoning in stop_reason
# ======================================================================

def test_4_2_10_no_raw_reasoning_in_stop_reason():
    """
    The stop_reason should NOT contain raw LLM reasoning, prompts, or chain-of-thought.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {"answer": "Test", "confidence_level": "LOW", "confidence_reason": "Weak", "evidence": []}
    ])
    
    # Simulate what a well-behaved verification agent returns
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.STOP, "reason": "Confidence remains low after repeated attempts.", "recommendation": None}
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    
    planner.run("Test?")
    
    traces = PlannerTraceRepository.list_by_session(db, planner.session_id)
    
    stop_reason = traces[0].stop_reason if traces else ""
    has_forbidden, pattern = contains_forbidden_content(stop_reason)
    
    passed = not has_forbidden
    detail = f"forbidden_found={has_forbidden}" + (f", pattern='{pattern}'" if has_forbidden else "")
    
    db.close()
    return passed, detail


# ======================================================================
# 4.2.11 TEST: No LLM prompt text in any trace field
# ======================================================================

def test_4_2_11_no_llm_prompt_in_traces():
    """
    No trace field should contain LLM prompt artifacts like 'You are a...' or 'STRICT RULES'.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {"answer": "A1", "confidence_level": "LOW", "confidence_reason": "Single source only", "evidence": []},
        {"answer": "A2", "confidence_level": "HIGH", "confidence_reason": "Multiple sources agree", "evidence": []},
    ])
    
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.RETRY, "reason": "Evidence from single source lacks confirmation", "recommendation": "Search broader"},
        {"decision": VerificationDecision.ACCEPT, "reason": "Multiple independent sources now agree", "recommendation": None},
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    
    planner.run("Test?")
    
    traces = PlannerTraceRepository.list_by_session(db, planner.session_id)
    
    all_clean = True
    found_pattern = None
    
    for trace in traces:
        # Check all text fields
        fields_to_check = [
            trace.planner_state,
            trace.verification_decision,
            trace.strategy_used,
            trace.stop_reason or ""
        ]
        
        for field in fields_to_check:
            has_forbidden, pattern = contains_forbidden_content(str(field))
            if has_forbidden:
                all_clean = False
                found_pattern = pattern
                break
        
        if not all_clean:
            break
    
    passed = all_clean
    detail = f"all_fields_clean={all_clean}" + (f", found='{found_pattern}'" if found_pattern else "")
    
    db.close()
    return passed, detail


# ======================================================================
# 4.2.12 TEST: Trace created_at timestamp is set
# ======================================================================

def test_4_2_12_trace_timestamp_set():
    """
    Each trace should have a created_at timestamp.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {"answer": "Test", "confidence_level": "HIGH", "confidence_reason": "OK", "evidence": []}
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
    
    planner.run("Test?")
    
    traces = PlannerTraceRepository.list_by_session(db, planner.session_id)
    
    has_timestamp = traces[0].created_at is not None if traces else False
    
    passed = has_timestamp
    detail = f"created_at={traces[0].created_at if traces else None}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.2.13 TEST: Traces linked to correct session
# ======================================================================

def test_4_2_13_traces_linked_to_session():
    """
    All traces should be linked to the correct session_id.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {"answer": "A1", "confidence_level": "LOW", "confidence_reason": "Weak", "evidence": []},
        {"answer": "A2", "confidence_level": "HIGH", "confidence_reason": "OK", "evidence": []},
    ])
    
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.RETRY, "reason": "Low", "recommendation": "More"},
        {"decision": VerificationDecision.ACCEPT, "reason": "OK", "recommendation": None},
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    
    planner.run("Test?")
    
    traces = PlannerTraceRepository.list_by_session(db, planner.session_id)
    
    all_linked = all(str(t.session_id) == str(planner.session_id) for t in traces)
    
    passed = all_linked and len(traces) > 0
    detail = f"all_linked={all_linked}, trace_count={len(traces)}"
    
    db.close()
    return passed, detail


# ======================================================================
# MAIN TEST RUNNER
# ======================================================================

def run_all_tests():
    print_header()
    
    tests = [
        ("4.2.1", "One trace per attempt (single)", test_4_2_1_one_trace_per_attempt_single),
        ("4.2.2", "One trace per attempt (multiple)", test_4_2_2_one_trace_per_attempt_multiple),
        ("4.2.3", "Correct planner_state (VERIFY)", test_4_2_3_correct_planner_state),
        ("4.2.4", "Correct strategy_used (BASE first)", test_4_2_4_correct_strategy_used),
        ("4.2.5", "Strategy rotation recorded", test_4_2_5_strategy_rotation_recorded),
        ("4.2.6", "stop_reason on STOP decision", test_4_2_6_stop_reason_on_stop),
        ("4.2.7", "Reason on RETRY decisions", test_4_2_7_reason_on_retry),
        ("4.2.8", "verification_decision recorded", test_4_2_8_verification_decision_recorded),
        ("4.2.9", "num_docs recorded", test_4_2_9_num_docs_recorded),
        ("4.2.10", "No raw reasoning in stop_reason", test_4_2_10_no_raw_reasoning_in_stop_reason),
        ("4.2.11", "No LLM prompt in traces", test_4_2_11_no_llm_prompt_in_traces),
        ("4.2.12", "Trace timestamp set", test_4_2_12_trace_timestamp_set),
        ("4.2.13", "Traces linked to session", test_4_2_13_traces_linked_to_session),
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
            print_result(test_id, name, False, f"Exception: {e}")
            failed_count += 1
    
    print_summary(passed_count, failed_count, len(tests))
    return failed_count == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
