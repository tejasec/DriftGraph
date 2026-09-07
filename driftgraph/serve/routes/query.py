"""
Query API route: handle global GraphRAG and local search requests.
"""

from fastapi import APIRouter, HTTPException, Depends
from driftgraph.config import config
from driftgraph.query.models import QueryRequest, QueryResponse
from driftgraph.query.engine import QueryEngine
from driftgraph.embed.sbert import SBERTEmbedder
from driftgraph.graph.vector_store import VectorIndex
from driftgraph.graph.storage import SQLiteStorage

router = APIRouter(prefix="/api/query", tags=["Query"])

_query_engine: QueryEngine | None = None


def get_query_engine() -> QueryEngine:
    global _query_engine
    if _query_engine is None:
        embedder = SBERTEmbedder()
        vec_index = VectorIndex(dimension=embedder.dimension, index_path=config.database.vector_index_path)
        vec_index.load()
        storage = SQLiteStorage(db_path=config.database.sqlite_path)
        _query_engine = QueryEngine(
            embedder=embedder,
            vector_index=vec_index,
            storage=storage,
            llm_model=config.llm.model,
            llm_base_url=config.llm.base_url
        )
    return _query_engine


@router.post("", response_model=QueryResponse)
async def post_query(request: QueryRequest, engine: QueryEngine = Depends(get_query_engine)):
    """Execute search (Global or Local) on the knowledge graph."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    return await engine.query(request)
