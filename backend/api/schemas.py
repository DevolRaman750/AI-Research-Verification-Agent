from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class QuerySubmitRequest(BaseModel):
    question: str = Field(..., min_length=1)


class QuerySubmitResponse(BaseModel):
    session_id: UUID
    status: Literal["PROCESSING"]


class QueryStatusResponse(BaseModel):
    status: str


class EvidenceItem(BaseModel):
    claim: str
    status: str
    sources: List[str]


class QueryResultResponse(BaseModel):
    answer: str
    confidence_level: str
    confidence_reason: str
    evidence: List[EvidenceItem]
    notes: Optional[str] = None


class PlannerTraceItem(BaseModel):
    attempt_number: int
    planner_state: str
    verification_decision: Optional[str] = None
    strategy_used: Optional[str] = None
    num_docs: Optional[int] = None
    created_at: Optional[datetime] = None


class SearchLogItem(BaseModel):
    attempt_number: int
    query_used: str
    num_docs: int
    success: bool
    created_at: Optional[datetime] = None


class QueryTraceResponse(BaseModel):
    planner_traces: List[PlannerTraceItem]
    search_logs: List[SearchLogItem]
