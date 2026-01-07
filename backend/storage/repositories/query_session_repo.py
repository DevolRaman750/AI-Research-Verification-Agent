import uuid
from sqlalchemy.orm import Session
from storage.models.query_session import QuerySession


class QuerySessionRepository:

    @staticmethod
    def create(db: Session, question: str) -> QuerySession:
        session = QuerySession(
            id=str(uuid.uuid4()),
            question=question,
            status="INIT"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def update_final_status(
        db: Session,
        session_id,
        status: str,
        confidence_level: str,
        confidence_reason: str
    ):
        session_id = str(session_id)
        db.query(QuerySession).filter(
            QuerySession.id == session_id
        ).update({
            "status": status,
            "final_confidence_level": confidence_level,
            "final_confidence_reason": confidence_reason
        })
        db.commit()

    @staticmethod
    def update_status(db: Session, session_id, status: str) -> None:
        session_id = str(session_id)
        db.query(QuerySession).filter(
            QuerySession.id == session_id
        ).update({"status": status})
        db.commit()

    @staticmethod
    def get(db: Session, session_id) -> QuerySession | None:
        session_id = str(session_id)
        return db.query(QuerySession).filter(
            QuerySession.id == session_id
        ).first()
