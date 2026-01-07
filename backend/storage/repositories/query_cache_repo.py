from sqlalchemy.orm import Session
from storage.models.query_cache import QueryCache
from datetime import datetime, timedelta


class QueryCacheRepository:

    @staticmethod
    def get_valid(db: Session, query_hash: str):
        return db.query(QueryCache).filter(
            QueryCache.query_hash == query_hash,
            QueryCache.expires_at > datetime.utcnow()
        ).first()

    @staticmethod
    def store(db: Session, query_hash: str, session_id, ttl_seconds: int):
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        cache = QueryCache(
            query_hash=query_hash,
            session_id=str(session_id),
            expires_at=expires_at
        )
        db.merge(cache)
        db.commit()

    @staticmethod
    def get(db: Session, query_hash: str):
        return QueryCacheRepository.get_valid(db=db, query_hash=query_hash)

    @staticmethod
    def set(
        db: Session,
        query_hash: str,
        session_id,
        expires_at
    ):
        cache = QueryCache(
            query_hash=query_hash,
            session_id=str(session_id),
            expires_at=expires_at
        )
        db.merge(cache)
        db.commit()
