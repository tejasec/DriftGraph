"""
Hierarchical Map-Reduce summarization over Leiden community structure.
"""

from typing import List, Dict, Any, Optional
import asyncio
import json
import httpx
import structlog

from driftgraph.graph.models import Community, Node, Edge
from driftgraph.summarize.models import CommunitySummary, HierarchicalSummaryResult, SummaryConfig
from driftgraph.summarize.prompts import (
    COMMUNITY_MAP_SYSTEM_PROMPT,
    COMMUNITY_MAP_USER_PROMPT,
    GLOBAL_REDUCE_SYSTEM_PROMPT,
    GLOBAL_REDUCE_USER_PROMPT
)
from driftgraph.extract.parser import clean_json_text

logger = structlog.get_logger(__name__)


class CommunitySummarizer:
    """Performs hierarchical GraphRAG Map-Reduce summarization."""

    def __init__(self, config: Optional[SummaryConfig] = None):
        self.config = config or SummaryConfig()
        self.client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=float(self.config.timeout)
        )

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Call local Ollama model."""
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens
            },
            "stream": False,
            "format": "json"
        }
        try:
            resp = await self.client.post("/api/chat", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message", {}).get("content", "")
        except Exception:
            pass
        return None

    def _heuristic_community_summary(
        self,
        comm: Community,
        member_nodes: List[Node],
        internal_edges: List[Edge]
    ) -> CommunitySummary:
        """Heuristic summary generator when Ollama is offline."""
        node_names = [n.name for n in member_nodes]
        themes = node_names[:5]

        edge_descriptions = [
            f"{e.source} {e.predicate.lower()} {e.target}"
            for e in internal_edges[:5]
        ]

        summary_text = (
            f"Thematic cluster focusing on {', '.join(themes)}. "
            f"Key relationships include: {'; '.join(edge_descriptions) if edge_descriptions else 'interconnected conceptual relationships'}."
        )

        findings = [
            f"Cluster connects {len(member_nodes)} primary concepts: {', '.join(node_names[:4])}.",
            f"Primary activity involves {len(internal_edges)} directed relationships."
        ]

        return CommunitySummary(
            community_id=comm.id,
            level=comm.level,
            name=comm.name,
            summary=summary_text,
            findings=findings,
            themes=themes,
            node_count=len(member_nodes),
            confidence=0.85
        )

    async def summarize_community(
        self,
        comm: Community,
        nodes_lookup: Dict[str, Node],
        edges: List[Edge]
    ) -> CommunitySummary:
        """Map step: Generate a summary for a single community."""
        member_nodes = [nodes_lookup[nid] for nid in comm.node_ids if nid in nodes_lookup]
        member_node_ids = set(comm.node_ids)

        internal_edges = [
            e for e in edges
            if e.source in member_node_ids and e.target in member_node_ids
        ]

        entities_text = "\n".join([f"- {n.name} ({n.type}): {n.description or ''}" for n in member_nodes])
        relations_text = "\n".join([f"- {e.source} -> {e.predicate} -> {e.target}" for e in internal_edges])

        user_prompt = COMMUNITY_MAP_USER_PROMPT.format(
            name=comm.name,
            level=comm.level,
            entities_text=entities_text or "None",
            relations_text=relations_text or "None"
        )

        raw_resp = await self._call_llm(COMMUNITY_MAP_SYSTEM_PROMPT, user_prompt)
        if raw_resp:
            try:
                data = json.loads(clean_json_text(raw_resp))
                return CommunitySummary(
                    community_id=comm.id,
                    level=comm.level,
                    name=data.get("title", comm.name),
                    summary=data.get("summary", ""),
                    findings=data.get("findings", []),
                    themes=data.get("themes", []),
                    node_count=len(member_nodes),
                    confidence=0.95
                )
            except Exception:
                pass

        return self._heuristic_community_summary(comm, member_nodes, internal_edges)

    async def summarize_all(
        self,
        communities: List[Community],
        nodes: List[Node],
        edges: List[Edge]
    ) -> HierarchicalSummaryResult:
        """Execute full Map-Reduce pipeline over all communities."""
        nodes_lookup = {n.id: n for n in nodes}

        # 1. Map Step: summarize all communities concurrently
        tasks = [self.summarize_community(c, nodes_lookup, edges) for c in communities]
        summaries = await asyncio.gather(*tasks)

        # Update Community objects
        summary_map = {s.community_id: s for s in summaries}
        for c in communities:
            if c.id in summary_map:
                s = summary_map[c.id]
                c.summary = s.summary
                c.findings = s.findings
                c.themes = s.themes

        # 2. Reduce Step: Global Knowledge Base Summary
        global_text_chunks = [
            f"Community '{s.name}' (Level {s.level}):\n{s.summary}\nFindings: {'; '.join(s.findings)}"
            for s in summaries if s.level == 0
        ]
        combined_summaries_text = "\n\n".join(global_text_chunks)

        reduce_prompt = GLOBAL_REDUCE_USER_PROMPT.format(
            community_summaries_text=combined_summaries_text or "No communities available."
        )

        raw_reduce = await self._call_llm(GLOBAL_REDUCE_SYSTEM_PROMPT, reduce_prompt)
        global_overview = ""
        global_themes: List[str] = []

        if raw_reduce:
            try:
                data = json.loads(clean_json_text(raw_reduce))
                global_overview = data.get("global_overview", "")
                global_themes = data.get("overarching_themes", [])
            except Exception:
                pass

        if not global_overview:
            all_themes = []
            for s in summaries:
                all_themes.extend(s.themes)
            unique_themes = list(dict.fromkeys(all_themes))[:8]
            global_themes = unique_themes
            global_overview = (
                f"The knowledge graph contains {len(nodes)} interconnected entities partitioned into "
                f"{len(communities)} thematic communities. Dominant subjects include {', '.join(unique_themes)}."
            )

        return HierarchicalSummaryResult(
            global_summary=global_overview,
            key_themes=global_themes,
            community_summaries=summaries
        )

    async def close(self):
        await self.client.aclose()
