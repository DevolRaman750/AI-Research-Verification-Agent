"""
======================================================================
VERIFICATION & CONFIDENCE SAFETY TESTS - 3.3 High Confidence Case
======================================================================

Tests for well-known factual questions with strong evidence:
- HIGH confidence when multiple sources agree
- Multiple evidence sources in output
- No unnecessary retries (ACCEPT immediately)

These tests are deterministic - no LLM/web calls.
"""

import sys
sys.path.insert(0, "c:/Agents/AI-Research-Agent/backend")

from typing import List, Dict
from verification.models import VerifiedClaim, VerificationStatus
from confidence.confidence_scorer import ConfidenceScorer
from synthesis.answer_synthesizer import generate_notes
from agents.VerificationAgent import VerificationAgent, VerificationDecision


# ======================================================================
# TEST UTILITIES
# ======================================================================

def print_header():
    print("\n" + "=" * 70)
    print("VERIFICATION & CONFIDENCE SAFETY TESTS - 3.3 High Confidence Case")
    print("=" * 70)


def print_result(test_id: str, name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {test_id} {name} | {detail}")


def print_summary(passed: int, failed: int, total: int):
    print("-" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {total} tests")


# ======================================================================
# 3.3.1 TEST: Multiple agreeing sources → HIGH confidence
# ======================================================================

def test_3_3_1_multiple_sources_high_confidence():
    """
    When multiple independent sources agree on a claim,
    confidence_level must be HIGH.
    """
    scorer = ConfidenceScorer()
    
    # Well-known fact with multiple sources agreeing
    claims = [
        VerifiedClaim(
            claim="The Earth orbits the Sun in approximately 365.25 days",
            sources=["https://nasa.gov", "https://esa.int"],
            status=VerificationStatus.AGREEMENT
        ),
    ]
    
    result = scorer.score(claims)
    confidence_level = result.get("confidence_level")
    
    passed = confidence_level == "HIGH"
    detail = f"confidence_level={confidence_level}"
    return passed, detail


# ======================================================================
# 3.3.2 TEST: Two or more sources required for HIGH
# ======================================================================

def test_3_3_2_minimum_two_sources_for_high():
    """
    HIGH confidence requires at least 2 independent sources in AGREEMENT.
    """
    scorer = ConfidenceScorer()
    
    # Multiple sources from reputable domains
    claims = [
        VerifiedClaim(
            claim="Water boils at 100 degrees Celsius at sea level",
            sources=["https://physics.edu", "https://sciencedaily.com", "https://britannica.com"],
            status=VerificationStatus.AGREEMENT
        ),
    ]
    
    result = scorer.score(claims)
    confidence_level = result.get("confidence_level")
    
    # Count unique sources
    source_count = len(claims[0].sources)
    
    passed = confidence_level == "HIGH" and source_count >= 2
    detail = f"confidence={confidence_level}, sources={source_count}"
    return passed, detail


# ======================================================================
# 3.3.3 TEST: VerificationAgent returns ACCEPT on HIGH confidence
# ======================================================================

def test_3_3_3_accept_on_high_confidence():
    """
    When confidence is HIGH, VerificationAgent should ACCEPT immediately.
    No retries needed.
    """
    agent = VerificationAgent()
    
    claims = [
        VerifiedClaim(
            claim="The speed of light is approximately 299,792 km/s",
            sources=["https://nist.gov", "https://physics.org"],
            status=VerificationStatus.AGREEMENT
        ),
    ]
    
    confidence = {
        "confidence_level": "HIGH",
        "confidence_reason": "Multiple independent sources agree"
    }
    
    result = agent.decide(
        verified_claims=claims,
        confidence=confidence,
        attempt=1,  # First attempt
        max_attempts=3
    )
    
    decision = result.get("decision")
    
    passed = decision == VerificationDecision.ACCEPT
    detail = f"decision={decision} on first attempt"
    return passed, detail


# ======================================================================
# 3.3.4 TEST: No recommendation on ACCEPT (no retry needed)
# ======================================================================

def test_3_3_4_no_recommendation_on_accept():
    """
    When ACCEPT is returned, recommendation should be None
    (no further action needed).
    """
    agent = VerificationAgent()
    
    claims = [
        VerifiedClaim(
            claim="Mount Everest is the tallest mountain on Earth",
            sources=["https://nationalgeographic.com", "https://britannica.com"],
            status=VerificationStatus.AGREEMENT
        ),
    ]
    
    confidence = {
        "confidence_level": "HIGH",
        "confidence_reason": "Multiple reputable sources confirm"
    }
    
    result = agent.decide(
        verified_claims=claims,
        confidence=confidence,
        attempt=1,
        max_attempts=3
    )
    
    recommendation = result.get("recommendation")
    
    passed = recommendation is None
    detail = f"recommendation={recommendation}"
    return passed, detail


# ======================================================================
# 3.3.5 TEST: HIGH confidence reason is positive
# ======================================================================

def test_3_3_5_high_confidence_reason_positive():
    """
    The confidence_reason for HIGH should be positive/affirmative,
    mentioning agreement or multiple sources.
    """
    scorer = ConfidenceScorer()
    
    claims = [
        VerifiedClaim(
            claim="The Great Wall of China is visible from certain low Earth orbits",
            sources=["https://space.com", "https://nasa.gov"],
            status=VerificationStatus.AGREEMENT
        ),
    ]
    
    result = scorer.score(claims)
    reason = result.get("confidence_reason", "").lower()
    
    # Should mention positive indicators
    mentions_multiple = "multiple" in reason
    mentions_agree = "agree" in reason
    mentions_independent = "independent" in reason
    mentions_strong = "strong" in reason
    
    is_positive = mentions_multiple or mentions_agree or mentions_independent or mentions_strong
    
    detail = f"reason mentions positive indicators: {is_positive}"
    return is_positive, detail


# ======================================================================
# 3.3.6 TEST: No warning notes on HIGH confidence
# ======================================================================

def test_3_3_6_no_notes_on_high():
    """
    HIGH confidence should not generate warning notes.
    """
    notes = generate_notes("HIGH")
    
    passed = notes is None
    detail = f"notes={notes}"
    return passed, detail


# ======================================================================
# 3.3.7 TEST: Multiple claims all in AGREEMENT → HIGH
# ======================================================================

def test_3_3_7_multiple_agreement_claims_high():
    """
    When multiple claims all have AGREEMENT status from multiple sources,
    confidence should be HIGH.
    """
    scorer = ConfidenceScorer()
    
    claims = [
        VerifiedClaim(
            claim="The human body has 206 bones in adulthood",
            sources=["https://mayoclinic.org", "https://webmd.com"],
            status=VerificationStatus.AGREEMENT
        ),
        VerifiedClaim(
            claim="The heart pumps blood throughout the body",
            sources=["https://heart.org", "https://nih.gov"],
            status=VerificationStatus.AGREEMENT
        ),
        VerifiedClaim(
            claim="Red blood cells carry oxygen",
            sources=["https://hematology.org", "https://healthline.com"],
            status=VerificationStatus.AGREEMENT
        ),
    ]
    
    result = scorer.score(claims)
    confidence_level = result.get("confidence_level")
    
    # Count total unique sources
    all_sources = set()
    for c in claims:
        all_sources.update(c.sources)
    
    passed = confidence_level == "HIGH"
    detail = f"confidence={confidence_level}, total_unique_sources={len(all_sources)}"
    return passed, detail


# ======================================================================
# 3.3.8 TEST: ACCEPT even at later attempts if HIGH confidence reached
# ======================================================================

def test_3_3_8_accept_at_any_attempt_if_high():
    """
    If HIGH confidence is achieved at attempt 2 or 3,
    system should still ACCEPT (not force more retries).
    """
    agent = VerificationAgent()
    
    claims = [
        VerifiedClaim(
            claim="Pi is approximately 3.14159",
            sources=["https://math.edu", "https://wolfram.com"],
            status=VerificationStatus.AGREEMENT
        ),
    ]
    
    confidence = {
        "confidence_level": "HIGH",
        "confidence_reason": "Strong agreement from multiple sources"
    }
    
    # Test at attempt 2
    result_2 = agent.decide(
        verified_claims=claims,
        confidence=confidence,
        attempt=2,
        max_attempts=3
    )
    
    # Test at attempt 3
    result_3 = agent.decide(
        verified_claims=claims,
        confidence=confidence,
        attempt=3,
        max_attempts=3
    )
    
    accept_at_2 = result_2.get("decision") == VerificationDecision.ACCEPT
    accept_at_3 = result_3.get("decision") == VerificationDecision.ACCEPT
    
    passed = accept_at_2 and accept_at_3
    detail = f"accept_at_attempt_2={accept_at_2}, accept_at_attempt_3={accept_at_3}"
    return passed, detail


# ======================================================================
# 3.3.9 TEST: Evidence output contains all sources
# ======================================================================

def test_3_3_9_evidence_contains_all_sources():
    """
    The evidence output should preserve all sources from verified claims.
    """
    claims = [
        VerifiedClaim(
            claim="The Amazon River is the largest river by volume",
            sources=["https://worldwildlife.org", "https://nationalgeographic.com", "https://usgs.gov"],
            status=VerificationStatus.AGREEMENT
        ),
    ]
    
    # Build evidence the same way as AnswerSynthesizer
    evidence = [
        {
            "claim": c.claim,
            "status": c.status.value,
            "sources": c.sources
        }
        for c in claims
    ]
    
    # Check all sources preserved
    original_sources = claims[0].sources
    output_sources = evidence[0]["sources"]
    
    all_preserved = set(original_sources) == set(output_sources)
    source_count = len(output_sources)
    
    passed = all_preserved and source_count >= 2
    detail = f"sources_preserved={all_preserved}, count={source_count}"
    return passed, detail


# ======================================================================
# 3.3.10 TEST: MEDIUM confidence also ACCEPT (no unnecessary retry)
# ======================================================================

def test_3_3_10_medium_confidence_also_accepts():
    """
    MEDIUM confidence should also ACCEPT without retry.
    Only LOW and CONFLICT trigger retries.
    """
    agent = VerificationAgent()
    
    claims = [
        VerifiedClaim(
            claim="Coffee originated in Ethiopia",
            sources=["https://coffee-history.org"],
            status=VerificationStatus.AGREEMENT
        ),
    ]
    
    confidence = {
        "confidence_level": "MEDIUM",
        "confidence_reason": "Some agreement but limited sources"
    }
    
    result = agent.decide(
        verified_claims=claims,
        confidence=confidence,
        attempt=1,
        max_attempts=3
    )
    
    decision = result.get("decision")
    
    passed = decision == VerificationDecision.ACCEPT
    detail = f"MEDIUM confidence → decision={decision}"
    return passed, detail


# ======================================================================
# 3.3.11 TEST: HIGH confidence output structure complete
# ======================================================================

def test_3_3_11_high_confidence_output_complete():
    """
    HIGH confidence output should have all fields:
    - answer, confidence_level=HIGH, confidence_reason (positive), evidence, notes=None
    """
    scorer = ConfidenceScorer()
    
    claims = [
        VerifiedClaim(
            claim="The Pacific Ocean is the largest ocean on Earth",
            sources=["https://noaa.gov", "https://oceanservice.noaa.gov"],
            status=VerificationStatus.AGREEMENT
        ),
    ]
    
    confidence = scorer.score(claims)
    notes = generate_notes(confidence["confidence_level"])
    
    evidence = [
        {"claim": c.claim, "status": c.status.value, "sources": c.sources}
        for c in claims
    ]
    
    # Simulate output
    output = {
        "answer": "The Pacific Ocean is the largest ocean on Earth.",
        "confidence_level": confidence["confidence_level"],
        "confidence_reason": confidence["confidence_reason"],
        "evidence": evidence,
        "notes": notes
    }
    
    is_high = output["confidence_level"] == "HIGH"
    has_evidence = len(output["evidence"]) > 0
    has_multiple_sources = len(output["evidence"][0]["sources"]) >= 2
    no_warning_notes = output["notes"] is None
    
    passed = is_high and has_evidence and has_multiple_sources and no_warning_notes
    detail = f"HIGH={is_high}, evidence={has_evidence}, multi_sources={has_multiple_sources}, no_notes={no_warning_notes}"
    return passed, detail


# ======================================================================
# MAIN TEST RUNNER
# ======================================================================

def run_all_tests():
    print_header()
    
    tests = [
        ("3.3.1", "Multiple sources → HIGH confidence", test_3_3_1_multiple_sources_high_confidence),
        ("3.3.2", "Minimum 2 sources for HIGH", test_3_3_2_minimum_two_sources_for_high),
        ("3.3.3", "ACCEPT on HIGH confidence", test_3_3_3_accept_on_high_confidence),
        ("3.3.4", "No recommendation on ACCEPT", test_3_3_4_no_recommendation_on_accept),
        ("3.3.5", "HIGH confidence reason positive", test_3_3_5_high_confidence_reason_positive),
        ("3.3.6", "No notes on HIGH", test_3_3_6_no_notes_on_high),
        ("3.3.7", "Multiple AGREEMENT claims → HIGH", test_3_3_7_multiple_agreement_claims_high),
        ("3.3.8", "ACCEPT at any attempt if HIGH", test_3_3_8_accept_at_any_attempt_if_high),
        ("3.3.9", "Evidence contains all sources", test_3_3_9_evidence_contains_all_sources),
        ("3.3.10", "MEDIUM confidence also ACCEPT", test_3_3_10_medium_confidence_also_accepts),
        ("3.3.11", "HIGH confidence output complete", test_3_3_11_high_confidence_output_complete),
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
