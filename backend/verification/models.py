from enum import Enum
from typing import List
from pydantic import BaseModel


class VerificationStatus(str, Enum):
    AGREEMENT = "AGREEMENT"
    CONFLICT = "CONFLICT"
    SINGLE_SOURCE = "SINGLE_SOURCE"


class VerifiedClaim(BaseModel):
    claim: str
    sources: List[str]
    status: VerificationStatus
