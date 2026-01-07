import uuid
from sqlalchemy.orm import Session
from storage.models.planner_trace import PlannerTrace


class PlannerTraceRepository:

    @staticmethod
    def log(
        db: Session,
        session_id,
        attempt_number: int,
        planner_state: str,
        verification_decision: str,
        strategy_used: str,
        num_docs: int,
        stop_reason: str | None = None
    ):
        trace = PlannerTrace(
            id=str(uuid.uuid4()),
            session_id=str(session_id),
            attempt_number=attempt_number,
            planner_state=planner_state,
            verification_decision=verification_decision,
            strategy_used=strategy_used,
            num_docs=num_docs,
            stop_reason=stop_reason
        )
        db.add(trace)
        db.commit()

    @staticmethod
    def list_by_session(db: Session, session_id):
        session_id = str(session_id)
        return (
            db.query(PlannerTrace)
            .filter(PlannerTrace.session_id == session_id)
            .order_by(PlannerTrace.attempt_number.asc())
            .all()
        )
