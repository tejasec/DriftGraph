"""
Query Intent Router for selecting between Global (GraphRAG) and Local (Hybrid Vector+FTS) Search.
"""

from typing import Literal
import re
import structlog

logger = structlog.get_logger(__name__)

GLOBAL_KEYWORDS = {
    "theme", "themes", "overview", "summarize", "summary", "main topics",
    "overall", "entire", "all notes", "high level", "big picture", "broad",
    "structure", "communities", "clusters", "landscape", "what do i know about everything"
}


class QueryRouter:
    """Classifies user queries into 'global' (community GraphRAG) or 'local' (entity/chunk search)."""

    def route(self, query: str, explicit_mode: str = "auto") -> Literal["global", "local"]:
        if explicit_mode in ("global", "local"):
            return explicit_mode

        q_lower = query.lower()

        # Check for global keywords or broad question patterns
        for kw in GLOBAL_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", q_lower):
                logger.info("routed_to_global_query", reason=f"matched keyword: {kw}")
                return "global"

        # Questions asking "What are the main ...", "List all ...", "Give an overview"
        if re.search(r"\b(main|major|primary|key)\s+(themes|points|ideas|concepts|topics)\b", q_lower):
            return "global"

        # Default to local search for specific queries
        return "local"
