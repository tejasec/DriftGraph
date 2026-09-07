"""
Data models for Knowledge Graph nodes, edges, and communities.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Node(BaseModel):
    id: str
    name: str
    type: str = "CONCEPT"
    description: Optional[str] = None
    embedding: Optional[List[float]] = None
    provenance_chunk_ids: List[str] = Field(default_factory=list)
    degree: int = 0
    community_id: Optional[int] = None
    community_levels: Dict[int, int] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    id: str
    source: str
    target: str
    predicate: str
    description: Optional[str] = None
    weight: float = 1.0
    confidence: float = 1.0
    provenance_chunk_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Community(BaseModel):
    id: int
    level: int
    parent_id: Optional[int] = None
    name: str
    node_ids: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    findings: List[str] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)
    confidence: float = 1.0
