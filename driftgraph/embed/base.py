"""
Abstract Base Class for Embedders in DriftGraph.
"""

from abc import ABC, abstractmethod
from typing import List, Union
import numpy as np


class BaseEmbedder(ABC):
    """Abstract interface for all embedding models (SBERT, Word2Vec baseline, etc.)"""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed a list of text strings into an [N, D] numpy array."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> np.ndarray:
        """Embed a single query string into a [D] numpy array."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimension."""
        pass
