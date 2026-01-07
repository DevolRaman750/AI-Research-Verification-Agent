import uuid
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.sql import func

from storage.base import Base


def _uuid_col_type():
    try:
        # SQLAlchemy 2.x portable UUID type
        from sqlalchemy import Uuid  # type: ignore

        return Uuid(as_uuid=False)
    except Exception:
        return String(36)


UUID_COL_TYPE = _uuid_col_type()

class QuerySession(Base):
    __tablename__ = "query_sessions"

    id = Column(
        UUID_COL_TYPE,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    question = Column(
        Text,
        nullable=False
    )

    status = Column(
        String(20),   # DONE / FAILED
        nullable=False
    )

    final_confidence_level = Column(
        String(10),   # HIGH / MEDIUM / LOW
        nullable=True
    )

    final_confidence_reason = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

