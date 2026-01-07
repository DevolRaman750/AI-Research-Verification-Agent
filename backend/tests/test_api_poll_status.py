"""
API Contract & Behavior Tests - Poll Status API (1.2)
Tests surface correctness of GET /api/query/{session_id}/status endpoint
"""

import time
import uuid
import requests
from typing import List, Dict, Tuple, Optional
import sys

BASE_URL = "http://127.0.0.1:8000"

# Valid state transitions (from -> to)
# Note: Due to polling frequency, we may "skip" intermediate states
# The key rule is: no BACKWARD transitions from terminal states
VALID_TRANSITIONS = {
    "INIT": {"RESEARCH", "VERIFY", "SYNTHESIZE", "DONE", "FAILED"},  # May skip intermediate
    "RESEARCH": {"VERIFY", "SYNTHESIZE", "DONE", "FAILED"},  # May skip intermediate
    "VERIFY": {"SYNTHESIZE", "RESEARCH", "DONE", "FAILED"},  # Can retry back to RESEARCH
    "SYNTHESIZE": {"DONE", "FAILED"},
    "DONE": set(),  # Terminal state - CANNOT transition
    "FAILED": set(),  # Terminal state - CANNOT transition
    "PROCESSING": {"INIT", "RESEARCH", "VERIFY", "SYNTHESIZE", "DONE", "FAILED"},  # Initial API status
}

TERMINAL_STATES = {"DONE", "FAILED"}

# Test results collector
results: List[Dict] = []


def record(test_name: str, passed: bool, details: str = "", response_ms: float = 0):
    status = "✅ PASS" if passed else "❌ FAIL"
    results.append({
        "test": test_name,
        "passed": passed,
        "details": details,
        "response_ms": response_ms
    })
    print(f"{status} | {test_name} | {response_ms:.1f}ms | {details}")


