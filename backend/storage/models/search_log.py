import uuid
from sqlalchemy import Column, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from storage.base import Base
from storage.models.query_session import UUID_COL_TYPE

class SearchLog(Base):
    __tablename__ = "search_logs"

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

    query_used = Column(
        Text,
        nullable=False
    )

    num_docs = Column(
        Integer,
        nullable=False
    )

    success = Column(
        Boolean,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
