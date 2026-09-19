"""
LightRAG-Style Dual-Level Retrieval (Native Implementation).

Coordinates low-level entity subgraph expansion with high-level community summaries
and cross-community bridge edges to produce rich semantic context and graph-derived
provenance rankings for multi-list RRF.
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple, Set
import httpx
import numpy as np
import structlog
from pydantic import BaseModel, Field

from driftgraph.graph.models import Node, Edge, Community
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.embed.base import BaseEmbedder

logger = structlog.get_logger(__name__)

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "can", "did", "do", "does", "doing", "don",
    "down", "during", "each", "few", "for", "from", "further", "had", "has", "have",
    "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how",
    "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most",
    "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or",
    "other", "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she",
    "should", "so", "some", "such", "t", "than", "that", "the", "their", "theirs",
    "them", "themselves", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "we", "were", "what", "when",
    "where", "which", "while", "who", "whom", "why", "will", "with", "would"
}

KEYWORD_PROMPT = """You are an expert query analyzer in a knowledge graph retrieval engine.
Analyze the user's query and extract two distinct levels of keywords:
1. "low_level": Specific entity names, concrete concepts, technical terms, individual attributes, or specific relations mentioned or implied.
2. "high_level": Broad themes, overarching domains, abstract topics, general categories, or systemic questions.

Output ONLY valid JSON matching this schema:
{{
  "low_level": ["string"],
  "high_level": ["string"]
}}

