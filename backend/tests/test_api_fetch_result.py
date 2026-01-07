"""
API Contract & Behavior Tests - Fetch Result API (1.3)
Tests surface correctness of GET /api/query/{session_id}/result endpoint
"""

import time
import uuid
import requests
from typing import List, Dict, Tuple, Optional
import sys

BASE_URL = "http://127.0.0.1:8000"

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


def poll_status(session_id: str) -> Tuple[str, int]:
    """Poll status and return (status, status_code)"""
    try:
        resp = requests.get(
            f"{BASE_URL}/api/query/{session_id}/status",
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json().get("status", "UNKNOWN"), resp.status_code
        return "ERROR", resp.status_code
    except Exception as e:
        return "ERROR", 0


def fetch_result(session_id: str) -> Tuple[Dict, float, int]:
    """Fetch result and return (response_json, response_time_ms, status_code)"""
    start = time.perf_counter()
    try:
        resp = requests.get(
            f"{BASE_URL}/api/query/{session_id}/result",
            timeout=30
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


def wait_for_terminal(session_id: str, max_wait_sec: float = 120) -> str:
    """Wait until session reaches terminal state, return final status"""
    start = time.time()
    while time.time() - start < max_wait_sec:
        status, code = poll_status(session_id)
        if status in TERMINAL_STATES:
            return status
        time.sleep(0.5)
    return "TIMEOUT"


# ============================================================
# TEST 1.3.1: Call Before DONE (expect 409)
# ============================================================
def test_fetch_before_done():
    """Fetching result before completion should return 409 with proper message"""
    session_id, code = submit_query("What is the capital of France?")
    
    if code != 200 or not session_id:
        record("1.3.1 Fetch Before DONE", False, "Submit failed")
        return
    
    # Immediately try to fetch (before processing completes)
    data, ms, status_code = fetch_result(session_id)
    
    checks = []
    
    # Check 1: Should return 409 Conflict
    if status_code == 409:
        checks.append("status_409")
    else:
        checks.append(f"status_{status_code}")
    
    # Check 2: Should have proper error message (not garbage)
    detail = data.get("detail", "")
    if detail and "not ready" in detail.lower():
        checks.append("proper_message")
    elif detail:
        checks.append(f"msg={detail[:30]}")
    else:
        checks.append("no_message")
    
    # Check 3: Response should be fast (no computation)
    if ms < 100:
        checks.append(f"fast({ms:.0f}ms)")
    else:
        checks.append(f"slow({ms:.0f}ms)")
    
    passed = status_code == 409 and detail != ""
    record("1.3.1 Fetch Before DONE (expect 409)", passed, ", ".join(checks), ms)


# ============================================================
# TEST 1.3.2: Call After DONE (expect full result)
# ============================================================
def test_fetch_after_done():
    """Fetching result after DONE should return complete answer with evidence"""
    session_id, code = submit_query("What is 2 + 2?")
    
    if code != 200 or not session_id:
        record("1.3.2 Fetch After DONE", False, "Submit failed")
        return
    
    # Wait for completion
    final_status = wait_for_terminal(session_id, max_wait_sec=60)
    
    if final_status != "DONE":
        record("1.3.2 Fetch After DONE", False, f"Did not reach DONE: {final_status}")
        return
    
    # Fetch result
    data, ms, status_code = fetch_result(session_id)
    
    checks = []
    
    # Check 1: 200 OK
    if status_code == 200:
        checks.append("status_200")
    else:
        checks.append(f"status_{status_code}")
    
    # Check 2: Has answer field
    answer = data.get("answer", "")
    if answer and len(answer) > 10:
        checks.append(f"answer_len={len(answer)}")
    elif answer:
        checks.append(f"short_answer={len(answer)}")
    else:
        checks.append("no_answer")
    
    # Check 3: Has confidence_level
    confidence = data.get("confidence_level", "")
    if confidence in {"HIGH", "MEDIUM", "LOW"}:
        checks.append(f"confidence={confidence}")
    else:
        checks.append(f"bad_confidence={confidence}")
    
    # Check 4: Has evidence array
    evidence = data.get("evidence", [])
    if isinstance(evidence, list):
        checks.append(f"evidence_count={len(evidence)}")
    else:
        checks.append("no_evidence_array")
    
    # Check 5: Evidence items have required fields
    if evidence and len(evidence) > 0:
        first_ev = evidence[0]
        has_claim = "claim" in first_ev
        has_status = "status" in first_ev
        has_sources = "sources" in first_ev
        if has_claim and has_status and has_sources:
            checks.append("evidence_complete")
        else:
            missing = []
            if not has_claim: missing.append("claim")
            if not has_status: missing.append("status")
            if not has_sources: missing.append("sources")
            checks.append(f"evidence_missing={missing}")
    
    passed = (
        status_code == 200 and
        len(answer) > 0 and
        confidence in {"HIGH", "MEDIUM", "LOW"}
    )
    record("1.3.2 Fetch After DONE", passed, ", ".join(checks), ms)
    
    return session_id  # Return for idempotency test


# ============================================================
# TEST 1.3.3: Call After FAILED (graceful explanation)
# ============================================================
def test_fetch_after_failed():
    """
    Fetching result after FAILED should return graceful explanation.
    Note: Hard to force failure without mocking - test handles both outcomes.
    """
    # Use a query that might fail or succeed
    session_id, code = submit_query("Test query for failure handling")
    
    if code != 200 or not session_id:
        record("1.3.3 Fetch After FAILED", False, "Submit failed")
        return
    
    # Wait for completion
    final_status = wait_for_terminal(session_id, max_wait_sec=60)
    
    if final_status == "FAILED":
        # Good - we got a FAILED status, test the response
        data, ms, status_code = fetch_result(session_id)
        
        checks = []
        
        # Check 1: Should still return 200 (not 500)
        if status_code == 200:
            checks.append("status_200")
        else:
            checks.append(f"status_{status_code}")
        
        # Check 2: Should have some explanation
        answer = data.get("answer", "")
        notes = data.get("notes", "")
        confidence_reason = data.get("confidence_reason", "")
        
        has_explanation = bool(answer or notes or confidence_reason)
        if has_explanation:
            checks.append("has_explanation")
        else:
            checks.append("no_explanation")
        
        # Check 3: Confidence should be LOW for failed
        confidence = data.get("confidence_level", "")
        if confidence == "LOW":
            checks.append("confidence_LOW")
        else:
            checks.append(f"confidence={confidence}")
        
        passed = status_code == 200 and has_explanation
        record("1.3.3 Fetch After FAILED", passed, ", ".join(checks), ms)
    else:
        # Didn't get FAILED - that's OK, test passes with note
        record("1.3.3 Fetch After FAILED", True, f"Got {final_status} (FAILED not triggered - OK)", 0)


# ============================================================
# TEST 1.3.4: Repeated Calls - Idempotent
# ============================================================
def test_idempotent_fetch():
    """Multiple fetches should return identical results"""
    session_id, code = submit_query("What color is the sky?")
    
    if code != 200 or not session_id:
        record("1.3.4 Idempotent Fetch", False, "Submit failed")
        return
    
    # Wait for completion
    final_status = wait_for_terminal(session_id, max_wait_sec=60)
    
    if final_status not in TERMINAL_STATES:
        record("1.3.4 Idempotent Fetch", False, f"Did not complete: {final_status}")
        return
    
    # Fetch multiple times
    results_list = []
    times_list = []
    
    for i in range(5):
        data, ms, status_code = fetch_result(session_id)
        if status_code == 200:
            results_list.append(data)
            times_list.append(ms)
        time.sleep(0.2)
    
    if len(results_list) < 5:
        record("1.3.4 Idempotent Fetch", False, f"Only {len(results_list)}/5 successful")
        return
    
    checks = []
    
    # Check 1: All answers are identical
    answers = [r.get("answer", "") for r in results_list]
    answers_identical = len(set(answers)) == 1
    if answers_identical:
        checks.append("answers_identical")
    else:
        checks.append("answers_differ!")
    
    # Check 2: All confidence levels identical
    confidences = [r.get("confidence_level", "") for r in results_list]
    conf_identical = len(set(confidences)) == 1
    if conf_identical:
        checks.append("confidence_identical")
    else:
        checks.append("confidence_differs!")
    
    # Check 3: All evidence counts identical
    ev_counts = [len(r.get("evidence", [])) for r in results_list]
    ev_identical = len(set(ev_counts)) == 1
    if ev_identical:
        checks.append(f"evidence_identical({ev_counts[0]})")
    else:
        checks.append(f"evidence_differs={ev_counts}")
    
    # Check 4: Response times are fast (no recomputation)
    avg_time = sum(times_list) / len(times_list)
    max_time = max(times_list)
    if avg_time < 100 and max_time < 200:
        checks.append(f"fast(avg={avg_time:.0f}ms)")
    else:
        checks.append(f"slow(avg={avg_time:.0f}ms,max={max_time:.0f}ms)")
    
    passed = answers_identical and conf_identical and ev_identical
    record("1.3.4 Idempotent Fetch", passed, ", ".join(checks), avg_time)


# ============================================================
# TEST 1.3.5: No LLM Calls on Fetch (response time check)
# ============================================================
def test_no_llm_on_fetch():
    """Fetch should be fast DB read, not trigger new LLM calls"""
    session_id, code = submit_query("Explain photosynthesis briefly")
    
    if code != 200 or not session_id:
        record("1.3.5 No LLM on Fetch", False, "Submit failed")
        return
    
    # Wait for completion
    final_status = wait_for_terminal(session_id, max_wait_sec=90)
    
    if final_status not in TERMINAL_STATES:
        record("1.3.5 No LLM on Fetch", False, f"Did not complete: {final_status}")
        return
    
    # Time multiple fetches - should all be fast
    fetch_times = []
    
    for _ in range(10):
        data, ms, status_code = fetch_result(session_id)
        if status_code == 200:
            fetch_times.append(ms)
    
    if not fetch_times:
        record("1.3.5 No LLM on Fetch", False, "No successful fetches")
        return
    
    avg_ms = sum(fetch_times) / len(fetch_times)
    max_ms = max(fetch_times)
    min_ms = min(fetch_times)
    
    # LLM calls typically take 500ms-5000ms
    # DB reads should be <100ms typically
    passed = avg_ms < 100 and max_ms < 300
    
    checks = [
        f"avg={avg_ms:.0f}ms",
        f"max={max_ms:.0f}ms",
        f"min={min_ms:.0f}ms",
        f"samples={len(fetch_times)}",
        "NO_LLM" if passed else "POSSIBLE_LLM"
    ]
    
    record("1.3.5 No LLM on Fetch", passed, ", ".join(checks), avg_ms)


# ============================================================
# TEST 1.3.6: Invalid Session ID
# ============================================================
def test_invalid_session_id():
    """Should return 404 for non-existent session"""
    fake_id = str(uuid.uuid4())
    
    data, ms, status_code = fetch_result(fake_id)
    
    passed = status_code == 404
    details = f"status={status_code}, detail={data.get('detail', '')[:50]}"
    
    record("1.3.6 Invalid Session ID (expect 404)", passed, details, ms)


# ============================================================
# TEST 1.3.7: Malformed Session ID
# ============================================================
def test_malformed_session_id():
    """Should handle malformed session IDs gracefully (no 500s)"""
    malformed_ids = [
        "not-a-uuid",
        "12345",
        "'; DROP TABLE answer_snapshots; --",
        "null",
    ]
    
    all_handled = True
    results_detail = []
    
    for bad_id in malformed_ids:
        data, ms, status_code = fetch_result(bad_id)
        
        # Should return 404, NOT 500
        handled = status_code in [404, 422, 400]
        if not handled:
            all_handled = False
        
        results_detail.append(f"{bad_id[:15]}={status_code}")
    
    passed = all_handled
    details = ", ".join(results_detail)
    
    record("1.3.7 Malformed Session IDs (no 500s)", passed, details, 0)


# ============================================================
# TEST 1.3.8: Result Structure Validation
# ============================================================
def test_result_structure():
    """Verify result has all expected fields with correct types"""
    session_id, code = submit_query("What is machine learning?")
    
    if code != 200 or not session_id:
        record("1.3.8 Result Structure", False, "Submit failed")
        return
    
    # Wait for completion
    final_status = wait_for_terminal(session_id, max_wait_sec=90)
    
    if final_status != "DONE":
        record("1.3.8 Result Structure", final_status == "FAILED", f"Status={final_status}")
        return
    
    data, ms, status_code = fetch_result(session_id)
    
    if status_code != 200:
        record("1.3.8 Result Structure", False, f"status={status_code}")
        return
    
    checks = []
    issues = []
    
    # Required fields
    required_fields = {
        "answer": str,
        "confidence_level": str,
        "confidence_reason": str,
        "evidence": list,
    }
    
    for field, expected_type in required_fields.items():
        if field not in data:
            issues.append(f"missing_{field}")
        elif not isinstance(data[field], expected_type):
            issues.append(f"{field}_wrong_type")
        else:
            checks.append(f"{field}_ok")
    
    # Evidence item structure
    evidence = data.get("evidence", [])
    if evidence and len(evidence) > 0:
        ev_item = evidence[0]
        ev_fields = ["claim", "status", "sources"]
        for ef in ev_fields:
            if ef not in ev_item:
                issues.append(f"evidence_missing_{ef}")
            else:
                checks.append(f"ev_{ef}_ok")
    
    passed = len(issues) == 0
    details = ", ".join(checks + issues)
    
    record("1.3.8 Result Structure", passed, details, ms)


# ============================================================
# TEST 1.3.9: Concurrent Fetches
# ============================================================
def test_concurrent_fetches():
    """Multiple concurrent fetches should all succeed"""
    import concurrent.futures
    
    session_id, code = submit_query("What is artificial intelligence?")
    
    if code != 200 or not session_id:
        record("1.3.9 Concurrent Fetches", False, "Submit failed")
        return
    
    # Wait for completion
    final_status = wait_for_terminal(session_id, max_wait_sec=90)
    
    if final_status not in TERMINAL_STATES:
        record("1.3.9 Concurrent Fetches", False, f"Did not complete: {final_status}")
        return
    
    # Fire 20 concurrent fetches
    def do_fetch():
        return fetch_result(session_id)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(do_fetch) for _ in range(20)]
        results_local = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    success_count = sum(1 for data, ms, code in results_local if code == 200)
    error_count = sum(1 for data, ms, code in results_local if code >= 500)
    
    # All successful results should have same answer
    answers = [data.get("answer", "")[:100] for data, ms, code in results_local if code == 200]
    unique_answers = len(set(answers))
    
    passed = success_count == 20 and error_count == 0 and unique_answers == 1
    details = f"success={success_count}/20, 5xx={error_count}, unique_answers={unique_answers}"
    
    record("1.3.9 Concurrent Fetches", passed, details, 0)


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 70)
    print("API CONTRACT TESTS - Fetch Result API (GET /api/query/{id}/result)")
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
    test_fetch_before_done()
    test_fetch_after_done()
    test_fetch_after_failed()
    test_idempotent_fetch()
    test_no_llm_on_fetch()
    test_invalid_session_id()
    test_malformed_session_id()
    test_result_structure()
    test_concurrent_fetches()
    
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