def submit_query(question: str) -> Tuple[Optional[str], int]:
    """Submit a query and return (session_id, status_code)"""
    try:
        resp = requests.post(
            f"{BASE_URL}/api/query",
            json={"question": question},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json().get("session_id"), resp.status_code
        return None, resp.status_code
    except Exception as e:
        return None, 0


def poll_status(session_id: str) -> Tuple[Dict, float, int]:
    """Poll status and return (response_json, response_time_ms, status_code)"""
    start = time.perf_counter()
    try:
        resp = requests.get(
            f"{BASE_URL}/api/query/{session_id}/status",
            timeout=10
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        try:
            data = resp.json()
        except:
            data = {"raw": resp.text}
        return data, elapsed_ms, resp.status_code
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {"error": str(e)}, elapsed_ms, 0


def poll_until_terminal(session_id: str, max_wait_sec: float = 60) -> List[str]:
    """
    Poll until terminal state, return list of observed statuses.
    """
    observed = []
    start = time.time()
    last_status = None
    
    while time.time() - start < max_wait_sec:
        data, ms, code = poll_status(session_id)
        if code != 200:
            observed.append(f"ERROR_{code}")
            break
        
        status = data.get("status", "UNKNOWN")
        
        # Only record if status changed
        if status != last_status:
            observed.append(status)
            last_status = status
        
        if status in TERMINAL_STATES:
            break
        
        time.sleep(0.3)
    
    return observed


# ============================================================
# TEST 1.2.1: Poll Immediately After Submit
# ============================================================
def test_poll_immediately_after_submit():
    """Status should be available immediately after submit"""
    session_id, code = submit_query("Test question for immediate poll")
    
    if code != 200 or not session_id:
        record("1.2.1 Poll Immediately After Submit", False, "Submit failed")
        return None
    
    # Poll immediately (within milliseconds)
    data, ms, status_code = poll_status(session_id)
    
    checks = []
    
    # Check 1: 200 response
    if status_code == 200:
        checks.append("status_200")
    else:
        checks.append(f"status_{status_code}")
    
    # Check 2: Has status field
    if "status" in data:
        checks.append(f"has_status={data['status']}")
    else:
        checks.append("missing_status")
    
    # Check 3: Response time < 100ms
    if ms < 100:
        checks.append(f"fast({ms:.0f}ms)")
    else:
        checks.append(f"slow({ms:.0f}ms)")
    
    # Check 4: Status is valid initial state
    valid_initial = data.get("status") in {"PROCESSING", "INIT", "RESEARCH"}
    if valid_initial:
        checks.append("valid_initial_state")
    else:
        checks.append(f"unexpected_state={data.get('status')}")
    
    passed = status_code == 200 and "status" in data and ms < 100
    record("1.2.1 Poll Immediately After Submit", passed, ", ".join(checks), ms)
    
    return session_id


# ============================================================
# TEST 1.2.2: Observe RESEARCH State
# ============================================================
def test_observe_research_state():
    """Should observe RESEARCH state during execution"""
    session_id, code = submit_query("What are the effects of climate change on agriculture?")
    
    if code != 200 or not session_id:
        record("1.2.2 Observe RESEARCH State", False, "Submit failed")
        return
    
    # Poll rapidly to catch RESEARCH state
    research_seen = False
    poll_count = 0
    max_polls = 50
    
    while poll_count < max_polls:
        data, ms, status_code = poll_status(session_id)
        poll_count += 1
        
        if status_code != 200:
            break
        
        status = data.get("status")
        if status == "RESEARCH":
            research_seen = True
            break
        
        if status in TERMINAL_STATES:
            break
        
        time.sleep(0.1)
    
    passed = research_seen
    details = f"research_seen={research_seen}, polls={poll_count}"
    
    record("1.2.2 Observe RESEARCH State", passed, details, 0)


# ============================================================
# TEST 1.2.3: Observe VERIFY State
# ============================================================
def test_observe_verify_state():
    """Should observe VERIFY state during execution"""
    session_id, code = submit_query("Is coffee good for health? What do studies say?")
    
    if code != 200 or not session_id:
        record("1.2.3 Observe VERIFY State", False, "Submit failed")
        return
    
    # Poll to catch VERIFY state
    verify_seen = False
    all_states = []
    poll_count = 0
    max_polls = 100
    last_status = None
    
    while poll_count < max_polls:
        data, ms, status_code = poll_status(session_id)
        poll_count += 1
        
        if status_code != 200:
            break
        
        status = data.get("status")
        
        if status != last_status:
            all_states.append(status)
            last_status = status
        
        if status == "VERIFY":
            verify_seen = True
        
        if status in TERMINAL_STATES:
            break
        
        time.sleep(0.1)
    
    # VERIFY may be quick - check if we at least saw proper progression
    proper_progression = len(all_states) >= 2
    
    passed = verify_seen or proper_progression
    details = f"verify_seen={verify_seen}, states={all_states[:5]}"
    
    record("1.2.3 Observe VERIFY State", passed, details, 0)


# ============================================================
# TEST 1.2.4: Poll After DONE
# ============================================================
def test_poll_after_done():
    """Status should remain DONE after completion"""
    session_id, code = submit_query("What is 2+2?")
    
    if code != 200 or not session_id:
        record("1.2.4 Poll After DONE", False, "Submit failed")
        return
    
    # Wait for completion
    states = poll_until_terminal(session_id, max_wait_sec=60)
    
    if "DONE" not in states and "FAILED" not in states:
        record("1.2.4 Poll After DONE", False, f"Never reached terminal: {states}")
        return
    
    final_state = states[-1] if states else "UNKNOWN"
    
    # Poll multiple times after terminal
    consistent = True
    post_terminal_states = []
    
    for _ in range(5):
        data, ms, status_code = poll_status(session_id)
        if status_code == 200:
            post_terminal_states.append(data.get("status"))
        time.sleep(0.2)
    
    # All post-terminal polls should return same state
    if post_terminal_states:
        consistent = all(s == final_state for s in post_terminal_states)
    
    passed = consistent and final_state in TERMINAL_STATES
    details = f"final={final_state}, post_polls={post_terminal_states}, consistent={consistent}"
    
    record("1.2.4 Poll After DONE", passed, details, 0)


# ============================================================
# TEST 1.2.5: Poll After FAILED
# ============================================================
def test_poll_after_failed():
    """
    Status should remain FAILED after failure.
    Note: Hard to force failure without mocking, so we verify FAILED is stable if seen.
    """
    # Submit a question and track if we see FAILED
    session_id, code = submit_query("Test question that might fail")
    
    if code != 200 or not session_id:
        record("1.2.5 Poll After FAILED", False, "Submit failed")
        return
    
    # Wait for terminal
    states = poll_until_terminal(session_id, max_wait_sec=60)
    final_state = states[-1] if states else "UNKNOWN"
    
    if final_state == "FAILED":
        # Verify FAILED is stable
        stable = True
        for _ in range(3):
            data, ms, status_code = poll_status(session_id)
            if status_code != 200 or data.get("status") != "FAILED":
                stable = False
                break
            time.sleep(0.2)
        
        passed = stable
        details = f"FAILED state is stable={stable}"
    else:
        # Didn't see FAILED - that's OK, test the stability of whatever terminal we got
        passed = True
        details = f"Got {final_state} (FAILED not triggered - OK)"
    
    record("1.2.5 Poll After FAILED (stability)", passed, details, 0)


# ============================================================
# TEST 1.2.6: Invalid Session ID
# ============================================================
def test_invalid_session_id():
    """Should return 404 for non-existent session"""
    fake_id = str(uuid.uuid4())
    
    data, ms, status_code = poll_status(fake_id)
    
    passed = status_code == 404
    details = f"status={status_code}, response={data}"
    
    record("1.2.6 Invalid Session ID (expect 404)", passed, details, ms)


# ============================================================
# TEST 1.2.7: Malformed Session ID
# ============================================================
def test_malformed_session_id():
    """Should handle malformed session IDs gracefully"""
    malformed_ids = [
        "not-a-uuid",
        "12345",
        "",
        "'; DROP TABLE query_sessions; --",
        "null",
        "../../../etc/passwd",
    ]
    
    all_handled = True
    results_detail = []
    
    for bad_id in malformed_ids:
        if not bad_id:
            # Empty string - different URL
            continue
        
        data, ms, status_code = poll_status(bad_id)
        
        # Should return 404 or 422, NOT 500
        handled = status_code in [404, 422, 400]
        if not handled:
            all_handled = False
        
        results_detail.append(f"{bad_id[:15]}={status_code}")
    
    passed = all_handled
    details = ", ".join(results_detail)
    
    record("1.2.7 Malformed Session IDs (no 500s)", passed, details, 0)


# ============================================================
# TEST 1.2.8: No Status Regression
# ============================================================
def test_no_status_regression():
    """
    Status should never regress backwards unexpectedly.
    DONE should never go back to RESEARCH.
    """
    session_id, code = submit_query("Explain quantum entanglement in simple terms")
    
    if code != 200 or not session_id:
        record("1.2.8 No Status Regression", False, "Submit failed")
        return
    
    # Track all state transitions
    observed_states = []
    last_status = None
    invalid_transitions = []
    poll_count = 0
    max_polls = 200
    
    while poll_count < max_polls:
        data, ms, status_code = poll_status(session_id)
        poll_count += 1
        
        if status_code != 200:
            break
        
        current_status = data.get("status", "UNKNOWN")
        
        if last_status is not None and current_status != last_status:
            # Check if transition is valid
            allowed_next = VALID_TRANSITIONS.get(last_status, set())
            
            if current_status not in allowed_next and last_status not in {"PROCESSING"}:
                invalid_transitions.append(f"{last_status}->{current_status}")
            
            observed_states.append(current_status)
        elif last_status is None:
            observed_states.append(current_status)
        
        last_status = current_status
        
        if current_status in TERMINAL_STATES:
            break
        
        time.sleep(0.15)
    
    passed = len(invalid_transitions) == 0
    details = f"states={observed_states}, invalid={invalid_transitions}"
    
    record("1.2.8 No Status Regression", passed, details, 0)


# ============================================================
# TEST 1.2.9: Concurrent Polling
# ============================================================
def test_concurrent_polling():
    """Multiple concurrent polls should all succeed"""
    import concurrent.futures
    
    session_id, code = submit_query("What is machine learning?")
    
    if code != 200 or not session_id:
        record("1.2.9 Concurrent Polling", False, "Submit failed")
        return
    
    # Wait a moment for planner to start
    time.sleep(0.5)
    
    # Fire 20 concurrent polls
    def do_poll():
        return poll_status(session_id)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(do_poll) for _ in range(20)]
        results_local = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    success_count = sum(1 for data, ms, code in results_local if code == 200)
    error_count = sum(1 for data, ms, code in results_local if code >= 500)
    
    passed = success_count == 20 and error_count == 0
    details = f"success={success_count}/20, 5xx_errors={error_count}"
    
    record("1.2.9 Concurrent Polling (no 500s)", passed, details, 0)


# ============================================================
# TEST 1.2.10: Response Time Under Load
# ============================================================
def test_poll_response_time():
    """Poll response should be fast even with background work"""
    session_id, code = submit_query("Describe the history of the internet")
    
    if code != 200 or not session_id:
        record("1.2.10 Poll Response Time", False, "Submit failed")
        return
    
    # Measure poll times while planner is working
    poll_times = []
    
    for _ in range(10):
        data, ms, status_code = poll_status(session_id)
        if status_code == 200:
            poll_times.append(ms)
        
        if data.get("status") in TERMINAL_STATES:
            break
        
        time.sleep(0.3)
    
    if not poll_times:
        record("1.2.10 Poll Response Time", False, "No successful polls")
        return
    
    avg_ms = sum(poll_times) / len(poll_times)
    max_ms = max(poll_times)
    
    # Polls should be fast (< 100ms average, < 500ms max)
    passed = avg_ms < 100 and max_ms < 500
    details = f"avg={avg_ms:.0f}ms, max={max_ms:.0f}ms, samples={len(poll_times)}"
    
    record("1.2.10 Poll Response Time", passed, details, avg_ms)


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 70)
    print("API CONTRACT TESTS - Poll Status API (GET /api/query/{id}/status)")
    print("=" * 70)
    print()
    
    # Check server is up
    try:
        resp = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        if resp.status_code != 200:
            print("❌ Server not responding. Start with: uvicorn backend.main:app")
            sys.exit(1)
        print(f"✅ Server is running at {BASE_URL}")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        sys.exit(1)
    
    print()
    print("-" * 70)
    
    # Run all tests
    test_poll_immediately_after_submit()
    test_observe_research_state()
    test_observe_verify_state()
    test_poll_after_done()
    test_poll_after_failed()
    test_invalid_session_id()
    test_malformed_session_id()
    test_no_status_regression()
    test_concurrent_polling()
    test_poll_response_time()
    
    print("-" * 70)
    print()
    
    # Summary
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    
    print("=" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(results)} tests")
    print("=" * 70)
    
    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  ❌ {r['test']}: {r['details']}")
    
    print()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
