"""
API Routes package.
"""

from driftgraph.serve.routes.ingest import router as ingest_router
from driftgraph.serve.routes.query import router as query_router
from driftgraph.serve.routes.graph import router as graph_router
from driftgraph.serve.routes.export import router as export_router
from driftgraph.serve.routes.status import router as status_router

__all__ = [
    "ingest_router",
    "query_router",
    "graph_router",
    "export_router",
    "status_router",
]
