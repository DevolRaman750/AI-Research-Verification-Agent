"""\
======================================================================
FAILURE & CHAOS TESTS - 6.2 Database Failure
======================================================================

Simulate:
- DB temporarily unavailable (OperationalError)

Verify:
- API returns controlled error (503)
- No partial writes (no sessions/traces/logs created)
- No corrupted sessions

Runs as a plain script (no pytest dependency).
======================================================================
"""

import sys
# Ensure both `backend.*` and `storage.*` imports work
sys.path.insert(0, "c:/Agents/AI-Research-Agent")
sys.path.insert(0, "c:/Agents/AI-Research-Agent/backend")

from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from storage.base import Base
from storage.models.query_session import QuerySession
from storage.models.planner_trace import PlannerTrace
from storage.models.search_log import SearchLog
from storage.models.answer_snapshot import AnswerSnapshot
from storage.models.evidence import Evidence

from backend.api.routes import router as api_router


def print_header():
    print("\n" + "=" * 70)
    print("FAILURE & CHAOS TESTS - 6.2 Database Failure")
    print("=" * 70)


def print_result(test_id: str, name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {test_id} {name} | {detail}")


def print_summary(passed: int, failed: int, total: int):
    print("-" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {total} tests")


def make_sqlite_db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def make_app_with_router() -> FastAPI:
    app = FastAPI()
    app.include_router(api_router)
    return app


def test_6_2_A1_submit_query_db_unavailable_returns_503():
    """DB commit fails during session creation -> API returns 503."""

    db = make_sqlite_db_session()
    app = make_app_with_router()

    rollback_called = {"value": False}

    # Patch commit to simulate DB outage
    original_commit = db.commit

    def failing_commit():
        raise OperationalError("SELECT 1", {}, Exception("DB down"))

    def tracking_rollback():
        rollback_called["value"] = True
        return original_commit.__self__.rollback() if hasattr(original_commit, "__self__") else db.rollback()

    db.commit = failing_commit  # type: ignore

    original_rollback = db.rollback
    db.rollback = lambda: (rollback_called.__setitem__("value", True), original_rollback())[1]  # type: ignore

    # Override dependency in router module
    from backend.api import routes as routes_module

    def override_get_db() -> Generator:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[routes_module.get_db] = override_get_db

    client = TestClient(app)

    resp = client.post("/api/query", json={"question": "test"})

    passed = resp.status_code == 503
    detail = f"status_code={resp.status_code}, body={resp.json()}"

    db.close()
    return passed, detail


def test_6_2_A2_db_failure_no_partial_writes():
    """On DB outage during submit, there should be no rows written."""

    db = make_sqlite_db_session()
    app = make_app_with_router()

    # Simulate outage on commit
    from sqlalchemy.exc import OperationalError

    def failing_commit():
        raise OperationalError("INSERT", {}, Exception("DB down"))

    db.commit = failing_commit  # type: ignore

    from backend.api import routes as routes_module

    def override_get_db() -> Generator:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[routes_module.get_db] = override_get_db

    client = TestClient(app)

    client.post("/api/query", json={"question": "test"})

    sessions = db.query(QuerySession).count()
    traces = db.query(PlannerTrace).count()
    logs = db.query(SearchLog).count()
    answers = db.query(AnswerSnapshot).count()
    evidence = db.query(Evidence).count()

    passed = (sessions, traces, logs, answers, evidence) == (0, 0, 0, 0, 0)
    detail = f"sessions={sessions}, traces={traces}, logs={logs}, answers={answers}, evidence={evidence}"

    db.close()
    return passed, detail


def test_6_2_A3_status_endpoint_db_unavailable_returns_503():
    """DB failure during status check -> API returns 503."""

    db = make_sqlite_db_session()
    app = make_app_with_router()

    # Simulate outage on query
    original_query = db.query

    def failing_query(*args, **kwargs):
        raise OperationalError("SELECT", {}, Exception("DB down"))

    db.query = failing_query  # type: ignore

    from backend.api import routes as routes_module

    def override_get_db() -> Generator:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[routes_module.get_db] = override_get_db

    client = TestClient(app)

    # Use a valid UUID format
    resp = client.get("/api/query/12345678-1234-5678-1234-567812345678/status")

    passed = resp.status_code == 503
    detail = f"status_code={resp.status_code}, body={resp.json()}"

    db.close()
    return passed, detail


def test_6_2_A4_result_endpoint_db_unavailable_returns_503():
    """DB failure during result fetch -> API returns 503."""

    db = make_sqlite_db_session()
    app = make_app_with_router()

    # Simulate outage on query
    def failing_query(*args, **kwargs):
        raise OperationalError("SELECT", {}, Exception("DB down"))

    db.query = failing_query  # type: ignore

    from backend.api import routes as routes_module

    def override_get_db() -> Generator:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[routes_module.get_db] = override_get_db

    client = TestClient(app)

    resp = client.get("/api/query/12345678-1234-5678-1234-567812345678/result")

    passed = resp.status_code == 503
    detail = f"status_code={resp.status_code}, body={resp.json()}"

    db.close()
    return passed, detail


def test_6_2_B1_no_corrupted_sessions_on_failure():
    """
    If DB fails mid-operation, existing sessions should remain uncorrupted.
    Simulates: create session OK, then update fails -> original data preserved.
    """

    db = make_sqlite_db_session()

    # Create a valid session first
    from storage.repositories.query_session_repo import QuerySessionRepository
    session = QuerySessionRepository.create(db=db, question="Original question")
    original_id = session.id
    original_status = session.status  # Should be "INIT"

    # Now simulate failure on next commit (the update)
    original_commit = db.commit

    def always_fail_commit():
        raise OperationalError("UPDATE", {}, Exception("DB down"))

    db.commit = always_fail_commit  # type: ignore

    # Try to update (will fail)
    try:
        db.query(QuerySession).filter(QuerySession.id == original_id).update({"status": "FAILED"})
        db.commit()  # This will fail
    except OperationalError:
        db.rollback()

    # Restore commit
    db.commit = original_commit

    # Verify original session is intact (status should still be INIT, not FAILED)
    recovered_session = QuerySessionRepository.get(db, original_id)

    session_exists = recovered_session is not None
    status_preserved = recovered_session.status == original_status if recovered_session else False

    passed = session_exists and status_preserved
    detail = f"exists={session_exists}, status_preserved={status_preserved}, original={original_status}, current={recovered_session.status if recovered_session else 'N/A'}"

    db.close()
    return passed, detail


def test_6_2_B2_transaction_rollback_on_error():
    """
    On DB error, transaction should rollback cleanly.
    """

    db = make_sqlite_db_session()

    # Add a session to pending
    from storage.models.query_session import QuerySession
    import uuid

    session = QuerySession(
        id=str(uuid.uuid4()),
        question="Test question",
        status="INIT"
    )
    db.add(session)

    # Now simulate commit failure
    original_commit = db.commit

    def failing_commit():
        raise OperationalError("COMMIT", {}, Exception("DB down"))

    db.commit = failing_commit  # type: ignore

    try:
        db.commit()
    except OperationalError:
        db.rollback()

    # Restore and check
    db.commit = original_commit

    # Session should NOT be in DB (rolled back)
    count = db.query(QuerySession).count()

    passed = count == 0
    detail = f"sessions_after_rollback={count} (expected 0)"

    db.close()
    return passed, detail


def test_6_2_C1_error_response_is_json():
    """
    DB error responses should be valid JSON with detail field.
    """

    db = make_sqlite_db_session()
    app = make_app_with_router()

    def failing_commit():
        raise OperationalError("INSERT", {}, Exception("DB down"))

    db.commit = failing_commit  # type: ignore

    from backend.api import routes as routes_module

    def override_get_db() -> Generator:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[routes_module.get_db] = override_get_db

    client = TestClient(app)

    resp = client.post("/api/query", json={"question": "test"})

    is_json = resp.headers.get("content-type", "").startswith("application/json")
    body = resp.json()
    has_detail = "detail" in body

    passed = is_json and has_detail
    detail = f"is_json={is_json}, has_detail={has_detail}, body={body}"

    db.close()
    return passed, detail


def test_6_2_C2_error_message_does_not_leak_internals():
    """
    Error messages should not expose internal DB details or stack traces.
    """

    db = make_sqlite_db_session()
    app = make_app_with_router()

    def failing_commit():
        raise OperationalError("INSERT INTO sessions", {}, Exception("connection refused to localhost:5432"))

    db.commit = failing_commit  # type: ignore

    from backend.api import routes as routes_module

    def override_get_db() -> Generator:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[routes_module.get_db] = override_get_db

    client = TestClient(app)

    resp = client.post("/api/query", json={"question": "test"})
    body = resp.json()
    detail_msg = body.get("detail", "")

    # Should NOT contain internal details
    no_sql = "INSERT" not in detail_msg.upper()
    no_host = "localhost" not in detail_msg.lower()
    no_port = "5432" not in detail_msg
    no_stack = "Traceback" not in detail_msg

    passed = no_sql and no_host and no_port and no_stack
    detail = f"no_sql={no_sql}, no_host={no_host}, no_port={no_port}, no_stack={no_stack}, msg='{detail_msg}'"

    db.close()
    return passed, detail


def run_all_tests() -> bool:
    print_header()

    tests = [
        ("6.2.A1", "Submit query DB down -> 503", test_6_2_A1_submit_query_db_unavailable_returns_503),
        ("6.2.A2", "DB down -> no partial writes", test_6_2_A2_db_failure_no_partial_writes),
        ("6.2.A3", "Status endpoint DB down -> 503", test_6_2_A3_status_endpoint_db_unavailable_returns_503),
        ("6.2.A4", "Result endpoint DB down -> 503", test_6_2_A4_result_endpoint_db_unavailable_returns_503),
        ("6.2.B1", "No corrupted sessions on failure", test_6_2_B1_no_corrupted_sessions_on_failure),
        ("6.2.B2", "Transaction rollback on error", test_6_2_B2_transaction_rollback_on_error),
        ("6.2.C1", "Error response is JSON", test_6_2_C1_error_response_is_json),
        ("6.2.C2", "Error msg no internal leaks", test_6_2_C2_error_message_does_not_leak_internals),
    ]

    passed_count = 0
    failed_count = 0

    for test_id, name, fn in tests:
        try:
            passed, detail = fn()
            print_result(test_id, name, passed, detail)
            if passed:
                passed_count += 1
            else:
                failed_count += 1
        except Exception as exc:
            print_result(test_id, name, False, f"Exception: {type(exc).__name__}: {exc}")
            failed_count += 1

    print_summary(passed_count, failed_count, len(tests))
    return failed_count == 0


if __name__ == "__main__":
    ok = run_all_tests()
    raise SystemExit(0 if ok else 1)
