"""
Data models for query requests, responses, and search context.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class Citation(BaseModel):
    source_type: Literal["chunk", "community", "node"]
    id: str
    title: Optional[str] = None
    text_snippet: str
    score: float = 1.0


class QueryRequest(BaseModel):
    query: str
    mode: Optional[Literal["auto", "global", "local"]] = "auto"
    top_k: int = 5
    stream: bool = False


class QueryResponse(BaseModel):
    query: str
    mode_used: Literal["global", "local"]
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    confidence: float = 1.0
    latency_ms: float = 0.0


class SearchContextItem(BaseModel):
    id: str
    type: str
    title: str
    content: str
    score: float
