from sqlalchemy import Column, Text, DateTime, ForeignKey

from storage.base import Base
from storage.models.query_session import UUID_COL_TYPE


class QueryCache(Base):
    __tablename__ = "query_cache"

    query_hash = Column(
        Text,
        primary_key=True
    )

    session_id = Column(
        UUID_COL_TYPE,
        ForeignKey("query_sessions.id", ondelete="CASCADE"),
        nullable=False
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False
    )
