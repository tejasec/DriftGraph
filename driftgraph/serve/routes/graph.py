"""
Graph API routes: retrieve nodes, edges, communities, and Cytoscape.js elements.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from driftgraph.config import config
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.graph.builder import KnowledgeGraphBuilder
from driftgraph.graph.models import Community

router = APIRouter(prefix="/api/graph", tags=["Graph"])


@router.get("")
async def get_graph_elements() -> Dict[str, Any]:
    """Return Cytoscape.js compatible {nodes: [], edges: []} graph payload."""
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    nodes = await storage.get_all_nodes()
    edges = await storage.get_all_edges()

    builder = KnowledgeGraphBuilder()
    return builder.to_cytoscape_elements(nodes, edges)


@router.get("/communities", response_model=List[Community])
async def get_communities(level: Optional[int] = None):
    """Return detected hierarchical communities."""
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    return await storage.get_communities(level=level)


@router.get("/notes")
async def get_notes() -> List[Dict[str, Any]]:
    """Return all notes for the frontend editor."""
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    return await storage.get_all_notes()


@router.get("/stats")
async def get_graph_stats() -> Dict[str, Any]:
    """Return graph metrics."""
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    nodes = await storage.get_all_nodes()
    edges = await storage.get_all_edges()
    comms = await storage.get_communities()

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "community_count": len(comms),
        "levels": list(set(c.level for c in comms)) if comms else [0]
    }
