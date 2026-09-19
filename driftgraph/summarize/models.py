"""
Data models for Community Summarization and Hierarchical synthesis.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CommunitySummary(BaseModel):
    community_id: int
    level: int
    name: str
    summary: str
    findings: List[str] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)
    node_count: int = 0
    confidence: float = 1.0


class HierarchicalSummaryResult(BaseModel):
    global_summary: str
    key_themes: List[str] = Field(default_factory=list)
    community_summaries: List[CommunitySummary] = Field(default_factory=list)


class SummaryConfig(BaseModel):
    provider: str = "ollama"
    model: str = "llama3.1:8b-instruct-q4_K_M"
    base_url: str = "http://localhost:11434"
    api_key: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 1024
    timeout: int = 120
