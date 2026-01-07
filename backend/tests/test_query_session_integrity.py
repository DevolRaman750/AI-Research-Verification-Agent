"""
======================================================================
DATABASE CONSISTENCY & AUDIT TESTS - 4.1 Query Session Integrity
======================================================================

Tests for query session database integrity:
- Exactly one row in query_sessions per query
- Correct status updates (INIT → RESEARCH → VERIFY → SYNTHESIZE → DONE/FAILED)
- Correct final confidence stored

Uses in-memory SQLite for test isolation.
"""

import sys
sys.path.insert(0, "c:/Agents/AI-Research-Agent/backend")

import uuid
from typing import Dict, List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from storage.base import Base
from storage.models.query_session import QuerySession
from storage.repositories.query_session_repo import QuerySessionRepository
from planner.planner_agent import PlannerAgent, PlannerState, PlannerContext, SearchStrategy
from agents.VerificationAgent import VerificationAgent, VerificationDecision
from verification.models import VerifiedClaim, VerificationStatus


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
            result = self.results[-1]  # Return last result if exceeded
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
    print("DATABASE CONSISTENCY & AUDIT TESTS - 4.1 Query Session Integrity")
    print("=" * 70)


def print_result(test_id: str, name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {test_id} {name} | {detail}")


def print_summary(passed: int, failed: int, total: int):
    print("-" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {total} tests")


# ======================================================================
# 4.1.1 TEST: Exactly one row created per query
# ======================================================================

def test_4_1_1_exactly_one_row_per_query():
    """
    Running the planner should create exactly ONE row in query_sessions.
    """
    db = create_test_db()
    
    # Setup: Single successful flow
    fake_research = FakeResearchAgent([
        {
            "answer": "Test answer",
            "confidence_level": "HIGH",
            "confidence_reason": "Multiple sources agree",
            "evidence": [{"claim": "Test", "status": "AGREEMENT", "sources": ["a.com", "b.com"]}]
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
    
    # Execute
    planner.run("What is the capital of France?")
    
    # Verify: Count rows
    row_count = db.query(QuerySession).count()
    
    passed = row_count == 1
    detail = f"row_count={row_count}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.1.2 TEST: Session has correct question stored
# ======================================================================

def test_4_1_2_question_stored_correctly():
    """
    The query_session row should store the exact question asked.
    """
    db = create_test_db()
    
    question = "What is quantum entanglement?"
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Quantum entanglement is...",
            "confidence_level": "HIGH",
            "confidence_reason": "Sources agree",
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
    
    planner.run(question)
    
    # Verify
    session = db.query(QuerySession).first()
    stored_question = session.question if session else None
    
    passed = stored_question == question
    detail = f"stored='{stored_question}'"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.1.3 TEST: Status updates to DONE on success
# ======================================================================

def test_4_1_3_status_done_on_success():
    """
    When planner completes successfully, final status should be DONE.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Paris is the capital",
            "confidence_level": "HIGH",
            "confidence_reason": "Agreement",
            "evidence": [{"claim": "Paris is capital", "status": "AGREEMENT", "sources": ["a.com"]}]
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
    
    session = db.query(QuerySession).first()
    status = session.status if session else None
    
    passed = status == "DONE"
    detail = f"final_status={status}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.1.4 TEST: Status updates to FAILED on failure
# ======================================================================

def test_4_1_4_status_failed_on_failure():
    """
    When planner exhausts retries (RETRY decisions until _should_stop),
    final status should be FAILED.
    
    Note: STOP decision goes to SYNTHESIZE→DONE with low confidence.
    FAILED only happens when RETRY is exhausted via _should_stop().
    """
    db = create_test_db()
    
    # All attempts return LOW confidence → always RETRY
    fake_research = FakeResearchAgent([
        {
            "answer": "Uncertain answer",
            "confidence_level": "LOW",
            "confidence_reason": "Single source",
            "evidence": [{"claim": "Test", "status": "SINGLE_SOURCE", "sources": ["x.com"]}]
        }
    ] * 10)  # Multiple results for retries
    
    # Always return RETRY - this will exhaust attempts and trigger FAILED
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.RETRY, "reason": "Low confidence", "recommendation": "Try more sources"},
        {"decision": VerificationDecision.RETRY, "reason": "Still low", "recommendation": "Try more"},
        {"decision": VerificationDecision.RETRY, "reason": "Keep trying", "recommendation": "More sources"},
        {"decision": VerificationDecision.RETRY, "reason": "Retry again", "recommendation": "More"},
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    
    planner.run("Some obscure question with no good answer?")
    
    session = db.query(QuerySession).first()
    status = session.status if session else None
    
    passed = status == "FAILED"
    detail = f"final_status={status}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.1.5 TEST: Final confidence level stored correctly (HIGH)
# ======================================================================

def test_4_1_5_final_confidence_high_stored():
    """
    When result has HIGH confidence, it should be stored in query_session.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Water boils at 100C",
            "confidence_level": "HIGH",
            "confidence_reason": "Multiple authoritative sources agree",
            "evidence": []
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
    
    planner.run("At what temperature does water boil?")
    
    session = db.query(QuerySession).first()
    confidence_level = session.final_confidence_level if session else None
    
    passed = confidence_level == "HIGH"
    detail = f"final_confidence_level={confidence_level}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.1.6 TEST: Final confidence level stored correctly (LOW on failure)
# ======================================================================

def test_4_1_6_final_confidence_low_on_failure():
    """
    When planner fails, confidence should be stored as LOW.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Unknown",
            "confidence_level": "LOW",
            "confidence_reason": "No agreement",
            "evidence": []
        }
    ] * 5)
    
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.RETRY, "reason": "Low", "recommendation": "Retry"},
        {"decision": VerificationDecision.RETRY, "reason": "Low", "recommendation": "Retry"},
        {"decision": VerificationDecision.STOP, "reason": "Exhausted", "recommendation": None},
    ])
    
    planner = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    
    planner.run("Obscure question with no answer?")
    
    session = db.query(QuerySession).first()
    confidence_level = session.final_confidence_level if session else None
    
    passed = confidence_level == "LOW"
    detail = f"final_confidence_level={confidence_level}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.1.7 TEST: Final confidence reason stored correctly
# ======================================================================

def test_4_1_7_confidence_reason_stored():
    """
    The confidence_reason should be stored in query_session.
    """
    db = create_test_db()
    
    expected_reason = "Multiple independent sources confirm this fact"
    
    fake_research = FakeResearchAgent([
        {
            "answer": "The answer",
            "confidence_level": "HIGH",
            "confidence_reason": expected_reason,
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
    
    planner.run("Test question")
    
    session = db.query(QuerySession).first()
    stored_reason = session.final_confidence_reason if session else None
    
    passed = stored_reason == expected_reason
    detail = f"reason_stored={stored_reason is not None}, matches={stored_reason == expected_reason}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.1.8 TEST: Session ID is valid UUID
# ======================================================================

def test_4_1_8_session_id_is_valid_uuid():
    """
    The session ID should be a valid UUID string.
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
    
    planner.run("Test question")
    
    session = db.query(QuerySession).first()
    session_id = session.id if session else None
    
    # Validate UUID format
    is_valid_uuid = False
    if session_id:
        try:
            uuid.UUID(str(session_id))
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False
    
    passed = is_valid_uuid
    detail = f"session_id={session_id}, valid_uuid={is_valid_uuid}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.1.9 TEST: Multiple queries create separate rows
# ======================================================================

def test_4_1_9_multiple_queries_separate_rows():
    """
    Running multiple queries should create separate rows, not update existing.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {"answer": "Answer 1", "confidence_level": "HIGH", "confidence_reason": "OK", "evidence": []},
        {"answer": "Answer 2", "confidence_level": "HIGH", "confidence_reason": "OK", "evidence": []},
    ])
    
    fake_verification = FakeVerificationAgent([
        {"decision": VerificationDecision.ACCEPT, "reason": "OK", "recommendation": None},
        {"decision": VerificationDecision.ACCEPT, "reason": "OK", "recommendation": None},
    ])
    
    # First query
    planner1 = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    planner1.run("First question?")
    
    # Reset fake agents for second query
    fake_research.call_count = 0
    fake_verification.call_count = 0
    
    # Second query - new planner instance
    planner2 = PlannerAgent(
        research_agent=fake_research,
        verification_agent=fake_verification,
        db=db,
        max_attempts=3
    )
    planner2.run("Second question?")
    
    row_count = db.query(QuerySession).count()
    
    # Get both sessions
    sessions = db.query(QuerySession).all()
    questions = [s.question for s in sessions]
    ids_unique = len(set(s.id for s in sessions)) == 2
    
    passed = row_count == 2 and ids_unique
    detail = f"row_count={row_count}, ids_unique={ids_unique}, questions={questions}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.1.10 TEST: created_at timestamp is set
# ======================================================================

def test_4_1_10_created_at_timestamp_set():
    """
    The created_at timestamp should be automatically set.
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
    
    planner.run("Test question")
    
    session = db.query(QuerySession).first()
    created_at = session.created_at if session else None
    
    passed = created_at is not None
    detail = f"created_at={created_at}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.1.11 TEST: Repository get() returns correct session
# ======================================================================

def test_4_1_11_repository_get_returns_correct():
    """
    QuerySessionRepository.get() should return the correct session by ID.
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
    
    planner.run("Test question")
    
    # Get session ID from planner
    session_id = planner.session_id
    
    # Use repository to fetch
    fetched = QuerySessionRepository.get(db, session_id)
    
    passed = fetched is not None and str(fetched.id) == str(session_id)
    detail = f"session_id={session_id}, fetched_id={fetched.id if fetched else None}"
    
    db.close()
    return passed, detail


# ======================================================================
# MAIN TEST RUNNER
# ======================================================================

def run_all_tests():
    print_header()
    
    tests = [
        ("4.1.1", "Exactly one row per query", test_4_1_1_exactly_one_row_per_query),
        ("4.1.2", "Question stored correctly", test_4_1_2_question_stored_correctly),
        ("4.1.3", "Status DONE on success", test_4_1_3_status_done_on_success),
        ("4.1.4", "Status FAILED on failure", test_4_1_4_status_failed_on_failure),
        ("4.1.5", "Final confidence HIGH stored", test_4_1_5_final_confidence_high_stored),
        ("4.1.6", "Final confidence LOW on failure", test_4_1_6_final_confidence_low_on_failure),
        ("4.1.7", "Confidence reason stored", test_4_1_7_confidence_reason_stored),
        ("4.1.8", "Session ID is valid UUID", test_4_1_8_session_id_is_valid_uuid),
        ("4.1.9", "Multiple queries → separate rows", test_4_1_9_multiple_queries_separate_rows),
        ("4.1.10", "created_at timestamp set", test_4_1_10_created_at_timestamp_set),
        ("4.1.11", "Repository get() works", test_4_1_11_repository_get_returns_correct),
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
