"""
======================================================================
DATABASE CONSISTENCY & AUDIT TESTS - 4.3 Evidence Integrity
======================================================================

Tests for evidence database integrity:
- Every evidence row maps to session_id
- No evidence without source URLs
- Evidence matches answer claims exactly

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
from storage.models.evidence import Evidence
from storage.repositories.evidence_repo import EvidenceRepository
from planner.planner_agent import PlannerAgent, PlannerState
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
    print("DATABASE CONSISTENCY & AUDIT TESTS - 4.3 Evidence Integrity")
    print("=" * 70)


def print_result(test_id: str, name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {test_id} {name} | {detail}")


def print_summary(passed: int, failed: int, total: int):
    print("-" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {total} tests")


# ======================================================================
# 4.3.1 TEST: Evidence rows have valid session_id
# ======================================================================

def test_4_3_1_evidence_has_session_id():
    """
    Every evidence row must have a non-null session_id.
    """
    db = create_test_db()
    
    evidence_items = [
        {"claim": "Water boils at 100C", "status": "AGREEMENT", "sources": ["https://physics.edu", "https://science.org"]},
        {"claim": "Ice melts at 0C", "status": "AGREEMENT", "sources": ["https://chemistry.edu"]},
    ]
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Water boils at 100C",
            "confidence_level": "HIGH",
            "confidence_reason": "Multiple sources agree",
            "evidence": evidence_items
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
    
    # Check all evidence rows
    all_evidence = db.query(Evidence).all()
    all_have_session_id = all(e.session_id is not None for e in all_evidence)
    
    passed = all_have_session_id and len(all_evidence) > 0
    detail = f"evidence_count={len(all_evidence)}, all_have_session_id={all_have_session_id}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.3.2 TEST: Evidence maps to correct session
# ======================================================================

def test_4_3_2_evidence_maps_to_correct_session():
    """
    Evidence session_id should match the planner's session_id.
    """
    db = create_test_db()
    
    evidence_items = [
        {"claim": "Paris is the capital of France", "status": "AGREEMENT", "sources": ["https://gov.fr", "https://wiki.org"]},
    ]
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Paris",
            "confidence_level": "HIGH",
            "confidence_reason": "Agreement",
            "evidence": evidence_items
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
    
    planner.run("What is the capital of France?")
    
    evidence_list = EvidenceRepository.list_by_session(db, planner.session_id)
    all_match = all(str(e.session_id) == str(planner.session_id) for e in evidence_list)
    
    passed = all_match and len(evidence_list) > 0
    detail = f"evidence_count={len(evidence_list)}, all_match_session={all_match}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.3.3 TEST: No evidence without source URLs
# ======================================================================

def test_4_3_3_no_evidence_without_sources():
    """
    Every evidence row must have non-empty source_urls.
    """
    db = create_test_db()
    
    evidence_items = [
        {"claim": "The sun is a star", "status": "AGREEMENT", "sources": ["https://nasa.gov", "https://esa.int"]},
        {"claim": "Stars produce light", "status": "AGREEMENT", "sources": ["https://astronomy.edu"]},
    ]
    
    fake_research = FakeResearchAgent([
        {
            "answer": "The sun is a star",
            "confidence_level": "HIGH",
            "confidence_reason": "Multiple sources",
            "evidence": evidence_items
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
    
    planner.run("What is the sun?")
    
    all_evidence = db.query(Evidence).all()
    all_have_sources = all(
        e.source_urls is not None and len(e.source_urls) > 0
        for e in all_evidence
    )
    
    passed = all_have_sources and len(all_evidence) > 0
    detail = f"evidence_count={len(all_evidence)}, all_have_sources={all_have_sources}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.3.4 TEST: Source URLs are valid strings (not empty)
# ======================================================================

def test_4_3_4_source_urls_are_valid():
    """
    Source URLs should be valid non-empty strings.
    """
    db = create_test_db()
    
    evidence_items = [
        {"claim": "Test claim", "status": "AGREEMENT", "sources": ["https://example.com", "https://test.org"]},
    ]
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Test answer",
            "confidence_level": "HIGH",
            "confidence_reason": "OK",
            "evidence": evidence_items
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
    
    planner.run("Test question?")
    
    all_evidence = db.query(Evidence).all()
    
    all_urls_valid = True
    for e in all_evidence:
        for url in e.source_urls:
            if not isinstance(url, str) or len(url.strip()) == 0:
                all_urls_valid = False
                break
    
    passed = all_urls_valid and len(all_evidence) > 0
    detail = f"all_urls_valid={all_urls_valid}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.3.5 TEST: Evidence claim_text matches research result exactly
# ======================================================================

def test_4_3_5_evidence_matches_claims_exactly():
    """
    The claim_text in evidence should exactly match the claims from research result.
    """
    db = create_test_db()
    
    original_claims = [
        {"claim": "Mount Everest is 8,849 meters tall", "status": "AGREEMENT", "sources": ["https://geo.org"]},
        {"claim": "It is located in the Himalayas", "status": "AGREEMENT", "sources": ["https://maps.edu"]},
    ]
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Mount Everest is the tallest mountain",
            "confidence_level": "HIGH",
            "confidence_reason": "Agreement",
            "evidence": original_claims
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
    
    planner.run("How tall is Mount Everest?")
    
    stored_evidence = EvidenceRepository.list_by_session(db, planner.session_id)
    stored_claims = {e.claim_text for e in stored_evidence}
    original_claim_texts = {c["claim"] for c in original_claims}
    
    exact_match = stored_claims == original_claim_texts
    
    passed = exact_match
    detail = f"stored={stored_claims}, original={original_claim_texts}, match={exact_match}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.3.6 TEST: Evidence verification_status preserved
# ======================================================================

def test_4_3_6_verification_status_preserved():
    """
    The verification_status should be preserved exactly (AGREEMENT/CONFLICT/SINGLE_SOURCE).
    """
    db = create_test_db()
    
    evidence_items = [
        {"claim": "Claim with agreement", "status": "AGREEMENT", "sources": ["https://a.com", "https://b.com"]},
        {"claim": "Claim from single source", "status": "SINGLE_SOURCE", "sources": ["https://c.com"]},
    ]
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Mixed evidence answer",
            "confidence_level": "MEDIUM",
            "confidence_reason": "Some agreement",
            "evidence": evidence_items
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
    
    planner.run("Test question?")
    
    stored_evidence = EvidenceRepository.list_by_session(db, planner.session_id)
    stored_statuses = {e.verification_status for e in stored_evidence}
    expected_statuses = {"AGREEMENT", "SINGLE_SOURCE"}
    
    passed = stored_statuses == expected_statuses
    detail = f"stored_statuses={stored_statuses}, expected={expected_statuses}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.3.7 TEST: Evidence source count matches original
# ======================================================================

def test_4_3_7_source_count_preserved():
    """
    The number of sources per evidence should match the original.
    """
    db = create_test_db()
    
    evidence_items = [
        {"claim": "Multi-source claim", "status": "AGREEMENT", "sources": ["https://a.com", "https://b.com", "https://c.com"]},
    ]
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Answer",
            "confidence_level": "HIGH",
            "confidence_reason": "OK",
            "evidence": evidence_items
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
    
    planner.run("Test?")
    
    stored_evidence = EvidenceRepository.list_by_session(db, planner.session_id)
    
    original_source_count = len(evidence_items[0]["sources"])
    stored_source_count = len(stored_evidence[0].source_urls) if stored_evidence else 0
    
    passed = stored_source_count == original_source_count
    detail = f"original={original_source_count}, stored={stored_source_count}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.3.8 TEST: Evidence count matches research result
# ======================================================================

def test_4_3_8_evidence_count_matches():
    """
    The number of evidence rows should match the number of claims in research result.
    """
    db = create_test_db()
    
    evidence_items = [
        {"claim": "Claim 1", "status": "AGREEMENT", "sources": ["https://a.com"]},
        {"claim": "Claim 2", "status": "AGREEMENT", "sources": ["https://b.com"]},
        {"claim": "Claim 3", "status": "SINGLE_SOURCE", "sources": ["https://c.com"]},
    ]
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Answer with 3 claims",
            "confidence_level": "HIGH",
            "confidence_reason": "OK",
            "evidence": evidence_items
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
    
    planner.run("Test?")
    
    stored_evidence = EvidenceRepository.list_by_session(db, planner.session_id)
    
    passed = len(stored_evidence) == len(evidence_items)
    detail = f"stored={len(stored_evidence)}, original={len(evidence_items)}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.3.9 TEST: Evidence has valid UUID id
# ======================================================================

def test_4_3_9_evidence_has_valid_id():
    """
    Each evidence row should have a valid UUID id.
    """
    db = create_test_db()
    
    evidence_items = [
        {"claim": "Test claim", "status": "AGREEMENT", "sources": ["https://test.com"]},
    ]
    
    fake_research = FakeResearchAgent([
        {
            "answer": "Test",
            "confidence_level": "HIGH",
            "confidence_reason": "OK",
            "evidence": evidence_items
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
    
    planner.run("Test?")
    
    stored_evidence = db.query(Evidence).all()
    
    all_valid_uuids = True
    for e in stored_evidence:
        try:
            uuid.UUID(str(e.id))
        except ValueError:
            all_valid_uuids = False
            break
    
    passed = all_valid_uuids and len(stored_evidence) > 0
    detail = f"all_valid_uuids={all_valid_uuids}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.3.10 TEST: Multiple sessions have isolated evidence
# ======================================================================

def test_4_3_10_sessions_have_isolated_evidence():
    """
    Evidence from different sessions should not mix.
    """
    db = create_test_db()
    
    # Session 1
    fake_research_1 = FakeResearchAgent([
        {
            "answer": "Answer 1",
            "confidence_level": "HIGH",
            "confidence_reason": "OK",
            "evidence": [{"claim": "Session 1 claim", "status": "AGREEMENT", "sources": ["https://s1.com"]}]
        }
    ])
    
    fake_verification_1 = FakeVerificationAgent([
        {"decision": VerificationDecision.ACCEPT, "reason": "OK", "recommendation": None}
    ])
    
    planner_1 = PlannerAgent(
        research_agent=fake_research_1,
        verification_agent=fake_verification_1,
        db=db,
        max_attempts=3
    )
    planner_1.run("Question 1?")
    session_1_id = planner_1.session_id
    
    # Session 2
    fake_research_2 = FakeResearchAgent([
        {
            "answer": "Answer 2",
            "confidence_level": "HIGH",
            "confidence_reason": "OK",
            "evidence": [
                {"claim": "Session 2 claim A", "status": "AGREEMENT", "sources": ["https://s2a.com"]},
                {"claim": "Session 2 claim B", "status": "AGREEMENT", "sources": ["https://s2b.com"]},
            ]
        }
    ])
    
    fake_verification_2 = FakeVerificationAgent([
        {"decision": VerificationDecision.ACCEPT, "reason": "OK", "recommendation": None}
    ])
    
    planner_2 = PlannerAgent(
        research_agent=fake_research_2,
        verification_agent=fake_verification_2,
        db=db,
        max_attempts=3
    )
    planner_2.run("Question 2?")
    session_2_id = planner_2.session_id
    
    # Verify isolation
    evidence_1 = EvidenceRepository.list_by_session(db, session_1_id)
    evidence_2 = EvidenceRepository.list_by_session(db, session_2_id)
    
    session_1_count = len(evidence_1)
    session_2_count = len(evidence_2)
    
    # Session 1 should have 1 evidence, Session 2 should have 2
    isolated = session_1_count == 1 and session_2_count == 2
    
    # Verify claims are correct for each session
    session_1_claims = {e.claim_text for e in evidence_1}
    session_2_claims = {e.claim_text for e in evidence_2}
    
    no_cross_contamination = (
        "Session 1 claim" in list(session_1_claims)[0] and
        all("Session 2" in c for c in session_2_claims)
    )
    
    passed = isolated and no_cross_contamination
    detail = f"s1_count={session_1_count}, s2_count={session_2_count}, isolated={no_cross_contamination}"
    
    db.close()
    return passed, detail


# ======================================================================
# 4.3.11 TEST: Empty evidence list doesn't create rows
# ======================================================================

def test_4_3_11_empty_evidence_no_rows():
    """
    When research returns empty evidence, no evidence rows should be created.
    """
    db = create_test_db()
    
    fake_research = FakeResearchAgent([
        {
            "answer": "No evidence answer",
            "confidence_level": "LOW",
            "confidence_reason": "No claims found",
            "evidence": []  # Empty evidence
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
    
    planner.run("Obscure question?")
    
    stored_evidence = EvidenceRepository.list_by_session(db, planner.session_id)
    
    passed = len(stored_evidence) == 0
    detail = f"evidence_count={len(stored_evidence)} (expected 0)"
    
    db.close()
    return passed, detail


# ======================================================================
# MAIN TEST RUNNER
# ======================================================================

def run_all_tests():
    print_header()
    
    tests = [
        ("4.3.1", "Evidence has session_id", test_4_3_1_evidence_has_session_id),
        ("4.3.2", "Evidence maps to correct session", test_4_3_2_evidence_maps_to_correct_session),
        ("4.3.3", "No evidence without sources", test_4_3_3_no_evidence_without_sources),
        ("4.3.4", "Source URLs are valid", test_4_3_4_source_urls_are_valid),
        ("4.3.5", "Evidence matches claims exactly", test_4_3_5_evidence_matches_claims_exactly),
        ("4.3.6", "Verification status preserved", test_4_3_6_verification_status_preserved),
        ("4.3.7", "Source count preserved", test_4_3_7_source_count_preserved),
        ("4.3.8", "Evidence count matches", test_4_3_8_evidence_count_matches),
        ("4.3.9", "Evidence has valid UUID", test_4_3_9_evidence_has_valid_id),
        ("4.3.10", "Sessions have isolated evidence", test_4_3_10_sessions_have_isolated_evidence),
        ("4.3.11", "Empty evidence → no rows", test_4_3_11_empty_evidence_no_rows),
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
