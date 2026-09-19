"""driftgraph/analytics/models.py

Data models for Graph Analytics, God Node Identification, Path Finding, and Suggested Questions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GodNode(BaseModel):
    id: str
    name: str
    type: str
    degree: int
    pagerank: float
    betweenness: float
    hub_score: float
    explanation: str


class PathStep(BaseModel):
    source: str
    relation: str
    target: str
    weight: float = 1.0


class PathResult(BaseModel):
    source: str
    target: str
    path_found: bool
    hops: int = 0
    node_sequence: List[str] = Field(default_factory=list)
    steps: List[PathStep] = Field(default_factory=list)
    narrative: str = ""


class SurprisingConnection(BaseModel):
    source_name: str
    source_type: str
    target_name: str
    target_type: str
    relation: str
    source_community_id: Optional[Any] = None
    target_community_id: Optional[Any] = None
    rationale: str = ""


class SuggestedQuestion(BaseModel):
    question: str
    category: str  # "cross_community", "central_hub", "boundary"
    entities_involved: List[str]
    rationale: str


class SubgraphData(BaseModel):
    center_entity: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    depth: int


class GraphAnalyticsReport(BaseModel):
    node_count: int
    edge_count: int
    community_count: int
    density: float
    is_connected: bool
    god_nodes: List[GodNode]
    top_relations: List[Dict[str, Any]]
    surprising_connections: List[SurprisingConnection]
    suggested_questions: List[SuggestedQuestion]
