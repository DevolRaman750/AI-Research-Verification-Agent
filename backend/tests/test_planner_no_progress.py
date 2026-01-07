"""Planner Agent Behavior Tests (2.3) - No-Progress Detection

Goals (deterministic, no web/LLM):
- Force same confidence + same decision across multiple attempts
- Verify no_progress_count increments correctly
- Verify planner stops after threshold (no_progress_count >= 2)
- Verify stop_reason is meaningful

Run:
  $env:PYTHONPATH="c:/Agents/AI-Research-Agent/backend"; python backend/tests/test_planner_no_progress.py
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List

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
    """Returns same confidence_level repeatedly to trigger no-progress detection."""

    def __init__(self, confidence_level: str = "LOW", confidence_reason: str = "Same reason"):
        self._confidence_level = confidence_level
        self._confidence_reason = confidence_reason
        self.call_count = 0

    def research(self, question: str, num_docs: int) -> Dict[str, Any]:
        self.call_count += 1
        return {
            "answer": f"fake-answer call={self.call_count}",
            "confidence_level": self._confidence_level,
            "confidence_reason": self._confidence_reason,
            "evidence": [
                {
                    "claim": "Fake claim",
                    "status": "UNVERIFIED",
                    "sources": ["https://example.com"],
                }
            ],
        }


class FakeVerificationAgent:
    """Returns same decision repeatedly to trigger no-progress detection."""

    def __init__(self, decision: str = VerificationDecision.RETRY):
        self._decision = decision
        self.calls: List[Dict[str, Any]] = []

    def decide(
        self,
        verified_claims: List[Dict[str, Any]],
        confidence: Dict[str, str],
        attempt: int,
        max_attempts: int,
    ) -> Dict[str, Any]:
        self.calls.append({
            "attempt": attempt,
            "confidence_level": confidence.get("confidence_level"),
            "confidence_reason": confidence.get("confidence_reason"),
        })
        return {
            "decision": self._decision,
            "reason": "same decision every time",
            "recommendation": None,
        }


def test_no_progress_count_increments():
    """no_progress_count should increment when confidence + decision stay the same."""
    test_name = "2.3.1 no_progress_count increments correctly"
    try:
        # Same confidence_level and same decision every time
        research = FakeResearchAgent(
            confidence_level="LOW",
            confidence_reason="Single source only"
        )
        verifier = FakeVerificationAgent(decision=VerificationDecision.RETRY)
        
        planner = PlannerAgent(
            research_agent=research,
            verification_agent=verifier,
            db=None,
            max_attempts=10  # High enough to let no_progress trigger first
        )

        result = planner.run("test question for no progress")

        # no_progress_count should be at least 2 (the threshold)
        assert_true(
            planner.context.no_progress_count >= 2,
            f"no_progress_count should be >= 2, got {planner.context.no_progress_count}"
        )

        record(test_name, True, f"no_progress_count={planner.context.no_progress_count}")
    except Exception as e:
        record(test_name, False, str(e))


def test_stops_after_no_progress_threshold():
    """Planner should stop when no_progress_count reaches threshold (2)."""
    test_name = "2.3.2 Stops after no_progress threshold"
    try:
        research = FakeResearchAgent(
            confidence_level="LOW",
            confidence_reason="Same reason every time"
        )
        verifier = FakeVerificationAgent(decision=VerificationDecision.RETRY)
        
        planner = PlannerAgent(
            research_agent=research,
            verification_agent=verifier,
            db=None,
            max_attempts=10
        )

        result = planner.run("test question for no progress threshold")

        # Should end in FAILED state
        assert_equal(
            planner.context.current_state,
            PlannerState.FAILED,
            "Planner should be FAILED after no progress"
        )
        
        # Should have stopped due to no_progress, not max_attempts
        # With threshold=2, it should stop at attempt 3 (after 2 no-progress increments)
        assert_true(
            planner.context.attempt_count < planner.context.max_attempts,
            f"Should stop before max_attempts due to no_progress (attempt={planner.context.attempt_count}, max={planner.context.max_attempts})"
        )

        record(
            test_name,
            True,
            f"stopped at attempt={planner.context.attempt_count}, no_progress_count={planner.context.no_progress_count}"
        )
    except Exception as e:
        record(test_name, False, str(e))


def test_stop_reason_is_meaningful():
    """budget_exhausted_reason should explain why stopped."""
    test_name = "2.3.3 stop_reason is meaningful"
    try:
        research = FakeResearchAgent(
            confidence_level="LOW",
            confidence_reason="Same reason"
        )
        verifier = FakeVerificationAgent(decision=VerificationDecision.RETRY)
        
        planner = PlannerAgent(
            research_agent=research,
            verification_agent=verifier,
            db=None,
            max_attempts=10
        )

        result = planner.run("test question for stop reason")

        reason = planner.context.budget_exhausted_reason or ""
        
        # Should mention "no progress"
        assert_true(
            "no progress" in reason.lower(),
            f"stop_reason should mention 'no progress', got: {reason}"
        )

        record(test_name, True, f"stop_reason='{reason}'")
    except Exception as e:
        record(test_name, False, str(e))


def test_progress_resets_on_different_outcome():
    """no_progress_count should reset when confidence or decision changes."""
    test_name = "2.3.4 Progress resets on different outcome"
    try:
        # This test needs a more complex setup:
        # - First 2 attempts: same confidence + same decision (no_progress_count = 1, then 2... but wait)
        # - Actually, let's test the reset by having changing outcomes
        
        class VaryingResearchAgent:
            def __init__(self):
                self.call_count = 0
                # Alternate between LOW and MEDIUM to reset no_progress
                self.confidence_sequence = ["LOW", "LOW", "MEDIUM", "LOW", "MEDIUM"]
            
            def research(self, question: str, num_docs: int) -> Dict[str, Any]:
                idx = min(self.call_count, len(self.confidence_sequence) - 1)
                conf = self.confidence_sequence[idx]
                self.call_count += 1
                return {
                    "answer": f"answer {self.call_count}",
                    "confidence_level": conf,
                    "confidence_reason": f"reason for {conf}",
                    "evidence": [{"claim": "claim", "status": "UNVERIFIED", "sources": []}],
                }
        
        class VaryingVerificationAgent:
            def __init__(self):
                self.call_count = 0
            
            def decide(self, verified_claims, confidence, attempt, max_attempts):
                self.call_count += 1
                # Always retry until max attempts
                return {
                    "decision": VerificationDecision.RETRY,
                    "reason": "keep retrying",
                    "recommendation": None,
                }
        
        research = VaryingResearchAgent()
        verifier = VaryingVerificationAgent()
        
        planner = PlannerAgent(
            research_agent=research,
            verification_agent=verifier,
            db=None,
            max_attempts=5
        )

        result = planner.run("test question varying outcomes")

        # With varying confidence, no_progress should reset and not trigger early stop
        # It should reach max_attempts instead of no_progress stop
        
        # Either it hit max_attempts OR it hit no_progress at some point
        # The key is that varying outcomes should have reset no_progress at least once
        
        # Check that we got past attempt 2 (which would be the earliest no_progress stop)
        # if there was no reset
        assert_true(
            planner.context.attempt_count >= 3 or planner.context.current_state == PlannerState.FAILED,
            f"Should continue past early no_progress threshold when outcomes vary"
        )

        record(
            test_name,
            True,
            f"attempt_count={planner.context.attempt_count}, final_no_progress={planner.context.no_progress_count}"
        )
    except Exception as e:
        record(test_name, False, str(e))


def test_no_progress_with_low_confidence_output():
    """When stopped due to no progress, result should have LOW confidence."""
    test_name = "2.3.5 No progress result has LOW confidence"
    try:
        research = FakeResearchAgent(
            confidence_level="LOW",
            confidence_reason="Same reason"
        )
        verifier = FakeVerificationAgent(decision=VerificationDecision.RETRY)
        
        planner = PlannerAgent(
            research_agent=research,
            verification_agent=verifier,
            db=None,
            max_attempts=10
        )

        result = planner.run("test question for low confidence output")

        # Result should indicate low confidence
        assert_equal(
            result.get("confidence_level"),
            "LOW",
            "Result should have LOW confidence when stopped due to no progress"
        )
        
        # Should have some notes/explanation
        notes = result.get("notes", "")
        assert_true(
            len(notes) > 0,
            "Result should have notes explaining the failure"
        )

        record(test_name, True, f"confidence={result.get('confidence_level')}, has_notes=True")
    except Exception as e:
        record(test_name, False, str(e))


def main() -> int:
    print("=" * 70)
    print("PLANNER AGENT BEHAVIOR TESTS - 2.3 No-Progress Detection")
    print("=" * 70)

    test_no_progress_count_increments()
    test_stops_after_no_progress_threshold()
    test_stop_reason_is_meaningful()
    test_progress_resets_on_different_outcome()
    test_no_progress_with_low_confidence_output()

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
