"""
Entity and relation extraction module.
"""

from typing import Optional

from driftgraph.extract.models import Entity, Relation, ExtractionResult, ExtractionConfig
from driftgraph.extract.ollama_client import OllamaExtractionClient
from driftgraph.extract.api_client import APIExtractionClient, call_chat_completion
from driftgraph.extract.parser import parse_llm_extraction_response, fallback_heuristic_extraction


def get_extraction_client(config_override: Optional[ExtractionConfig] = None):
    """Factory creating appropriate extraction client based on configuration."""
    from driftgraph.config import config
    if config.llm.provider == "openai_compatible":
        cfg = config_override or ExtractionConfig(
            model=config.llm.model,
            base_url=config.llm.base_url,
            temperature=config.llm.temperature,
            timeout=config.llm.timeout,
            api_key=config.llm.get_api_key(),
        )
        return APIExtractionClient(cfg)
    else:
        cfg = config_override or ExtractionConfig(
            model=config.llm.model,
            base_url=config.llm.base_url,
            temperature=config.llm.temperature,
            timeout=config.llm.timeout,
        )
        return OllamaExtractionClient(cfg)


__all__ = [
    "Entity",
    "Relation",
    "ExtractionResult",
    "ExtractionConfig",
    "OllamaExtractionClient",
    "APIExtractionClient",
    "call_chat_completion",
    "get_extraction_client",
    "parse_llm_extraction_response",
    "fallback_heuristic_extraction",
]
