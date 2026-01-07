import uuid
from sqlalchemy.orm import Session
from storage.models.evidence import Evidence


class EvidenceRepository:

    @staticmethod
    def bulk_create(
        db: Session,
        session_id,
        evidence_items: list[dict]
    ):
        session_id = str(session_id)
        records = []

        for item in evidence_items:
            records.append(
                Evidence(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    claim_text=item["claim"],
                    verification_status=item["status"],
                    source_urls=item["sources"]
                )
            )

        db.add_all(records)
        db.commit()

    @staticmethod
    def list_by_session(db: Session, session_id):
        session_id = str(session_id)
        return (
            db.query(Evidence)
            .filter(Evidence.session_id == session_id)
            .all()
        )
