"""driftgraph/serve/routes/analytics.py

Graph Intelligence and Analytics API routes:
- God Node identification & Graph Density
- Path discovery & explanation between two concepts ("What connects X to Y?")
- Surprising connection detection
- Suggested exploratory questions from community boundaries
- Subgraph extraction around key concepts
"""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from driftgraph.config import config
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.analytics import (
    GraphAnalyticsEngine,
    GraphAnalyticsReport,
    PathResult,
    SuggestedQuestion,
    SubgraphData,
)

router = APIRouter(prefix="/api/graph/analytics", tags=["Analytics"])


class PathQueryRequest(BaseModel):
    source: str
    target: str


def _get_engine() -> GraphAnalyticsEngine:
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    return GraphAnalyticsEngine(storage)


@router.get("", response_model=GraphAnalyticsReport)
async def get_graph_analytics_report():
    """Return full graph intelligence report: God nodes, density, bridges, questions."""
    engine = _get_engine()
    return await engine.generate_report()


@router.post("/path", response_model=PathResult)
async def find_concept_path(req: PathQueryRequest):
    """Find shortest path and narrative connection between two concepts."""
    if not req.source.strip() or not req.target.strip():
        raise HTTPException(status_code=400, detail="Source and Target cannot be empty.")
    engine = _get_engine()
    return await engine.find_shortest_path(req.source, req.target)


@router.get("/questions", response_model=List[SuggestedQuestion])
async def get_suggested_questions():
    """Return suggested exploratory questions synthesized from graph topology."""
    engine = _get_engine()
    report = await engine.generate_report()
    return report.suggested_questions


@router.get("/subgraph", response_model=SubgraphData)
async def get_concept_subgraph(
    entity: str = Query(..., description="Name or ID of central entity"),
    depth: int = Query(1, ge=1, le=3, description="Hop depth")
):
    """Extract local subgraph centered on an entity."""
    engine = _get_engine()
    return await engine.extract_subgraph(entity, depth=depth)
