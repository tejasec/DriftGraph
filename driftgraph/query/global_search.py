"""
Global Search Engine: GraphRAG Map-Reduce query answering over hierarchical community summaries.
"""

from typing import List, Optional
import httpx
import structlog

from driftgraph.graph.storage import SQLiteStorage
from driftgraph.query.models import Citation, QueryResponse

logger = structlog.get_logger(__name__)

GLOBAL_QUERY_MAP_PROMPT = """You are answering a broad thematic question using a community summary from the user's knowledge graph.

COMMUNITY SUMMARY:
Title: {name}
Summary: {summary}
Findings: {findings}

QUESTION:
{query}

Rate how relevant this community is to the question (0-100) and provide a concise intermediate answer.

OUTPUT JSON FORMAT:
{{
  "relevance_score": 85,
  "intermediate_answer": "Key points addressing the query from this community's perspective"
}}
"""

GLOBAL_QUERY_REDUCE_PROMPT = """You are DriftGraph, synthesizing an overarching comprehensive answer to a global question across the user's entire knowledge base.

QUESTION:
{query}

INTERMEDIATE COMMUNITY INSIGHTS:
{intermediate_insights}

INSTRUCTIONS:
1. Synthesize a structured, cohesive answer that captures all main themes and connections.
2. Group the answer logically with key themes or headings.
3. Highlight cross-community connections.

GLOBAL ANSWER:"""


class GlobalSearchEngine:
    """Executes GraphRAG global queries across community summaries."""

    def __init__(
        self,
        storage: SQLiteStorage,
        llm_model: str = "llama3.1:8b-instruct-q4_K_M",
        llm_base_url: str = "http://localhost:11434",
        temperature: float = 0.2,
        timeout: float = 45.0,
        max_tokens: Optional[int] = None,
        llm_provider: Optional[str] = None,
        llm_api_key: Optional[str] = None,
    ):
        from driftgraph.config import config
        self.storage = storage
        self.llm_model = llm_model
        self.llm_base_url = llm_base_url
        self.llm_provider = llm_provider or getattr(config.llm, "provider", "ollama")
        self.llm_api_key = llm_api_key or config.llm.get_api_key()
        self.temperature = temperature
        self.timeout = timeout
        self.max_tokens = max_tokens

    async def search(self, query: str, community_level: int = 0) -> QueryResponse:
        """Execute Global GraphRAG search."""
        communities = await self.storage.get_communities(level=community_level)
        if not communities:
            # Fallback to any level
            communities = await self.storage.get_communities()

        citations: List[Citation] = []
        intermediate_insights: List[str] = []

        for comm in communities:
            if not comm.summary:
                continue

            findings_str = "; ".join(comm.findings) if comm.findings else "None"
            intermediate_insights.append(
                f"### {comm.name}\n- Summary: {comm.summary}\n- Key Findings: {findings_str}"
            )

            citations.append(Citation(
                source_type="community",
                id=f"community_{comm.id}",
                title=comm.name,
                text_snippet=comm.summary[:250],
                score=comm.confidence
            ))

        combined_insights = "\n\n".join(intermediate_insights)

        # Reduce step to produce final global response
        reduce_prompt = GLOBAL_QUERY_REDUCE_PROMPT.format(
            query=query,
            intermediate_insights=combined_insights or "No community summaries found."
        )

        answer = await self._call_llm_reduce(reduce_prompt, intermediate_insights, query)

        retrieval_trace = {
            "mode": "global",
            "communities_evaluated": len(communities),
            "citations_count": len(citations)
        }

        return QueryResponse(
            query=query,
            mode_used="global",
            answer=answer,
            citations=citations,
            confidence=0.95,
            retrieval_trace=retrieval_trace
        )

    async def _call_llm_reduce(self, prompt: str, intermediate_insights: List[str], query: str) -> str:
        """Synthesize global answer using LLM (OpenAI-compatible or local Ollama) or structured fallback."""
        if self.llm_provider == "openai_compatible":
            from driftgraph.extract.api_client import call_chat_completion
            from driftgraph.config import config
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
            "messages": [{"role": "user", "content": prompt}],
            "options": {"temperature": self.temperature},
            "stream": False
        }
        if self.max_tokens and self.max_tokens > 0:
            payload["options"]["num_predict"] = self.max_tokens
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

        if not intermediate_insights:
            return f"No community summaries found to answer the global query: '{query}'."

        # Fallback structured synthesis
        synthesis = [
            f"### Global Knowledge Graph Overview for: '{query}'\n",
            "Across the detected thematic communities in your notes:\n"
        ]
        for insight in intermediate_insights[:4]:
            synthesis.append(insight)

        return "\n\n".join(synthesis)
