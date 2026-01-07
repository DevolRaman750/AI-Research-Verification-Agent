from typing import List, Dict
from pydantic import BaseModel, Field


class WebDocument(BaseModel):
    url: str
    title: str | None = None
    text: str
    metadata: Dict[str, str] = Field(default_factory=dict)


class WebEnvironmentState(BaseModel):
    query: str | None = None
    visited_urls: List[str] = Field(default_factory=list)
    documents: List[WebDocument] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
