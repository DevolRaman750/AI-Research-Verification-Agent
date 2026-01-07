import uuid
from sqlalchemy.orm import Session
from storage.models.search_log import SearchLog


class SearchLogRepository:

    @staticmethod
    def log(
        db: Session,
        session_id,
        attempt_number: int,
        query_used: str,
        num_docs: int,
        success: bool
    ):
        log = SearchLog(
            id=str(uuid.uuid4()),
            session_id=str(session_id),
            attempt_number=attempt_number,
            query_used=query_used,
            num_docs=num_docs,
            success=success
        )
        db.add(log)
        db.commit()

    @staticmethod
    def list_by_session(db: Session, session_id):
        session_id = str(session_id)
        return (
            db.query(SearchLog)
            .filter(SearchLog.session_id == session_id)
            .order_by(SearchLog.attempt_number.asc())
            .all()
        )
