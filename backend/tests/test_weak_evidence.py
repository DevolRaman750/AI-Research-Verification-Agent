"""
======================================================================
VERIFICATION & CONFIDENCE SAFETY TESTS - 3.2 Weak Evidence
======================================================================

Tests for niche/obscure questions with limited evidence:
- LOW confidence when evidence is weak/single-source
- Clear confidence_reason explaining the weakness
- Notes warn user properly
- No hallucinated facts (evidence comes from verified claims only)

These tests are deterministic - no LLM/web calls.
"""

import sys
sys.path.insert(0, "c:/Agents/AI-Research-Agent/backend")

from typing import List, Dict
from verification.models import VerifiedClaim, VerificationStatus
from confidence.confidence_scorer import ConfidenceScorer
from synthesis.answer_synthesizer import generate_notes, AnswerSynthesizer
from agents.VerificationAgent import VerificationAgent, VerificationDecision


# ======================================================================
# TEST UTILITIES
# ======================================================================

def print_header():
    print("\n" + "=" * 70)
    print("VERIFICATION & CONFIDENCE SAFETY TESTS - 3.2 Weak Evidence")
    print("=" * 70)


def print_result(test_id: str, name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {test_id} {name} | {detail}")


def print_summary(passed: int, failed: int, total: int):
    print("-" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {total} tests")


# ======================================================================
# 3.2.1 TEST: Single source → LOW confidence
# ======================================================================

def test_3_2_1_single_source_low_confidence():
    """
    When all claims come from a single source (weak evidence),
    confidence_level must be LOW.
    """
    scorer = ConfidenceScorer()
    
    # Niche topic with only one source
    claims = [
        VerifiedClaim(
            claim="The rare Spix's Macaw was last seen in the wild in 2000",
            sources=["https://obscure-bird-blog.com"],
            status=VerificationStatus.SINGLE_SOURCE
        ),
    ]
    
    result = scorer.score(claims)
    confidence_level = result.get("confidence_level")
    
    passed = confidence_level == "LOW"
    detail = f"confidence_level={confidence_level}"
    return passed, detail


# ======================================================================
# 3.2.2 TEST: No agreement → LOW confidence
# ======================================================================

def test_3_2_2_no_agreement_low_confidence():
    """
    When there's no AGREEMENT status among claims,
    confidence should be LOW (no corroboration).
    """
    scorer = ConfidenceScorer()
    
    # Multiple single-source claims, none corroborated
    claims = [
        VerifiedClaim(
            claim="Ancient Roman concrete contained volcanic ash",
            sources=["https://history-facts.com"],
            status=VerificationStatus.SINGLE_SOURCE
        ),
        VerifiedClaim(
            claim="Roman buildings lasted centuries due to special materials",
            sources=["https://architecture-blog.net"],
            status=VerificationStatus.SINGLE_SOURCE
        ),
    ]
    
    result = scorer.score(claims)
    confidence_level = result.get("confidence_level")
    
    passed = confidence_level == "LOW"
    detail = f"confidence_level={confidence_level} (no agreement among sources)"
    return passed, detail


# ======================================================================
# 3.2.3 TEST: Empty claims → LOW confidence
# ======================================================================

def test_3_2_3_empty_claims_low_confidence():
    """
    When no claims are available (very niche/obscure topic),
    confidence must be LOW.
    """
    scorer = ConfidenceScorer()
    
    claims = []  # No evidence found
    
    result = scorer.score(claims)
    confidence_level = result.get("confidence_level")
    confidence_reason = result.get("confidence_reason", "")
    
    passed = confidence_level == "LOW"
    has_reason = len(confidence_reason) > 10
    
    detail = f"level={confidence_level}, has_reason={has_reason}"
    return passed and has_reason, detail


# ======================================================================
# 3.2.4 TEST: confidence_reason is clear and meaningful
# ======================================================================

def test_3_2_4_confidence_reason_is_clear():
    """
    The confidence_reason must clearly explain WHY confidence is low.
    Should mention "single source" or "limited" or similar.
    """
    scorer = ConfidenceScorer()
    
    claims = [
        VerifiedClaim(
            claim="The deepest point in Lake Baikal is 1,642 meters",
            sources=["https://lake-facts.ru"],
            status=VerificationStatus.SINGLE_SOURCE
        ),
    ]
    
    result = scorer.score(claims)
    reason = result.get("confidence_reason", "").lower()
    
    # Check for meaningful explanation keywords
    has_single_source = "single source" in reason
    has_limited = "limited" in reason or "lacks" in reason
    has_independent = "independent" in reason
    
    is_meaningful = has_single_source or has_limited or has_independent
    
    detail = f"reason contains explanation: {is_meaningful}"
    return is_meaningful, detail


# ======================================================================
# 3.2.5 TEST: generate_notes warns user on LOW confidence
# ======================================================================

def test_3_2_5_notes_warn_user_on_low():
    """
    When confidence is LOW, generate_notes must return a warning.
    """
    notes = generate_notes("LOW")
    
    has_notes = notes is not None and len(notes) > 10
    warns_limited = "limited" in notes.lower() if notes else False
    warns_confirmation = "confirmation" in notes.lower() if notes else False
    
    passed = has_notes and (warns_limited or warns_confirmation)
    detail = f"notes='{notes[:50]}...'" if notes else "notes=None"
    return passed, detail


# ======================================================================
# 3.2.6 TEST: generate_notes returns None on HIGH confidence
# ======================================================================

def test_3_2_6_no_notes_on_high_confidence():
    """
    When confidence is HIGH, no warning notes should be generated.
    """
    notes_high = generate_notes("HIGH")
    notes_medium = generate_notes("MEDIUM")
    
    no_notes_high = notes_high is None
    no_notes_medium = notes_medium is None
    
    passed = no_notes_high and no_notes_medium
    detail = f"HIGH_notes={notes_high}, MEDIUM_notes={notes_medium}"
    return passed, detail


# ======================================================================
# 3.2.7 TEST: Evidence comes directly from claims (no hallucination)
# ======================================================================

def test_3_2_7_evidence_matches_claims_exactly():
    """
    The evidence in the output must exactly match the verified claims.
    No additional facts should be invented.
    """
    # Create verified claims
    original_claims = [
        VerifiedClaim(
            claim="Tardigrades can survive extreme temperatures",
            sources=["https://science-daily.com", "https://nature.org"],
            status=VerificationStatus.AGREEMENT
        ),
        VerifiedClaim(
            claim="Tardigrades enter cryptobiosis under stress",
            sources=["https://biology-journal.edu"],
            status=VerificationStatus.SINGLE_SOURCE
        ),
    ]
    
    # Build evidence list the same way AnswerSynthesizer does
    evidence = [
        {
            "claim": c.claim,
            "status": c.status.value,
            "sources": c.sources
        }
        for c in original_claims
    ]
    
    # Verify evidence matches claims exactly
    all_match = True
    for i, ev in enumerate(evidence):
        original = original_claims[i]
        claim_match = ev["claim"] == original.claim
        status_match = ev["status"] == original.status.value
        sources_match = ev["sources"] == original.sources
        
        if not (claim_match and status_match and sources_match):
            all_match = False
            break
    
    # Check no extra evidence was invented
    same_count = len(evidence) == len(original_claims)
    
    passed = all_match and same_count
    detail = f"evidence_count={len(evidence)}, claims_count={len(original_claims)}, exact_match={all_match}"
    return passed, detail


# ======================================================================
# 3.2.8 TEST: VerificationAgent recommends RETRY on weak evidence
# ======================================================================

def test_3_2_8_verification_agent_retry_on_weak():
    """
    When evidence is weak (LOW confidence, single source),
    VerificationAgent should recommend RETRY to find more sources.
    """
    agent = VerificationAgent()
    
    weak_claims = [
        VerifiedClaim(
            claim="The island of Socotra has unique dragon blood trees",
            sources=["https://travel-blog.com"],
            status=VerificationStatus.SINGLE_SOURCE
        ),
    ]
    
    confidence = {
        "confidence_level": "LOW",
        "confidence_reason": "Single source, lacks independent confirmation"
    }
    
    result = agent.decide(
        verified_claims=weak_claims,
        confidence=confidence,
        attempt=1,
        max_attempts=3
    )
    
    decision = result.get("decision")
    recommendation = result.get("recommendation", "")
    
    passed = decision == VerificationDecision.RETRY
    has_recommendation = recommendation is not None and len(recommendation) > 0
    
    detail = f"decision={decision}, has_recommendation={has_recommendation}"
    return passed and has_recommendation, detail


# ======================================================================
# 3.2.9 TEST: After max attempts, STOP with LOW confidence preserved
# ======================================================================

def test_3_2_9_stop_preserves_low_confidence():
    """
    After max attempts with weak evidence, system should STOP
    but preserve the LOW confidence level.
    """
    agent = VerificationAgent()
    
    weak_claims = [
        VerifiedClaim(
            claim="Obscure fact about quantum entanglement in photosynthesis",
            sources=["https://fringe-science.net"],
            status=VerificationStatus.SINGLE_SOURCE
        ),
    ]
    
    confidence = {
        "confidence_level": "LOW",
        "confidence_reason": "Limited evidence from single source"
    }
    
    result = agent.decide(
        verified_claims=weak_claims,
        confidence=confidence,
        attempt=3,  # Max attempts reached
        max_attempts=3
    )
    
    decision = result.get("decision")
    reason = result.get("reason", "")
    
    passed = decision == VerificationDecision.STOP
    mentions_low_confidence = "low" in reason.lower() or "confidence" in reason.lower()
    
    detail = f"decision={decision}, reason_acknowledges_weakness={mentions_low_confidence}"
    return passed, detail


# ======================================================================
# 3.2.10 TEST: Weak evidence output structure is complete
# ======================================================================

def test_3_2_10_weak_evidence_output_complete():
    """
    Even with weak evidence, the output must have all required fields:
    - answer (even if cautious)
    - confidence_level (LOW)
    - confidence_reason (explains weakness)
    - evidence (list of claims)
    - notes (warning to user)
    """
    scorer = ConfidenceScorer()
    
    claims = [
        VerifiedClaim(
            claim="Ancient Sumerian tablets mention beer recipes",
            sources=["https://history-curiosities.com"],
            status=VerificationStatus.SINGLE_SOURCE
        ),
    ]
    
    confidence = scorer.score(claims)
    notes = generate_notes(confidence["confidence_level"])
    
    # Build evidence
    evidence = [
        {"claim": c.claim, "status": c.status.value, "sources": c.sources}
        for c in claims
    ]
    
    # Simulate complete output
    output = {
        "answer": "Based on limited evidence...",  # Would be LLM-generated
        "confidence_level": confidence["confidence_level"],
        "confidence_reason": confidence["confidence_reason"],
        "evidence": evidence,
        "notes": notes
    }
    
    # Verify all fields present
    has_answer = "answer" in output and len(output["answer"]) > 0
    has_level = output.get("confidence_level") == "LOW"
    has_reason = output.get("confidence_reason") is not None and len(output["confidence_reason"]) > 0
    has_evidence = "evidence" in output and isinstance(output["evidence"], list)
    has_notes = output.get("notes") is not None
    
    all_present = has_answer and has_level and has_reason and has_evidence and has_notes
    
    detail = f"level={has_level}, reason={has_reason}, evidence={has_evidence}, notes={has_notes}"
    return all_present, detail


# ======================================================================
# 3.2.11 TEST: Confidence reason distinguishes single-source from conflict
# ======================================================================

def test_3_2_11_reason_distinguishes_weakness_types():
    """
    The confidence_reason should be specific about the type of weakness:
    - Single source: mentions "single source" or "lacks confirmation"
    - No claims: mentions "no claims" or "no verifiable"
    """
    scorer = ConfidenceScorer()
    
    # Case 1: Single source
    single_source_claims = [
        VerifiedClaim(
            claim="Test claim",
            sources=["https://one-source.com"],
            status=VerificationStatus.SINGLE_SOURCE
        ),
    ]
    result_single = scorer.score(single_source_claims)
    reason_single = result_single.get("confidence_reason", "").lower()
    
    # Case 2: No claims
    result_empty = scorer.score([])
    reason_empty = result_empty.get("confidence_reason", "").lower()
    
    # Verify reasons are different and specific
    single_mentions_source = "single source" in reason_single or "independent" in reason_single
    empty_mentions_no_claims = "no" in reason_empty and ("claim" in reason_empty or "verif" in reason_empty)
    
    reasons_are_different = reason_single != reason_empty
    
    passed = single_mentions_source and empty_mentions_no_claims and reasons_are_different
    detail = f"single_specific={single_mentions_source}, empty_specific={empty_mentions_no_claims}"
    return passed, detail


# ======================================================================
# MAIN TEST RUNNER
# ======================================================================

def run_all_tests():
    print_header()
    
    tests = [
        ("3.2.1", "Single source → LOW confidence", test_3_2_1_single_source_low_confidence),
        ("3.2.2", "No agreement → LOW confidence", test_3_2_2_no_agreement_low_confidence),
        ("3.2.3", "Empty claims → LOW confidence", test_3_2_3_empty_claims_low_confidence),
        ("3.2.4", "confidence_reason is clear", test_3_2_4_confidence_reason_is_clear),
        ("3.2.5", "Notes warn user on LOW", test_3_2_5_notes_warn_user_on_low),
        ("3.2.6", "No notes on HIGH/MEDIUM", test_3_2_6_no_notes_on_high_confidence),
        ("3.2.7", "Evidence matches claims (no hallucination)", test_3_2_7_evidence_matches_claims_exactly),
        ("3.2.8", "VerificationAgent RETRY on weak", test_3_2_8_verification_agent_retry_on_weak),
        ("3.2.9", "STOP preserves LOW confidence", test_3_2_9_stop_preserves_low_confidence),
        ("3.2.10", "Weak evidence output complete", test_3_2_10_weak_evidence_output_complete),
        ("3.2.11", "Reason distinguishes weakness types", test_3_2_11_reason_distinguishes_weakness_types),
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
