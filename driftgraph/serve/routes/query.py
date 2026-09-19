"""
Query API route: handle global GraphRAG and local search requests.
"""

from fastapi import APIRouter, HTTPException, Depends
import structlog
from driftgraph.config import config
from driftgraph.query.models import QueryRequest, QueryResponse
from driftgraph.query.engine import QueryEngine
from driftgraph.embed.sbert import SBERTEmbedder
from driftgraph.graph.vector_store import VectorIndex
from driftgraph.graph.storage import SQLiteStorage

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/query", tags=["Query"])

_query_engine: QueryEngine | None = None


def get_query_engine() -> QueryEngine:
    global _query_engine
    if _query_engine is None:
        embedder = SBERTEmbedder()
        vec_index = VectorIndex(dimension=embedder.dimension, index_path=config.database.vector_index_path)
        if not vec_index.load():
            logger.warning(
                "vector_index_load_failed",
                index_path=config.database.vector_index_path,
                hint="Run a build first; falling back to FTS-only search."
            )
        storage = SQLiteStorage(db_path=config.database.sqlite_path)
        _query_engine = QueryEngine(
            embedder=embedder,
            vector_index=vec_index,
            storage=storage,
            llm_model=config.llm.model,
            llm_base_url=config.llm.base_url,
            top_k=config.retrieval.top_k,
            hybrid_alpha=config.retrieval.hybrid_alpha,
            llm_temperature=config.llm.temperature,
            llm_provider=config.llm.provider,
            llm_api_key=config.llm.get_api_key()
        )
    return _query_engine


def invalidate_query_engine() -> None:
    """Drop the cached QueryEngine so a fresh build/IPA re-init is picked up."""
    global _query_engine
    _query_engine = None


@router.post("", response_model=QueryResponse)
async def post_query(request: QueryRequest, engine: QueryEngine = Depends(get_query_engine)):
    """Execute search (Global or Local) on the knowledge graph."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    return await engine.query(request)
