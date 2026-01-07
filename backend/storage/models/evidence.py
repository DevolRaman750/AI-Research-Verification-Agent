import uuid
from sqlalchemy import JSON, Column, ForeignKey, String, Text

from storage.base import Base
from storage.models.query_session import UUID_COL_TYPE


class Evidence(Base):
    __tablename__ = "evidence"

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

    claim_text = Column(
        Text,
        nullable=False
    )

    verification_status = Column(
        String(20),   # AGREEMENT / CONFLICT / SINGLE_SOURCE
        nullable=False
    )

    source_urls = Column(
        JSON,
        nullable=False
    )
