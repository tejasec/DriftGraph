"""
Unified QueryEngine interface for DriftGraph.
"""

import time
from typing import Optional
import structlog

from driftgraph.embed.base import BaseEmbedder
from driftgraph.graph.vector_store import VectorIndex
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.query.models import QueryRequest, QueryResponse
from driftgraph.query.router import QueryRouter
from driftgraph.query.local import LocalSearchEngine
from driftgraph.query.global_search import GlobalSearchEngine

logger = structlog.get_logger(__name__)


class QueryEngine:
    """Unified engine routing queries between Global GraphRAG and Local Hybrid search."""

    def __init__(
        self,
        embedder: BaseEmbedder,
        vector_index: VectorIndex,
        storage: SQLiteStorage,
        llm_model: str = "llama3.1:8b-instruct-q4_K_M",
        llm_base_url: str = "http://localhost:11434",
        top_k: int = 8,
        hybrid_alpha: float = 0.5,
        llm_temperature: float = 0.1,
        llm_timeout: float = 30.0,
        llm_provider: Optional[str] = None,
        llm_api_key: Optional[str] = None,
    ):
        from driftgraph.config import config
        self.router = QueryRouter()
        self.storage = storage
        self.top_k = top_k
        self.hybrid_alpha = hybrid_alpha
        self.llm_provider = llm_provider or getattr(config.llm, "provider", "ollama")
        self.llm_api_key = llm_api_key or config.llm.get_api_key()
        self.local_engine = LocalSearchEngine(
            embedder=embedder,
            vector_index=vector_index,
            storage=storage,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            temperature=llm_temperature,
            timeout=llm_timeout,
            llm_provider=self.llm_provider,
            llm_api_key=self.llm_api_key
        )
        self.global_engine = GlobalSearchEngine(
            storage=storage,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            temperature=llm_temperature,
            timeout=llm_timeout,
            llm_provider=self.llm_provider,
            llm_api_key=self.llm_api_key
        )

    async def query(self, request: QueryRequest) -> QueryResponse:
        """Route and execute query."""
        start_time = time.perf_counter()
        target_mode = self.router.route(request.query, explicit_mode=request.mode or "auto")

        if target_mode == "global":
            resp = await self.global_engine.search(request.query)
        else:
            resp = await self.local_engine.search(
                request.query,
                top_k=request.top_k or self.top_k,
                hybrid_alpha=self.hybrid_alpha
            )

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        resp.latency_ms = round(latency_ms, 2)
        return resp
