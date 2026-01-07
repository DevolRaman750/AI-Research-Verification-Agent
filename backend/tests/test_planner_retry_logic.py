"""Planner Agent Behavior Tests (2.1) - Retry Logic

Goals (deterministic, no web/LLM):
- Force: fail first attempt, succeed on second
- Force: fail first + second, succeed on third (needed to observe BASE -> BROADEN -> AUTHORITATIVE)
- Force: never converge (retries stop at max_attempts)

Verifies:
- attempt_count increments correctly
- strategy rotates (BASE -> BROADEN_QUERY -> AUTHORITATIVE_SITES)
- num_docs escalates (5 -> 10 -> 20)
- retries stop at max_attempts

Run:
  $env:PYTHONPATH="c:/Agents/AI-Research-Agent/backend"; python backend/tests/test_planner_retry_logic.py
"""

from __future__ import annotations

import sys
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
    """Returns a deterministic research result; can vary confidence_reason by call."""

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
    """Returns a deterministic sequence of decisions across attempts."""

    def __init__(self, decisions_by_attempt: Dict[int, str]):
        # attempt is 1-based in this codebase
        self._decisions_by_attempt = decisions_by_attempt
        self.calls: List[Dict[str, Any]] = []

    def decide(
        self,
        verified_claims: List[Dict[str, Any]],
        confidence: Dict[str, str],
        attempt: int,
        max_attempts: int,
    ) -> Dict[str, Any]:
        decision = self._decisions_by_attempt.get(attempt, VerificationDecision.RETRY)
        self.calls.append(
            {
                "attempt": attempt,
                "decision": decision,
                "confidence_reason": confidence.get("confidence_reason"),
            }
        )
        return {
            "decision": decision,
            "reason": f"fake-decision attempt={attempt}",
            # IMPORTANT: keep recommendation None so PlannerAgent strategy selection is
            # driven by confidence_reason (single source -> broaden, conflict -> authority)
            "recommendation": None,
        }


def _run_planner(planner: PlannerAgent, question: str) -> Dict[str, Any]:
    # Sanity: PlannerAgent.run is an internal loop until DONE/FAILED.
    result = planner.run(question)
    assert_true(isinstance(result, dict), "Planner result must be a dict")
    return result


def test_fail_first_succeed_second():
    test_name = "2.1.1 Fail first, succeed second"
    try:
        research = FakeResearchAgent(
            confidence_reasons=[
                "Single source only; low coverage",  # triggers BROADEN_QUERY on retry
                "Enough sources now",
            ]
        )
        verifier = FakeVerificationAgent(
            decisions_by_attempt={
                1: VerificationDecision.RETRY,
                2: VerificationDecision.ACCEPT,
            }
        )
        planner = PlannerAgent(research_agent=research, verification_agent=verifier, db=None, max_attempts=3)

        _run_planner(planner, "question: fail then succeed")

        # attempt_count starts at 1 in INIT, increments on RETRY
        assert_equal(planner.context.attempt_count, 2, "attempt_count should be 2 after one retry")

        # num_docs: starts at 5, doubles on retry
        assert_equal(planner.context.num_docs, 10, "num_docs should escalate 5->10 after one retry")

        # strategy should move from BASE to BROADEN_QUERY (due to 'single source')
        assert_equal(planner.context.current_strategy, SearchStrategy.BROADEN_QUERY, "strategy should be BROADEN_QUERY after retry")

        # should end DONE
        assert_equal(planner.context.current_state, PlannerState.DONE, "planner should end in DONE")

        record(test_name, True, "attempt_count=2, num_docs=10, strategy=BROADEN_QUERY")
    except Exception as e:
        record(test_name, False, str(e))


