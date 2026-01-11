# AI Research Agent – Copilot Instructions

## Architecture (what calls what)
- FastAPI entrypoint: `backend/main.py`; routes live in `backend/api/routes.py` (mounted under `/api`).
- `POST /api/query` creates a `QuerySession` row, then runs `PlannerAgent.run()` via `BackgroundTasks` (request returns immediately).
- `PlannerAgent` (`backend/planner/planner_agent.py`) is the orchestrator state machine: `INIT → RESEARCH → VERIFY → SYNTHESIZE → DONE/FAILED`.
  - Retries + strategy rotation via `SearchStrategy`, with budgets (`max_attempts`, `max_searches`, `num_docs` escalation).
  - Query cache key is a hash of normalized question + strategy + `num_docs`; cache lookup only happens on retries (attempt > 1).
  - Cache is stored only when the last `VerificationDecision` is `ACCEPT` (never on `STOP`).
- `ResearchAgent` (`backend/agents/research_agent.py`) is a single-attempt pipeline:
  - `WebEnvironment.run()` → `ClaimExtractor.extract_claims()` → `VerificationEngine.verify()` → `ConfidenceScorer.score()` → `AnswerSynthesizer.synthesize()`.
- Web I/O: `backend/environments/web/` (Google CSE search, then fetch+extract); domain blocklist lives in `backend/constants/rules.py`.
- Persistence uses repository helpers under `backend/storage/repositories/`; `PlannerAgent._handle_synthesize()` writes `AnswerSnapshot` + bulk `Evidence`.
- `GET /api/query/{session_id}/trace` is TEA-safe metadata only, and is gated by `INTERNAL_TRACE_TOKEN` (header: `X-Internal-Token`).

## Run & debug
- Backend deps: `pip install -r backend/requirements.txt`
- Run API (dev): `uvicorn backend.main:app --reload`
- DB config: `backend/storage/db.py` loads `.env`; default is local Postgres, but you can run with SQLite by setting `DATABASE_URL` to `sqlite:///./dev.db`.
- Web search config: `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_CX`, optional `GOOGLE_SEARCH_ENDPOINT`.
- Tests are script-style contract checks under `backend/tests/` (they hit `http://127.0.0.1:8000` via `requests`).
  - Typical flow: start the API, then run `python backend/tests/test_api_submit_query.py` (and similar files).

## Repo-specific conventions / footguns
- Import layout is intentionally mixed:
  - API code imports `backend.*`, while many internal modules use the “historical layout” (`agents.*`, `storage.*`, `verification.*`).
  - `backend/main.py` and `backend/api/routes.py` prepend the backend dir to `sys.path` to support this.
  - If you refactor imports, do it consistently (API + planner + scripts), or you’ll break runtime.
- LLM calls: `backend/utils/llm_client.py` uses `google-genai` (Gemini) with deterministic settings; it currently contains a hardcoded API key (avoid copying it into issues/logs; prefer env wiring if you touch this code).

## Frontend (current state)
- `frontend/` is a Vite+React app: `npm install` then `npm run dev`.
- UI currently uses the mock API in `frontend/src/mock/api.js` (it does not call the FastAPI backend yet).
