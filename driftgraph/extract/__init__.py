"""
Entity and relation extraction module.
"""

from driftgraph.extract.models import Entity, Relation, ExtractionResult, ExtractionConfig
from driftgraph.extract.ollama_client import OllamaExtractionClient
from driftgraph.extract.parser import parse_llm_extraction_response, fallback_heuristic_extraction

__all__ = [
    "Entity",
    "Relation",
    "ExtractionResult",
    "ExtractionConfig",
    "OllamaExtractionClient",
    "parse_llm_extraction_response",
    "fallback_heuristic_extraction",
]
