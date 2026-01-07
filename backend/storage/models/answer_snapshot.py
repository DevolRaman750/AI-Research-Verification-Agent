import uuid
from sqlalchemy import Column, Text, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from storage.base import Base
from storage.models.query_session import UUID_COL_TYPE


class AnswerSnapshot(Base):
    __tablename__ = "answer_snapshots"

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

    answer_text = Column(
        Text,
        nullable=False
    )

    confidence_level = Column(
        String(10),   # HIGH / MEDIUM / LOW
        nullable=False
    )

    confidence_reason = Column(
        Text,
        nullable=False
    )

    notes = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
