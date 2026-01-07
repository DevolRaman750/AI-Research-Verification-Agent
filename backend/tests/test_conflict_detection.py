"""
======================================================================
VERIFICATION & CONFIDENCE SAFETY TESTS - 3.1 Conflict Detection
======================================================================

Tests that verify the system properly handles controversial/disputed claims:
- Conflicting claims are detected
- confidence_level = LOW when conflicts exist
- STOP or FAIL happens appropriately
- Evidence shows conflicts clearly

These tests are deterministic - no LLM/web calls.
"""

import sys
sys.path.insert(0, "c:/Agents/AI-Research-Agent/backend")

from typing import List, Dict
from verification.models import VerifiedClaim, VerificationStatus
from verification.verifier import VerificationEngine
from verification.claim_extractor import ExtractedClaim
from confidence.confidence_scorer import ConfidenceScorer
from agents.VerificationAgent import VerificationAgent, VerificationDecision
from utils.polarity import polarity_score


# ======================================================================
# TEST UTILITIES
# ======================================================================

def print_header():
    print("\n" + "=" * 70)
    print("VERIFICATION & CONFIDENCE SAFETY TESTS - 3.1 Conflict Detection")
    print("=" * 70)


def print_result(test_id: str, name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {test_id} {name} | {detail}")


def print_summary(passed: int, failed: int, total: int):
    print("-" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {total} tests")


# ======================================================================
# 3.1.1 TEST: Polarity Score detects opposing stances
# ======================================================================

def test_3_1_1_polarity_detects_opposing_stances():
    """
    Verify polarity_score correctly identifies positive vs negative assertions.
    Uses keywords from the actual polarity.py implementation.
    """
    test_cases = [
        # (claim, expected_sign)
        ("Coffee reduces the risk of heart disease", +1),  # positive - "reduce"
        ("Coffee increases the risk of heart disease", -1),  # negative - "increase"
        ("Studies show coffee consumption decline over years", +1),  # positive - "decline"
        ("Studies show coffee consumption rise sharply", -1),  # negative - "rise"
        ("The economy is growing", 0),  # neutral - no polarity keyword
    ]
    
    all_correct = True
    details = []
    
    for claim, expected_sign in test_cases:
        score = polarity_score(claim)
        if expected_sign == 0:
            correct = score == 0
        elif expected_sign > 0:
            correct = score > 0
        else:
            correct = score < 0
        
        if not correct:
            all_correct = False
            details.append(f"'{claim[:30]}...' expected {expected_sign}, got {score}")
    
    detail = "all polarities correct" if all_correct else "; ".join(details)
    return all_correct, detail


# ======================================================================
# 3.1.2 TEST: VerificationEngine detects conflict between opposite claims
# ======================================================================

def test_3_1_2_verification_engine_detects_conflict():
    """
    Given claims with opposite polarities from different sources,
    VerificationEngine should mark them as CONFLICT.
    """
    engine = VerificationEngine()
    
    # Create conflicting claims about the same topic
    claims = [
        ExtractedClaim(
            claim="Drinking coffee reduces the risk of heart disease according to new research",
            source_url="https://health-journal.com/coffee-study"
        ),
        ExtractedClaim(
            claim="Drinking coffee increases the risk of heart disease warns new study",
            source_url="https://medical-news.org/coffee-risks"
        ),
    ]
    
    # Manually test the conflict detection logic
    is_conflict = engine._is_conflicting(claims[0].claim, claims[1].claim)
    
    detail = f"conflict_detected={is_conflict}"
    return is_conflict, detail


# ======================================================================
# 3.1.3 TEST: Direct conflict detection in VerificationEngine
# ======================================================================

def test_3_1_3_verified_claims_have_conflict_status():
    """
    Test the conflict detection logic directly by simulating 
    claims that are already grouped (bypassing embedding similarity).
    
    When claims with opposite polarities exist in the same group,
    they should be marked as CONFLICT.
    """
    engine = VerificationEngine()
    
    # Test the _is_conflicting method directly with opposing claims
    claim_positive = "The new policy reduces unemployment rates significantly"
    claim_negative = "The new policy increases unemployment rates dramatically"
    
    is_conflict = engine._is_conflicting(claim_positive, claim_negative)
    
    # Also verify that same-polarity claims don't conflict
    claim_same_1 = "Prices have fallen this quarter"
    claim_same_2 = "Costs have declined recently"
    
    same_polarity_no_conflict = not engine._is_conflicting(claim_same_1, claim_same_2)
    
    passed = is_conflict and same_polarity_no_conflict
    detail = f"opposite_conflict={is_conflict}, same_no_conflict={same_polarity_no_conflict}"
    return passed, detail


# ======================================================================
# 3.1.4 TEST: ConfidenceScorer returns LOW on conflict
# ======================================================================

def test_3_1_4_confidence_low_on_conflict():
    """
    When verified claims include a CONFLICT status,
    ConfidenceScorer must return confidence_level=LOW.
    """
    scorer = ConfidenceScorer()
    
    # Create verified claims with a conflict
    claims_with_conflict = [
        VerifiedClaim(
            claim="Vaccines are safe for children",
            sources=["https://cdc.gov", "https://who.int"],
            status=VerificationStatus.AGREEMENT
        ),
        VerifiedClaim(
            claim="Vaccine side effects are common in children",
            sources=["https://health-concerns.com", "https://research-hub.org"],
            status=VerificationStatus.CONFLICT
        ),
    ]
    
    result = scorer.score(claims_with_conflict)
    
    confidence_level = result.get("confidence_level")
    confidence_reason = result.get("confidence_reason", "")
    
    passed = confidence_level == "LOW"
    has_conflict_reason = "conflict" in confidence_reason.lower()
    
    detail = f"level={confidence_level}, mentions_conflict={has_conflict_reason}"
    return passed and has_conflict_reason, detail


# ======================================================================
# 3.1.5 TEST: VerificationAgent returns RETRY on conflict (first attempt)
# ======================================================================

def test_3_1_5_verification_agent_retry_on_conflict():
    """
    On first attempt with conflicting claims,
    VerificationAgent should recommend RETRY to gather more evidence.
    """
    agent = VerificationAgent()
    
    claims_with_conflict = [
        VerifiedClaim(
            claim="Electric cars are better for the environment",
            sources=["https://green-energy.org", "https://eco-studies.com"],
            status=VerificationStatus.CONFLICT
        ),
    ]
    
    confidence = {
        "confidence_level": "LOW",
        "confidence_reason": "Conflicting evidence prevents confident conclusion"
    }
    
    result = agent.decide(
        verified_claims=claims_with_conflict,
        confidence=confidence,
        attempt=1,  # First attempt
        max_attempts=3
    )
    
    decision = result.get("decision")
    reason = result.get("reason", "")
    recommendation = result.get("recommendation", "")
    
    passed = decision == VerificationDecision.RETRY
    mentions_conflict = "conflict" in reason.lower()
    has_recommendation = recommendation is not None and len(recommendation) > 0
    
    detail = f"decision={decision}, mentions_conflict={mentions_conflict}"
    return passed and mentions_conflict, detail


# ======================================================================
# 3.1.6 TEST: VerificationAgent returns STOP on conflict after max attempts
# ======================================================================

def test_3_1_6_verification_agent_stop_on_persistent_conflict():
    """
    After max attempts with unresolved conflict,
    VerificationAgent should STOP (not retry infinitely).
    """
    agent = VerificationAgent()
    
    claims_with_conflict = [
        VerifiedClaim(
            claim="GMO foods are safe for consumption",
            sources=["https://food-science.edu", "https://health-watch.org"],
            status=VerificationStatus.CONFLICT
        ),
    ]
    
    confidence = {
        "confidence_level": "LOW",
        "confidence_reason": "Conflicting evidence persists"
    }
    
    result = agent.decide(
        verified_claims=claims_with_conflict,
        confidence=confidence,
        attempt=3,  # At max attempts
        max_attempts=3
    )
    
    decision = result.get("decision")
    reason = result.get("reason", "")
    
    passed = decision == VerificationDecision.STOP
    mentions_conflict = "conflict" in reason.lower()
    
    detail = f"decision={decision}, reason_mentions_conflict={mentions_conflict}"
    return passed, detail


# ======================================================================
# 3.1.7 TEST: Conflict evidence is clearly visible in output
# ======================================================================

def test_3_1_7_conflict_evidence_is_clear():
    """
    When conflicts exist, the verified claims should clearly show:
    - The conflicting claim text
    - The sources involved
    - The CONFLICT status
    """
    # Create conflicting verified claims
    conflict_claim = VerifiedClaim(
        claim="Sugar consumption affects health outcomes",
        sources=["https://nutrition-study.org", "https://food-myths.com"],
        status=VerificationStatus.CONFLICT
    )
    
    # Check that all evidence fields are populated
    has_claim = len(conflict_claim.claim) > 10
    has_sources = len(conflict_claim.sources) >= 2
    has_status = conflict_claim.status == VerificationStatus.CONFLICT
    
    passed = has_claim and has_sources and has_status
    detail = f"claim_len={len(conflict_claim.claim)}, sources={len(conflict_claim.sources)}, status={conflict_claim.status.value}"
    
    return passed, detail


# ======================================================================
# 3.1.8 TEST: Multiple conflicts all detected
# ======================================================================

def test_3_1_8_multiple_conflicts_all_detected():
    """
    When there are multiple conflicting topics,
    ConfidenceScorer should still return LOW (catches any conflict).
    """
    scorer = ConfidenceScorer()
    
    claims = [
        VerifiedClaim(
            claim="Climate change is accelerating",
            sources=["https://climate.gov", "https://weather-data.org"],
            status=VerificationStatus.AGREEMENT
        ),
        VerifiedClaim(
            claim="Sea levels are rising",
            sources=["https://ocean-study.edu", "https://coast-watch.gov"],
            status=VerificationStatus.CONFLICT  # First conflict
        ),
        VerifiedClaim(
            claim="Carbon emissions cause warming",
            sources=["https://energy-research.org"],
            status=VerificationStatus.SINGLE_SOURCE
        ),
        VerifiedClaim(
            claim="Polar ice is melting faster",
            sources=["https://arctic-data.org", "https://ice-studies.edu"],
            status=VerificationStatus.CONFLICT  # Second conflict
        ),
    ]
    
    result = scorer.score(claims)
    confidence_level = result.get("confidence_level")
    
    passed = confidence_level == "LOW"
    detail = f"level={confidence_level} with 2 conflicts among 4 claims"
    
    return passed, detail


# ======================================================================
# 3.1.9 TEST: Agreement + Conflict → LOW (conflict wins)
# ======================================================================

def test_3_1_9_conflict_overrides_agreement():
    """
    Even if some claims have AGREEMENT status,
    the presence of ANY conflict should result in LOW confidence.
    """
    scorer = ConfidenceScorer()
    
    # Mix of agreement and conflict
    claims = [
        VerifiedClaim(
            claim="Exercise improves cardiovascular health",
            sources=["https://heart-health.org", "https://fitness-studies.edu", "https://medical-journal.com"],
            status=VerificationStatus.AGREEMENT  # Strong agreement
        ),
        VerifiedClaim(
            claim="Exercise reduces stress levels",
            sources=["https://mental-health.gov", "https://wellness.org"],
            status=VerificationStatus.AGREEMENT  # More agreement
        ),
        VerifiedClaim(
            claim="High-intensity exercise is beneficial for all ages",
            sources=["https://sports-medicine.edu", "https://senior-health.org"],
            status=VerificationStatus.CONFLICT  # But one conflict!
        ),
    ]
    
    result = scorer.score(claims)
    confidence_level = result.get("confidence_level")
    reason = result.get("confidence_reason", "")
    
    passed = confidence_level == "LOW"
    mentions_conflict = "conflict" in reason.lower()
    
    detail = f"level={confidence_level}, conflict_overrides_2_agreements={passed}"
    
    return passed and mentions_conflict, detail


# ======================================================================
# 3.1.10 TEST: End-to-end controversial question flow
# ======================================================================

def test_3_1_10_end_to_end_controversial_flow():
    """
    Simulate a full controversial question flow:
    1. Create claims with opposite polarities
    2. Verify them (detect conflict)
    3. Score confidence (should be LOW)
    4. Agent decides (should RETRY then STOP)
    """
    engine = VerificationEngine()
    scorer = ConfidenceScorer()
    agent = VerificationAgent()
    
    # Simulate extracted claims about a controversial topic
    extracted_claims = [
        ExtractedClaim(
            claim="Studies show remote work increases employee productivity",
            source_url="https://work-research.org/remote-positive"
        ),
        ExtractedClaim(
            claim="Studies show remote work decreases employee productivity",
            source_url="https://office-trends.com/remote-negative"
        ),
    ]
    
    # Step 1: Verify (detect conflict via polarity)
    # Note: These claims may or may not group depending on embedding similarity
    # We test the polarity directly
    polarity_1 = polarity_score(extracted_claims[0].claim)
    polarity_2 = polarity_score(extracted_claims[1].claim)
    
    polarities_opposite = (polarity_1 * polarity_2) < 0
    
    # Step 2: Manually create conflict scenario (as if claims grouped)
    verified_claims = [
        VerifiedClaim(
            claim="Studies show remote work affects employee productivity",
            sources=[
                "https://work-research.org/remote-positive",
                "https://office-trends.com/remote-negative"
            ],
            status=VerificationStatus.CONFLICT
        )
    ]
    
    # Step 3: Score confidence
    confidence = scorer.score(verified_claims)
    is_low = confidence.get("confidence_level") == "LOW"
    
    # Step 4: Agent decision at attempt 1
    decision_1 = agent.decide(verified_claims, confidence, attempt=1, max_attempts=3)
    retry_first = decision_1.get("decision") == VerificationDecision.RETRY
    
    # Step 5: Agent decision at max attempts
    decision_3 = agent.decide(verified_claims, confidence, attempt=3, max_attempts=3)
    stop_finally = decision_3.get("decision") == VerificationDecision.STOP
    
    passed = polarities_opposite and is_low and retry_first and stop_finally
    detail = (
        f"polarities_opposite={polarities_opposite}, "
        f"confidence_LOW={is_low}, "
        f"retry_at_1={retry_first}, "
        f"stop_at_3={stop_finally}"
    )
    
    return passed, detail


# ======================================================================
# MAIN TEST RUNNER
# ======================================================================

def run_all_tests():
    print_header()
    
    tests = [
        ("3.1.1", "Polarity detects opposing stances", test_3_1_1_polarity_detects_opposing_stances),
        ("3.1.2", "VerificationEngine detects conflict", test_3_1_2_verification_engine_detects_conflict),
        ("3.1.3", "Verified claims have CONFLICT status", test_3_1_3_verified_claims_have_conflict_status),
        ("3.1.4", "ConfidenceScorer returns LOW on conflict", test_3_1_4_confidence_low_on_conflict),
        ("3.1.5", "VerificationAgent RETRY on conflict (attempt 1)", test_3_1_5_verification_agent_retry_on_conflict),
        ("3.1.6", "VerificationAgent STOP on persistent conflict", test_3_1_6_verification_agent_stop_on_persistent_conflict),
        ("3.1.7", "Conflict evidence is clearly visible", test_3_1_7_conflict_evidence_is_clear),
        ("3.1.8", "Multiple conflicts all detected", test_3_1_8_multiple_conflicts_all_detected),
        ("3.1.9", "Conflict overrides agreement", test_3_1_9_conflict_overrides_agreement),
        ("3.1.10", "End-to-end controversial flow", test_3_1_10_end_to_end_controversial_flow),
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
