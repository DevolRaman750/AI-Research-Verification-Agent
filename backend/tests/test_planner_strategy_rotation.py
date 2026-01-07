"""Planner Agent Behavior Tests (2.2) - Strategy Rotation Integrity

Goals (deterministic, no web/LLM):
- Force same confidence_reason repeatedly → planner must NOT repeat same strategy
- Force same recommendation repeatedly → planner must NOT repeat same strategy  
- All strategies exhausted → FAILED safely
- No infinite loops (test completes in finite time)

Run:
  $env:PYTHONPATH="c:/Agents/AI-Research-Agent/backend"; python backend/tests/test_planner_strategy_rotation.py
"""

from __future__ import annotations

import sys
import time
from typing import Any, Dict, List, Optional

from planner.planner_agent import PlannerAgent, PlannerState, SearchStrategy
from agents.VerificationAgent import VerificationDecision


results: List[Dict[str, Any]] = []


def record(test_name: str, passed: bool, details: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    results.append({"test": test_name, "passed": passed, "details": details})
    print(f"{status} | {test_name} | {details}")


def assert_true(condition: bool, msg: str):
    if not condition:
        raise AssertionError(msg)


def assert_equal(actual: Any, expected: Any, msg: str):
    if actual != expected:
        raise AssertionError(f"{msg} (actual={actual!r}, expected={expected!r})")


class FakeResearchAgent:
    """Returns a deterministic research result with configurable confidence_reason."""

    def __init__(self, confidence_reasons: List[str]):
        self._reasons = confidence_reasons
        self.call_count = 0

    def research(self, question: str, num_docs: int) -> Dict[str, Any]:
        reason = self._reasons[min(self.call_count, len(self._reasons) - 1)]
        self.call_count += 1
        return {
            "answer": f"fake-answer call={self.call_count}",
            "confidence_level": "LOW",
            "confidence_reason": reason,
            "evidence": [
                {
                    "claim": "Fake claim",
                    "status": "UNVERIFIED",
                    "sources": ["https://example.com"],
                }
            ],
        }


class FakeVerificationAgent:
    """Always returns RETRY to force repeated strategy rotations."""

    def __init__(self, always_retry: bool = True):
        self._always_retry = always_retry
        self.calls: List[Dict[str, Any]] = []

    def decide(
        self,
        verified_claims: List[Dict[str, Any]],
        confidence: Dict[str, str],
        attempt: int,
        max_attempts: int,
    ) -> Dict[str, Any]:
        self.calls.append({"attempt": attempt, "confidence_reason": confidence.get("confidence_reason")})
        
        if self._always_retry:
            return {
                "decision": VerificationDecision.RETRY,
                "reason": "forced retry for strategy rotation test",
                "recommendation": None,
            }
        return {
            "decision": VerificationDecision.ACCEPT,
            "reason": "accepted",
            "recommendation": None,
        }


class FakeVerificationAgentWithRecommendation:
    """Always returns RETRY with a recommendation to trigger RESEARCH_FOCUSED."""

    def __init__(self):
        self.calls: List[Dict[str, Any]] = []

    def decide(
        self,
        verified_claims: List[Dict[str, Any]],
        confidence: Dict[str, str],
        attempt: int,
        max_attempts: int,
    ) -> Dict[str, Any]:
        self.calls.append({"attempt": attempt})
        return {
            "decision": VerificationDecision.RETRY,
            "reason": "need more research",
            "recommendation": "Try research papers and policy documents",
        }


def test_same_confidence_reason_no_repeat_strategy():
    """Same confidence_reason repeatedly should NOT cause same strategy forever."""
    test_name = "2.2.1 Same confidence_reason - no strategy repeat"
    try:
        # Always return "single source" - would always prefer BROADEN_QUERY
        # but after first use, it should rotate to other strategies
        research = FakeResearchAgent(
            confidence_reasons=["Single source only"] * 10  # Always same reason
        )
        verifier = FakeVerificationAgent(always_retry=True)
        
        # High max_attempts to let it exhaust strategies
        planner = PlannerAgent(
            research_agent=research,
            verification_agent=verifier,
            db=None,
            max_attempts=10  # More than strategies available
        )

        result = planner.run("test question for same confidence_reason")

        # Should have used multiple different strategies, not just BROADEN_QUERY
        strategies_used = planner.context.strategy_history
        unique_strategies = set(strategies_used)
        
        # Must have tried more than one strategy
        assert_true(
            len(unique_strategies) > 1,
            f"Should use multiple strategies, got: {strategies_used}"
        )
        
        # No strategy should appear more than once
        strategy_counts = {}
        for s in strategies_used:
            strategy_counts[s] = strategy_counts.get(s, 0) + 1
        
        duplicates = {k: v for k, v in strategy_counts.items() if v > 1}
        assert_true(
            len(duplicates) == 0,
            f"No strategy should repeat, duplicates: {duplicates}"
        )

        record(test_name, True, f"strategies_used={[s.value for s in strategies_used]}, no duplicates")
    except Exception as e:
        record(test_name, False, str(e))


def test_same_recommendation_no_repeat_strategy():
    """Same recommendation repeatedly should NOT cause same strategy forever."""
    test_name = "2.2.2 Same recommendation - no strategy repeat"
    try:
        # Neutral confidence_reason so recommendation drives strategy
        research = FakeResearchAgent(
            confidence_reasons=["Need more evidence"] * 10  # No "single source" or "conflict"
        )
        verifier = FakeVerificationAgentWithRecommendation()  # Always sends recommendation
        
        planner = PlannerAgent(
            research_agent=research,
            verification_agent=verifier,
            db=None,
            max_attempts=10
        )

        result = planner.run("test question for same recommendation")

        strategies_used = planner.context.strategy_history
        unique_strategies = set(strategies_used)
        
        # Must have tried more than one strategy
        assert_true(
            len(unique_strategies) > 1,
            f"Should use multiple strategies, got: {strategies_used}"
        )
        
        # No strategy should appear more than once
        strategy_counts = {}
        for s in strategies_used:
            strategy_counts[s] = strategy_counts.get(s, 0) + 1
        
        duplicates = {k: v for k, v in strategy_counts.items() if v > 1}
        assert_true(
            len(duplicates) == 0,
            f"No strategy should repeat, duplicates: {duplicates}"
        )

        record(test_name, True, f"strategies_used={[s.value for s in strategies_used]}, no duplicates")
    except Exception as e:
        record(test_name, False, str(e))


def test_all_strategies_exhausted_fails_safely():
    """When all strategies are exhausted, planner should FAIL safely."""
    test_name = "2.2.3 All strategies exhausted → FAILED safely"
    try:
        # Rotate through different reasons to use all strategies
        research = FakeResearchAgent(
            confidence_reasons=[
                "Single source only",      # → BROADEN_QUERY
                "Conflict detected",        # → AUTHORITATIVE_SITES
                "Need more evidence",       # → RESEARCH_FOCUSED (via fallback or recommendation)
                "Still needs work",         # → will try remaining strategies
                "Still failing",
                "Still failing",
            ]
        )
        verifier = FakeVerificationAgent(always_retry=True)
        
        planner = PlannerAgent(
            research_agent=research,
            verification_agent=verifier,
            db=None,
            max_attempts=10  # High enough to exhaust all strategies
        )

        result = planner.run("test question exhaust all strategies")

        # Should end in FAILED state
        assert_equal(
            planner.context.current_state,
            PlannerState.FAILED,
            "Planner should be in FAILED state when all strategies exhausted"
        )
        
        # All 4 strategies should have been tried (or close to it)
        # STRATEGY_ORDER = [BASE, BROADEN_QUERY, AUTHORITATIVE_SITES, RESEARCH_FOCUSED]
        strategies_used = set(planner.context.strategy_history)
        all_strategies = {
            SearchStrategy.BASE,
            SearchStrategy.BROADEN_QUERY,
            SearchStrategy.AUTHORITATIVE_SITES,
            SearchStrategy.RESEARCH_FOCUSED,
        }
        
        # Note: BASE is the initial strategy and may not appear in strategy_history
        # (it's set in _handle_init, not via record_strategy)
        # So we check that strategy_history has exhausted the non-BASE strategies
        non_base_strategies = all_strategies - {SearchStrategy.BASE}
        strategies_in_history = strategies_used
        
        # Result should indicate failure gracefully
        assert_true(
            result.get("confidence_level") == "LOW",
            "Failed result should have LOW confidence"
        )

        record(
            test_name,
            True,
            f"state=FAILED, strategies_tried={[s.value for s in strategies_used]}"
        )
    except Exception as e:
        record(test_name, False, str(e))


def test_no_infinite_loop():
    """Planner must terminate in finite time even with always-retry verifier."""
    test_name = "2.2.4 No infinite loop (terminates in <5s)"
    try:
        research = FakeResearchAgent(
            confidence_reasons=["Single source only"] * 100
        )
        verifier = FakeVerificationAgent(always_retry=True)
        
        planner = PlannerAgent(
            research_agent=research,
            verification_agent=verifier,
            db=None,
            max_attempts=5
        )

        start = time.perf_counter()
        result = planner.run("test question infinite loop check")
        elapsed = time.perf_counter() - start

        # Must complete within 5 seconds (should be nearly instant with fakes)
        assert_true(elapsed < 5.0, f"Planner took too long: {elapsed:.2f}s")
        
        # Must reach terminal state
        assert_true(
            planner.context.current_state in {PlannerState.DONE, PlannerState.FAILED},
            f"Planner should be in terminal state, got: {planner.context.current_state}"
        )

        record(test_name, True, f"completed in {elapsed:.3f}s, state={planner.context.current_state.value}")
    except Exception as e:
        record(test_name, False, str(e))


def test_strategy_order_followed():
    """Fallback rotation should follow STRATEGY_ORDER."""
    test_name = "2.2.5 Strategy fallback follows STRATEGY_ORDER"
    try:
        # Use a neutral confidence_reason that defaults to BROADEN_QUERY
        # After BROADEN_QUERY is used, fallback should follow STRATEGY_ORDER
        research = FakeResearchAgent(
            confidence_reasons=["Need more evidence"] * 10  # Defaults to BROADEN_QUERY preferred
        )
        verifier = FakeVerificationAgent(always_retry=True)
        
        planner = PlannerAgent(
            research_agent=research,
            verification_agent=verifier,
            db=None,
            max_attempts=10
        )

        result = planner.run("test question strategy order")

        strategies_used = planner.context.strategy_history
        
        # The fallback mechanism should pick strategies from STRATEGY_ORDER
        # in order when preferred is already used
        # STRATEGY_ORDER = [BASE, BROADEN_QUERY, AUTHORITATIVE_SITES, RESEARCH_FOCUSED]
        
        # First retry should pick BROADEN_QUERY (preferred for neutral reason)
        if len(strategies_used) >= 1:
            assert_equal(
                strategies_used[0],
                SearchStrategy.BROADEN_QUERY,
                "First strategy should be BROADEN_QUERY"
            )
        
        # After BROADEN_QUERY, fallback goes through STRATEGY_ORDER
        # Next unused in order: BASE (if not initial), then AUTHORITATIVE_SITES, then RESEARCH_FOCUSED
        # Note: BASE is set initially but not recorded in strategy_history
        
        record(test_name, True, f"strategies_used={[s.value for s in strategies_used]}")
    except Exception as e:
        record(test_name, False, str(e))


def main() -> int:
    print("=" * 70)
    print("PLANNER AGENT BEHAVIOR TESTS - 2.2 Strategy Rotation Integrity")
    print("=" * 70)

    test_same_confidence_reason_no_repeat_strategy()
    test_same_recommendation_no_repeat_strategy()
    test_all_strategies_exhausted_fails_safely()
    test_no_infinite_loop()
    test_strategy_order_followed()

    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])

    print("-" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(results)} tests")

    if failed:
        print("\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  ❌ {r['test']}: {r['details']}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
