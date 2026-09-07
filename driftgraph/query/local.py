"""
Local Search Engine: Hybrid Vector Similarity (FAISS) + Full-Text Search (SQLite FTS5) + LLM synthesis.
"""

from typing import List, Dict, Any, Optional
import httpx
import numpy as np
import structlog

from driftgraph.embed.base import BaseEmbedder
from driftgraph.graph.vector_store import VectorIndex
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.query.models import Citation, QueryResponse

logger = structlog.get_logger(__name__)

LOCAL_ANSWER_PROMPT = """You are DriftGraph, an intelligent assistant answering questions based strictly on the user's personal knowledge base.

CONTEXT RETRIEVED FROM NOTES:
{context}

QUESTION:
{query}

INSTRUCTIONS:
1. Answer the question accurately using ONLY the retrieved context.
2. If the context does not contain sufficient information, state what is known and mention what is missing.
3. Be clear, concise, and direct.

ANSWER:"""


class LocalSearchEngine:
    """Performs hybrid retrieval (vector + keyword) and generates targeted answers."""

    def __init__(
        self,
        embedder: BaseEmbedder,
        vector_index: VectorIndex,
        storage: SQLiteStorage,
        llm_model: str = "llama3.1:8b-instruct-q4_K_M",
        llm_base_url: str = "http://localhost:11434"
    ):
        self.embedder = embedder
        self.vector_index = vector_index
        self.storage = storage
        self.llm_model = llm_model
        self.llm_base_url = llm_base_url

    async def search(self, query: str, top_k: int = 5, hybrid_alpha: float = 0.5) -> QueryResponse:
        """Execute hybrid search and answer generation."""
        citations: List[Citation] = []
        context_snippets: List[str] = []

        # 1. Vector Search
        q_emb = self.embedder.embed_query(query)
        vector_hits = self.vector_index.search(q_emb, top_k=top_k)

        # 2. SQLite FTS5 Keyword Search
        fts_hits = await self.storage.search_chunks_fts(query, limit=top_k)

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[str, float] = {}
        content_map: Dict[str, Dict[str, Any]] = {}

        # Vector scores (weight = 1 - hybrid_alpha)
        for rank, (chunk_id, sim_score) in enumerate(vector_hits):
            score = (1.0 - hybrid_alpha) * (1.0 / (60 + rank + 1))
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + score
            content_map[chunk_id] = {"id": chunk_id, "score": sim_score}

        # FTS scores (weight = hybrid_alpha)
        for rank, fts_item in enumerate(fts_hits):
            chunk_id = fts_item["chunk_id"]
            score = hybrid_alpha * (1.0 / (60 + rank + 1))
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + score
            if chunk_id not in content_map:
                content_map[chunk_id] = {"id": chunk_id, "score": 0.8}
            content_map[chunk_id]["text"] = fts_item.get("text", "")
            content_map[chunk_id]["title"] = fts_item.get("title", "")

        # Sort combined
        sorted_chunks = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # Fetch chunk details from SQLite if not present in content_map
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
                context_snippets.append(f"[{title or chunk_id}]: {text}")

            citations.append(Citation(
                source_type="chunk",
                id=chunk_id,
                title=title,
                text_snippet=snippet,
                score=float(rrf_score)
            ))

        combined_context = "\n\n".join(context_snippets)

        # 4. Generate Answer via Ollama
        prompt = LOCAL_ANSWER_PROMPT.format(context=combined_context or "No relevant notes found.", query=query)
        answer = await self._generate_llm_answer(prompt, combined_context, query)

        return QueryResponse(
            query=query,
            mode_used="local",
            answer=answer,
            citations=citations,
            confidence=0.92
        )

    async def _generate_llm_answer(self, prompt: str, context: str, query: str) -> str:
        """Call Ollama or fallback to grounded heuristic synthesis."""
        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "options": {"temperature": 0.1},
            "stream": False
        }
        try:
            async with httpx.AsyncClient(base_url=self.llm_base_url, timeout=30.0) as client:
                resp = await client.post("/api/chat", json=payload)
                if resp.status_code == 200:
                    return resp.json().get("message", {}).get("content", "").strip()
        except Exception:
            pass

        # Grounded heuristic fallback
        if not context.strip():
            return f"No matching notes or entities found for query: '{query}'."

        return (
            f"Based on your notes:\n\n"
            f"{context[:400]}...\n\n"
            f"(Note: Full LLM generation is available when Ollama is running)."
        )
