import uuid
from sqlalchemy.orm import Session
from storage.models.answer_snapshot import AnswerSnapshot


class AnswerSnapshotRepository:

    @staticmethod
    def create(
        db: Session,
        session_id,
        answer_text: str,
        confidence_level: str,
        confidence_reason: str
    ):
        snapshot = AnswerSnapshot(
            id=str(uuid.uuid4()),
            session_id=str(session_id),
            answer_text=answer_text,
            confidence_level=confidence_level,
            confidence_reason=confidence_reason
        )
        db.add(snapshot)
        db.commit()
        return snapshot

    @staticmethod
    def get_latest_by_session(db: Session, session_id):
        session_id = str(session_id)
        return (
            db.query(AnswerSnapshot)
            .filter(AnswerSnapshot.session_id == session_id)
            .order_by(AnswerSnapshot.created_at.desc())
            .first()
        )
