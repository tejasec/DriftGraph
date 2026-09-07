"""
Embedding module for dense semantic representations.
"""

from driftgraph.embed.models import EmbeddingConfig, EmbeddingResult
from driftgraph.embed.base import BaseEmbedder
from driftgraph.embed.sbert import SBERTEmbedder
from driftgraph.embed.baseline import Word2VecEmbedder

__all__ = [
    "EmbeddingConfig",
    "EmbeddingResult",
    "BaseEmbedder",
    "SBERTEmbedder",
    "Word2VecEmbedder",
]