Query: {query}
JSON:"""


class DualLevelKeywords(BaseModel):
    low_level: List[str] = Field(default_factory=list)
    high_level: List[str] = Field(default_factory=list)


class DualLevelResult(BaseModel):
    keywords: DualLevelKeywords
    entities: List[Node] = Field(default_factory=list)
    relations: List[Edge] = Field(default_factory=list)
    communities: List[Community] = Field(default_factory=list)
    bridge_edges: List[Edge] = Field(default_factory=list)
    ranked_chunks: List[Tuple[str, float]] = Field(default_factory=list)
    trace: Dict[str, Any] = Field(default_factory=dict)


class DualLevelRetriever:
    """Performs dual-level keyword extraction, entity 1-hop expansion, and community ranking."""

    def __init__(
        self,
        storage: SQLiteStorage,
        embedder: Optional[BaseEmbedder] = None,
        llm_model: str = "llama3.1:8b-instruct-q4_K_M",
        llm_base_url: str = "http://localhost:11434",
        timeout: float = 15.0,
        llm_provider: Optional[str] = None,
        llm_api_key: Optional[str] = None,
    ):
        from driftgraph.config import config
        self.storage = storage
        self.embedder = embedder
        self.llm_model = llm_model
        self.llm_base_url = llm_base_url
        self.llm_provider = llm_provider or getattr(config.llm, "provider", "ollama")
        self.llm_api_key = llm_api_key or config.llm.get_api_key()
        self.timeout = timeout

    async def extract_keywords(self, query: str) -> DualLevelKeywords:
        """Extract low-level and high-level keywords via LLM with heuristic fallback."""
        if self.llm_provider == "openai_compatible":
            from driftgraph.extract.api_client import call_chat_completion
            from driftgraph.config import config
            api_key = self.llm_api_key or config.llm.get_api_key()
            raw_content = await call_chat_completion(
                messages=[
                    {"role": "system", "content": "You extract keywords from queries. Respond with valid JSON."},
                    {"role": "user", "content": KEYWORD_PROMPT.format(query=query)}
                ],
                model=self.llm_model,
                base_url=self.llm_base_url,
                api_key=api_key,
                temperature=0.0,
                timeout=self.timeout,
                response_format={"type": "json_object"}
            )
            if raw_content:
                try:
                    parsed = json.loads(raw_content)
                    low = [str(k).strip() for k in parsed.get("low_level", []) if str(k).strip()]
                    high = [str(k).strip() for k in parsed.get("high_level", []) if str(k).strip()]
                    if low or high:
                        return DualLevelKeywords(low_level=low, high_level=high)
                except Exception:
                    pass

        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "user", "content": KEYWORD_PROMPT.format(query=query)}
            ],
            "options": {"temperature": 0.0},
            "stream": False,
            "format": "json"
        }
        base_url = str(self.llm_base_url).rstrip("/")
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=self.timeout) as client:
                resp = await client.post("/api/chat", json=payload)
                if resp.status_code == 200:
                    raw_content = resp.json().get("message", {}).get("content", "").strip()
                    parsed = json.loads(raw_content)
                    low = [str(k).strip() for k in parsed.get("low_level", []) if str(k).strip()]
                    high = [str(k).strip() for k in parsed.get("high_level", []) if str(k).strip()]
                    if low or high:
                        return DualLevelKeywords(low_level=low, high_level=high)
        except Exception as e:
            logger.debug("llm_keyword_extraction_fallback", reason=str(e))

        # Heuristic deterministic fallback
        return await self._fallback_keyword_extraction(query)

    async def _fallback_keyword_extraction(self, query: str) -> DualLevelKeywords:
        """Extract keywords using n-grams and SQLite entity lookup."""
        words = re.findall(r"\b[a-zA-Z0-9_-]+\b", query)
        content_words = [w for w in words if w.lower() not in STOP_WORDS]

        low_level: List[str] = []
        high_level: List[str] = []

        # Generate 1-grams, 2-grams, 3-grams
        candidates: Set[str] = set()
        n = len(content_words)
        for size in (3, 2, 1):
            for i in range(n - size + 1):
                candidates.add(" ".join(content_words[i:i + size]))

        # Search candidates against SQLite nodes
        for cand in candidates:
            matched_nodes = await self.storage.search_nodes(cand, limit=2)
            if matched_nodes:
                for node in matched_nodes:
                    if node.name not in low_level:
                        low_level.append(node.name)

        # Fallback high-level: query nouns or broad noun phrases
        if len(content_words) >= 2:
            high_level.append(" ".join(content_words[:3]))
        if query.strip() and query.strip() not in high_level:
            high_level.append(query.strip())

        if not low_level and content_words:
            low_level = content_words[:3]

        return DualLevelKeywords(low_level=low_level, high_level=high_level)

    async def retrieve(
        self,
        query: str,
        top_k_entities: int = 5,
        top_k_communities: int = 3
    ) -> DualLevelResult:
        """Execute dual-level graph retrieval."""
        keywords = await self.extract_keywords(query)
        trace: Dict[str, Any] = {
            "keywords": keywords.model_dump(),
            "matched_entities": [],
            "expanded_relations": 0,
            "communities": [],
            "bridge_edges_count": 0
        }

        # -------------------------------------------------------------
        # 1. LOW-LEVEL CHANNEL: Entity Subgraph & 1-Hop Expansion
        # -------------------------------------------------------------
        matched_nodes_map: Dict[str, Node] = {}
        for kw in keywords.low_level:
            found = await self.storage.search_nodes(kw, limit=top_k_entities)
            for n in found:
                matched_nodes_map[n.id] = n

        # If keyword search matched few nodes, try exact substring match from all nodes
        if len(matched_nodes_map) < top_k_entities:
            all_nodes = await self.storage.get_all_nodes()
            q_lower = query.lower()
            for n in all_nodes:
                if n.name.lower() in q_lower or any(kw.lower() in n.name.lower() for kw in keywords.low_level):
                    matched_nodes_map[n.id] = n
                if len(matched_nodes_map) >= top_k_entities:
                    break

        matched_nodes = list(matched_nodes_map.values())[:top_k_entities]
        trace["matched_entities"] = [n.name for n in matched_nodes]

        # 1-Hop Expansion
        node_ids = [n.id for n in matched_nodes]
        edges = await self.storage.get_edges_connected_to(node_ids)
        trace["expanded_relations"] = len(edges)

        # Chunk scoring from low-level channel
        chunk_scores: Dict[str, float] = {}
        for n in matched_nodes:
            # Degree centrality boost
            node_weight = 1.0 + (min(n.degree, 10) * 0.1)
            for cid in n.provenance_chunk_ids:
                chunk_scores[cid] = chunk_scores.get(cid, 0.0) + (1.5 * node_weight)

        for e in edges:
            edge_weight = float(e.weight) * float(e.confidence)
            for cid in e.provenance_chunk_ids:
                chunk_scores[cid] = chunk_scores.get(cid, 0.0) + (1.0 * edge_weight)

        # -------------------------------------------------------------
        # 2. HIGH-LEVEL CHANNEL: Community Ranking & Bridge Edges
        # -------------------------------------------------------------
        all_communities = await self.storage.get_communities()
        scored_communities: List[Tuple[float, Community]] = []

        q_vec = None
        if self.embedder is not None:
            try:
                q_vec = self.embedder.embed_query(query)
            except Exception:
                q_vec = None

        for comm in all_communities:
            score = 0.0
            comm_text = f"{comm.name} {comm.summary or ''} {' '.join(comm.themes)}".lower()

            # Keyword matches
            for hk in keywords.high_level:
                if hk.lower() in comm_text:
                    score += 2.0
            for lk in keywords.low_level:
                if lk.lower() in comm_text:
                    score += 0.5

            # Cosine similarity if embedding available
            if q_vec is not None and comm.summary and self.embedder is not None:
                try:
                    summary_vec = self.embedder.embed_texts([comm.summary])[0]
                    sim = float(np.dot(q_vec, summary_vec) / (
                        max(np.linalg.norm(q_vec) * np.linalg.norm(summary_vec), 1e-6)
                    ))
                    score += max(sim, 0.0) * 3.0
                except Exception:
                    pass

            scored_communities.append((score, comm))

        scored_communities.sort(key=lambda x: x[0], reverse=True)
        top_communities = [comm for score, comm in scored_communities[:top_k_communities] if score > 0]
        if not top_communities and all_communities:
            top_communities = all_communities[:top_k_communities]

        trace["communities"] = [c.name for c in top_communities]

        # Community Member Node chunks
        for comm in top_communities:
            member_nodes = await self.storage.get_nodes_by_ids(comm.node_ids[:10])
            for m in member_nodes:
                for cid in m.provenance_chunk_ids:
                    chunk_scores[cid] = chunk_scores.get(cid, 0.0) + 0.8

        # Cross-Community Bridge Edges
        # Find edges connecting nodes that belong to different communities
        all_edges = await self.storage.get_all_edges()
        node_comm_map: Dict[str, int] = {n.id: n.community_id for n in await self.storage.get_all_nodes() if n.community_id is not None}
        bridge_edges: List[Edge] = []
        for e in all_edges:
            c1 = node_comm_map.get(e.source)
            c2 = node_comm_map.get(e.target)
            if c1 is not None and c2 is not None and c1 != c2:
                bridge_edges.append(e)
                for cid in e.provenance_chunk_ids:
                    chunk_scores[cid] = chunk_scores.get(cid, 0.0) + 1.2

        trace["bridge_edges_count"] = len(bridge_edges)

        # -------------------------------------------------------------
        # 3. Output Assembly & Ranking
        # -------------------------------------------------------------
        sorted_chunks = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)

        return DualLevelResult(
            keywords=keywords,
            entities=matched_nodes,
            relations=edges[:15],
            communities=top_communities,
            bridge_edges=bridge_edges[:10],
            ranked_chunks=sorted_chunks,
            trace=trace
        )
