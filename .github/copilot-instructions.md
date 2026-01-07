# AI Research Agent – Copilot Instructions

## Architecture (what calls what)
- API entrypoint is `backend/main.py` (FastAPI) with routes in `backend/api/routes.py`.
- `/api/query` creates a `QuerySession` and runs `PlannerAgent.run()` in a FastAPI `BackgroundTasks` job.
- `PlannerAgent` (`backend/planner/planner_agent.py`) is the orchestrator/state machine: `INIT → RESEARCH → VERIFY → SYNTHESIZE → DONE/FAILED`.
  - Implements retries, query strategy rotation (`SearchStrategy`), and a search budget (`max_searches`).
  - Persists status + artifacts via `backend/storage/repositories/*`.
  - Caches results by `query_hash` only when the last `VerificationDecision` is `ACCEPT`.
- `ResearchAgent` (`backend/agents/research_agent.py`) is a single-attempt pipeline:
  - `WebEnvironment.run()` → `ClaimExtractor.extract_claims()` → `VerificationEngine.verify()` → `ConfidenceScorer.score()` → `AnswerSynthesizer.synthesize()`.
- Web I/O lives in `backend/environments/web/` (Google CSE search + fetch + extract, domain blocklist in `backend/constants/rules.py`).
- Verification lives in `backend/verification/` (claim grouping + polarity-based conflict detection; outputs `VerifiedClaim` / `VerificationStatus`).

## Run & debug
- Install deps: `pip install -r backend/requirements.txt`
- Run API (dev): `uvicorn backend.main:app --reload`
- Env vars used by the API:
  - `DATABASE_URL` (defaults to local Postgres in `backend/storage/db.py`)
  - `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_CX`, optional `GOOGLE_SEARCH_ENDPOINT`
  - `INTERNAL_TRACE_TOKEN` gates `/api/query/{session_id}/trace`
- Tests are plain scripts (no central runner): `python backend/test_planner_agent.py`, `python backend/test_research_agent.py`, etc.

## Repo-specific conventions / footguns
- Import layout is intentionally mixed: many modules assume `backend/` is on `sys.path` (e.g., tests import `planner.*`).
  - `backend/main.py` and `backend/api/routes.py` explicitly insert the backend dir into `sys.path` to support this “historical layout”.
  - If you refactor imports, do it consistently across API + scripts.
- Persistence pattern: repositories are simple `@staticmethod` helpers under `backend/storage/repositories/`; `PlannerAgent._handle_synthesize()` writes `AnswerSnapshot` + bulk evidence.
- LLM calls: use `backend/utils/llm_client.py` (`llm_complete`, deterministic config). It currently contains a hardcoded Gemini API key.
- `backend/synthesis/answer_synthesizer.py` contains duplicated/legacy code blocks; the active runtime class is the bottom `AnswerSynthesizer` that is constructed with no args.
