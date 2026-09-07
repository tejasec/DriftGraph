"""
Embedding configuration models and data structures.
"""

from typing import List, Optional
import numpy as np
from pydantic import BaseModel, Field


class EmbeddingConfig(BaseModel):
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str = "cpu"
    batch_size: int = 32
    normalize: bool = True
    dimension: int = 384


class EmbeddingResult(BaseModel):
    chunk_id: str
    embedding: List[float]
    dimension: int
