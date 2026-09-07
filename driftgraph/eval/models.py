"""
Data models for Benchmarking, Profiling, and RAGAS evaluation.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class StageMetrics(BaseModel):
    stage_name: str
    latency_ms: float
    peak_rss_mb: float
    cpu_percent: float
    items_processed: int = 0
    extra: Dict[str, Any] = Field(default_factory=dict)


class BenchmarkReport(BaseModel):
    run_id: str
    timestamp: str
    stages: List[StageMetrics] = Field(default_factory=list)
    total_latency_ms: float = 0.0
    max_rss_mb: float = 0.0


class EvaluationScores(BaseModel):
    context_precision: float
    faithfulness: float
    answer_relevance: float
    overall_score: float