def test_succeed_on_third_attempt_strategy_rotation():
    """Needed to observe BASE -> BROADEN_QUERY -> AUTHORITATIVE_SITES (requires 2 retries)."""

    test_name = "2.1.2 Succeed third (observe BASE->BROADEN->AUTH)"
    try:
        research = FakeResearchAgent(
            confidence_reasons=[
                "Single source only; low coverage",  # retry 1 -> BROADEN_QUERY
                "Conflict detected between sources",  # retry 2 -> AUTHORITATIVE_SITES
                "Enough sources now",
            ]
        )
        verifier = FakeVerificationAgent(
            decisions_by_attempt={
                1: VerificationDecision.RETRY,
                2: VerificationDecision.RETRY,
                3: VerificationDecision.ACCEPT,
            }
        )
        planner = PlannerAgent(research_agent=research, verification_agent=verifier, db=None, max_attempts=3)

        _run_planner(planner, "question: retry twice then succeed")

        assert_equal(planner.context.attempt_count, 3, "attempt_count should be 3 after two retries")
        assert_equal(planner.context.num_docs, 20, "num_docs should escalate 5->10->20 after two retries")

        # strategy_history contains the strategies chosen on retries (BASE is initial but not recorded)
        assert_true(len(planner.context.strategy_history) >= 2, "strategy_history should include at least 2 entries")
        assert_equal(planner.context.strategy_history[0], SearchStrategy.BROADEN_QUERY, "first rotation should be BROADEN_QUERY")
        assert_equal(planner.context.strategy_history[1], SearchStrategy.AUTHORITATIVE_SITES, "second rotation should be AUTHORITATIVE_SITES")

        assert_equal(planner.context.current_strategy, SearchStrategy.AUTHORITATIVE_SITES, "current strategy should be AUTHORITATIVE_SITES at end")
        assert_equal(planner.context.current_state, PlannerState.DONE, "planner should end in DONE")

        record(test_name, True, "attempt_count=3, num_docs=20, strategy sequence ok")
    except Exception as e:
        record(test_name, False, str(e))


def test_never_converge_stops_at_max_attempts():
    test_name = "2.1.3 Never converge (stop at max_attempts)"
    try:
        research = FakeResearchAgent(
            confidence_reasons=[
                "Single source only; low coverage",  # broaden
                "Conflict detected between sources",  # authority
                "Still conflicting and unclear",  # will rotate further if needed
                "Still conflicting and unclear",
            ]
        )
        verifier = FakeVerificationAgent(
            decisions_by_attempt={
                1: VerificationDecision.RETRY,
                2: VerificationDecision.RETRY,
                3: VerificationDecision.RETRY,
                4: VerificationDecision.RETRY,
                5: VerificationDecision.RETRY,
            }
        )
        planner = PlannerAgent(research_agent=research, verification_agent=verifier, db=None, max_attempts=3)

        result = _run_planner(planner, "question: never converge")

        # With max_attempts=3, planner should stop retrying at attempt_count == 3
        # (attempt_count reflects the attempt currently being executed).
        assert_equal(planner.context.attempt_count, 3, "attempt_count should end at 3 when max_attempts=3")
        assert_equal(planner.context.current_state, PlannerState.FAILED, "planner should end in FAILED")

        # num_docs escalates and caps at 20
        assert_equal(planner.context.num_docs, 20, "num_docs should cap at 20")

        assert_true(
            (planner.context.budget_exhausted_reason or "").lower().find("maximum") >= 0,
            "budget_exhausted_reason should mention maximum retry attempts",
        )

        assert_true(
            result.get("confidence_level") == "LOW",
            "failed result should be LOW confidence",
        )

        record(test_name, True, "stopped at max_attempts (attempt_count=3), num_docs capped")
    except Exception as e:
        record(test_name, False, str(e))


def main() -> int:
    print("=" * 70)
    print("PLANNER AGENT BEHAVIOR TESTS - 2.1 Retry Logic")
    print("=" * 70)

    test_fail_first_succeed_second()
    test_succeed_on_third_attempt_strategy_rotation()
    test_never_converge_stops_at_max_attempts()

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
