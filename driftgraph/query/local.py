"""
Local Search Engine: Hybrid Vector Similarity (FAISS) + Full-Text Search (SQLite FTS5)
+ LightRAG Dual-Level Knowledge Graph Expansion + Multi-List RRF.
"""

import os
from typing import List, Dict, Any, Optional
import httpx
import structlog

from driftgraph.config import config
from driftgraph.embed.base import BaseEmbedder
from driftgraph.graph.vector_store import VectorIndex
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.query.models import Citation, QueryResponse
from driftgraph.query.dual_level import DualLevelRetriever, DualLevelResult

logger = structlog.get_logger(__name__)

LOCAL_ANSWER_PROMPT = """You are DriftGraph, an intelligent assistant answering questions based strictly on the user's personal knowledge base.

CONTEXT RETRIEVED FROM KNOWLEDGE GRAPH & NOTES:
{context}

QUESTION:
{query}

INSTRUCTIONS:
1. Answer the question accurately using ONLY the retrieved context.
2. If the context contains entity relationships or community themes, synthesize them cohesively with note excerpts.
3. If the context does not contain sufficient information, state what is known and mention what is missing.
4. Be clear, concise, and direct.

ANSWER:"""


class LocalSearchEngine:
    """Performs hybrid retrieval (vector + keyword + dual-level graph) and generates targeted answers."""

    def __init__(
        self,
        embedder: BaseEmbedder,
        vector_index: VectorIndex,
        storage: SQLiteStorage,
        llm_model: str = "llama3.1:8b-instruct-q4_K_M",
        llm_base_url: str = "http://localhost:11434",
        temperature: float = 0.1,
        timeout: float = 30.0,
        dual_level: Optional[bool] = None,
        llm_provider: Optional[str] = None,
        llm_api_key: Optional[str] = None,
    ):
        self.embedder = embedder
        self.vector_index = vector_index
        self.storage = storage
        self.llm_model = llm_model
        self.llm_base_url = llm_base_url
        self.llm_provider = llm_provider or getattr(config.llm, "provider", "ollama")
        self.llm_api_key = llm_api_key or config.llm.get_api_key()
        self.temperature = temperature
        self.timeout = timeout

        env_dual = os.environ.get("DRIFTGRAPH_DUAL_LEVEL", "1") != "0"
        cfg_dual = getattr(config.retrieval, "dual_level", True)
        self.dual_level_enabled = (dual_level if dual_level is not None else (env_dual and cfg_dual))
        self.dual_level_weight = getattr(config.retrieval, "dual_level_weight", 0.5)

        self.dual_retriever = DualLevelRetriever(
            storage=storage,
            embedder=embedder,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            timeout=timeout,
            llm_provider=self.llm_provider,
            llm_api_key=self.llm_api_key
        )

    async def search(self, query: str, top_k: int = 5, hybrid_alpha: float = 0.5) -> QueryResponse:
        """Execute hybrid search and answer generation with multi-list RRF."""
        citations: List[Citation] = []
        context_snippets: List[str] = []

        # 1. Vector Search (Dense)
        q_emb = self.embedder.embed_query(query)
        vector_hits = self.vector_index.search(q_emb, top_k=top_k)

        # 2. SQLite FTS5 Keyword Search (Lexical)
        fts_hits = await self.storage.search_chunks_fts(query, limit=top_k)

        # 3. Dual-Level Graph Retrieval (Entities + Communities)
        dual_res: Optional[DualLevelResult] = None
        graph_hits: List[Any] = []
        if self.dual_level_enabled:
            try:
                dual_res = await self.dual_retriever.retrieve(query, top_k_entities=top_k, top_k_communities=3)
                graph_hits = dual_res.ranked_chunks[:top_k]
            except Exception as e:
                logger.warning("dual_level_retrieval_failed", error=str(e))
                dual_res = None

        # 4. Multi-List Reciprocal Rank Fusion (RRF, k=60)
        rrf_scores: Dict[str, float] = {}
        content_map: Dict[str, Dict[str, Any]] = {}

        # Vector Channel (Dense): weight = 1 - hybrid_alpha
        w_dense = 1.0 - hybrid_alpha
        for rank, (chunk_id, sim_score) in enumerate(vector_hits):
            score = w_dense * (1.0 / (60 + rank + 1))
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + score
            content_map[chunk_id] = {"id": chunk_id, "score": sim_score}

        # FTS5 Channel (Lexical): weight = hybrid_alpha
        w_lex = hybrid_alpha
        for rank, fts_item in enumerate(fts_hits):
            chunk_id = fts_item["chunk_id"]
            score = w_lex * (1.0 / (60 + rank + 1))
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + score
            if chunk_id not in content_map:
                content_map[chunk_id] = {"id": chunk_id, "score": 0.8}
            content_map[chunk_id]["text"] = fts_item.get("text", "")
            content_map[chunk_id]["title"] = fts_item.get("title", "")

        # Dual-Level Graph Channel (Entities & Communities): weight = dual_level_weight
        if self.dual_level_enabled and graph_hits:
            w_graph = self.dual_level_weight
            for rank, (chunk_id, g_score) in enumerate(graph_hits):
                score = w_graph * (1.0 / (60 + rank + 1))
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + score
                if chunk_id not in content_map:
                    content_map[chunk_id] = {"id": chunk_id, "score": float(g_score)}

        # Sort combined by RRF score
        sorted_chunks = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # 5. Fetch chunk details from SQLite if not present in content_map
        for chunk_id, rrf_score in sorted_chunks:
            info = content_map.get(chunk_id, {})
            text = info.get("text", "")
            title = info.get("title", chunk_id)

            if not text:
                chunk_record = await self.storage.get_chunk_by_id(chunk_id)
                if chunk_record:
                    text = chunk_record.get("text", "")

            snippet = text[:300] if text else f"Reference chunk: {chunk_id}"
            if text:
                context_snippets.append(f"[{title or chunk_id}]: {snippet}")

            citations.append(Citation(
                source_type="chunk",
                id=chunk_id,
                title=title,
                text_snippet=snippet,
                score=float(rrf_score)
            ))

        # Add entity citations from dual-level retrieval
        if dual_res and dual_res.entities:
            for ent in dual_res.entities[:3]:
                citations.append(Citation(
                    source_type="node",
                    id=ent.id,
                    title=ent.name,
                    text_snippet=ent.description or f"Entity: {ent.name} ({ent.type})",
                    score=1.0
                ))

        # 6. Structured Dual-Level Context Assembly
        context_blocks = []
        if dual_res:
            if dual_res.entities:
                ent_line = ", ".join(f"{n.name} ({n.type})" for n in dual_res.entities[:6])
                context_blocks.append(f"### Knowledge Graph Entities:\n{ent_line}")
            if dual_res.relations:
                rel_lines = [f"- {r.source} -[{r.predicate}]-> {r.target}" for r in dual_res.relations[:6]]
                context_blocks.append("### Key Relationships:\n" + "\n".join(rel_lines))
            if dual_res.communities:
                comm_lines = [f"- {c.name}: {c.summary[:180]}..." for c in dual_res.communities[:3] if c.summary]
                if comm_lines:
                    context_blocks.append("### High-Level Community Context:\n" + "\n".join(comm_lines))

        if context_snippets:
            context_blocks.append("### Note Excerpts:\n" + "\n\n".join(context_snippets))

        combined_context = "\n\n".join(context_blocks)

        # 7. Generate Answer via Ollama or Fallback
        prompt = LOCAL_ANSWER_PROMPT.format(
            context=combined_context or "No relevant notes or entities found.",
            query=query
        )
        answer = await self._generate_llm_answer(prompt, combined_context, query)

        # 8. Additive Retrieval Trace
        retrieval_trace: Dict[str, Any] = {
            "dual_level_active": self.dual_level_enabled,
            "keywords": dual_res.keywords.model_dump() if dual_res else {},
            "matched_entities": [n.name for n in dual_res.entities] if dual_res else [],
            "expanded_relations_count": len(dual_res.relations) if dual_res else 0,
            "top_communities": [c.name for c in dual_res.communities] if dual_res else [],
            "bridge_edges_count": len(dual_res.bridge_edges) if dual_res else 0,
            "channel_counts": {
                "dense": len(vector_hits),
                "lexical": len(fts_hits),
                "graph": len(graph_hits)
            }
        }

        return QueryResponse(
            query=query,
            mode_used="local",
            answer=answer,
            citations=citations,
            confidence=0.92,
            retrieval_trace=retrieval_trace
        )

    async def _generate_llm_answer(self, prompt: str, context: str, query: str) -> str:
        """Call LLM (hosted OpenAI-compatible or local Ollama) or fallback to grounded heuristic synthesis."""
        if self.llm_provider == "openai_compatible":
            from driftgraph.extract.api_client import call_chat_completion
            api_key = self.llm_api_key or config.llm.get_api_key()
            ans = await call_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=self.llm_model,
                base_url=self.llm_base_url,
                api_key=api_key,
                temperature=self.temperature,
                timeout=self.timeout
            )
            if ans:
                return ans

        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "options": {"temperature": self.temperature},
            "stream": False
        }
        base_url = str(self.llm_base_url).rstrip("/")
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=self.timeout) as client:
                resp = await client.post("/api/chat", json=payload)
                if resp.status_code == 200:
                    return resp.json().get("message", {}).get("content", "").strip()
        except Exception:
            pass

        # Grounded heuristic fallback
        if not context.strip():
            return f"No matching notes or entities found for query: '{query}'."

        return (
            f"Based on your notes and knowledge graph:\n\n"
            f"{context[:450]}...\n\n"
            f"(Note: Full LLM generation is available when Ollama is running)."
        )
