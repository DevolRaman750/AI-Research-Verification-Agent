import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from storage.base import Base

# Load .env file if present
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/ai_research_agent"
)

# Ensure models are imported so Base.metadata has tables.
from storage import models as _models  # noqa: F401

engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
    "pool_size": 20,           # Base pool connections
    "max_overflow": 30,        # Extra connections under load
    "pool_timeout": 60,        # Wait up to 60s for a connection
    "pool_recycle": 1800,      # Recycle connections every 30 min
}

# Allow local runs without Postgres by setting DATABASE_URL to sqlite.
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    # SQLite doesn't support pool_size/max_overflow the same way
    engine_kwargs.pop("pool_size", None)
    engine_kwargs.pop("max_overflow", None)
    engine_kwargs.pop("pool_recycle", None)

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
def get_db():
    """
    Yields a database session and ensures cleanup.
    Safe for API, tests, and scripts.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def init_db():
    """
    Creates all tables.
    Call once at startup or via script.
    """
    Base.metadata.create_all(bind=engine)

