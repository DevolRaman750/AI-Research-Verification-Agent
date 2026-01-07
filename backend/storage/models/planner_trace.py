import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from storage.base import Base
from storage.models.query_session import UUID_COL_TYPE


class PlannerTrace(Base):
    __tablename__ = "planner_traces"

    id = Column(
        UUID_COL_TYPE,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    session_id = Column(
        UUID_COL_TYPE,
        ForeignKey("query_sessions.id", ondelete="CASCADE"),
        nullable=False
    )

    attempt_number = Column(
        Integer,
        nullable=False
    )

    planner_state = Column(
        String(20),   # INIT / RESEARCH / VERIFY / SYNTHESIZE / FAILED
        nullable=False
    )

    verification_decision = Column(
        String(20),   # ACCEPT / RETRY / STOP
        nullable=True
    )

    strategy_used = Column(
        String(30),   # BASE / BROADEN_QUERY / AUTHORITATIVE_SITES / etc.
        nullable=True
    )

    num_docs = Column(
        Integer,
        nullable=True
    )

    stop_reason = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
