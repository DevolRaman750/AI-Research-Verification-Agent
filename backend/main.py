import sys
from pathlib import Path

from fastapi import FastAPI

# Allow existing modules to import using the historical layout (e.g. `verification.*`, `planner.*`)
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
	sys.path.insert(0, str(BACKEND_DIR))

from backend.api.routes import router as api_router
from backend.storage.db import init_db

app = FastAPI(title="AI Research Agent API", version="1.0.0")


@app.on_event("startup")
def _startup_init_db() -> None:
	# Best-effort table creation for local/dev runs.
	# If DATABASE_URL points at an unreachable DB, API can still start.
	try:
		init_db()
	except Exception:
		pass

app.include_router(api_router)
