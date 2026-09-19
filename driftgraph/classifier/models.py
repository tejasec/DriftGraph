"""driftgraph/classifier/models.py

Data models for offline rule-based document classification, text statistics, and auto-tagging.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CategoryScore(BaseModel):
    category: str
    percentage: float  # 0.0 to 100.0
    raw_score: float
    matched_keywords: List[str] = Field(default_factory=list)
    progress_bar: str = ""


class ContextualEntity(BaseModel):
    entity: str
    category: str
    origin_url: Optional[str] = None
    search_url: Optional[str] = None
    connected_concepts: List[str] = Field(default_factory=list)


class ClassificationResult(BaseModel):
    filename: str
    word_count: int
    char_count: int
    line_count: int
    top_category: str
    categories: List[CategoryScore]
    ascii_box: str
    auto_tags: List[str] = Field(default_factory=list)
    sentiment: str = "neutral"  # positive, neutral, negative
    sentiment_score: float = 0.0  # -1.0 to 1.0
    priority: str = "medium"  # urgent, high, medium, low
    contextual_entities: List[ContextualEntity] = Field(default_factory=list)
