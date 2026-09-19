"""driftgraph/serve/routes package"""

from driftgraph.serve.routes.ingest import router as ingest_router
from driftgraph.serve.routes.query import router as query_router
from driftgraph.serve.routes.graph import router as graph_router
from driftgraph.serve.routes.export import router as export_router
from driftgraph.serve.routes.status import router as status_router
from driftgraph.serve.routes.voice import router as voice_router
from driftgraph.serve.routes.classify import router as classify_router
from driftgraph.serve.routes.notes import router as notes_router
from driftgraph.serve.routes.analytics import router as analytics_router

__all__ = [
    "ingest_router",
    "query_router",
    "graph_router",
    "export_router",
    "status_router",
    "voice_router",
    "classify_router",
    "notes_router",
    "analytics_router",
]
