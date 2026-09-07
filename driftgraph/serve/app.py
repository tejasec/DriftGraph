"""
FastAPI Application for DriftGraph Knowledge Graph Server.
"""

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import structlog

from driftgraph.config import config
from driftgraph.serve.routes import ingest_router, query_router, graph_router, export_router, status_router
from driftgraph.graph.storage import SQLiteStorage

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context: initialize SQLite database schema and warm models."""
    logger.info("driftgraph_server_starting", host=config.server.host, port=config.server.port)
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    await storage.initialize_schema()
    yield
    logger.info("driftgraph_server_shutting_down")


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="DriftGraph API",
        description="Local-First GraphRAG Knowledge Graph Service",
        version=config.app.version,
        lifespan=lifespan
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(ingest_router)
    app.include_router(query_router)
    app.include_router(graph_router)
    app.include_router(export_router)
    app.include_router(status_router)

    # Health check
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "app": config.app.name,
            "version": config.app.version
        }

    # Static frontend files
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

        @app.get("/")
        async def serve_index():
            index_path = frontend_dir / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            return {"message": "Frontend index.html not found."}

    return app


app = create_app()
