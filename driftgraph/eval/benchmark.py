"""
System performance and resource profiling using psutil and high-resolution timers.
"""

import time
import os
import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import psutil
import structlog

from driftgraph.eval.models import StageMetrics, BenchmarkReport

logger = structlog.get_logger(__name__)


class BenchmarkRunner:
    """Tracks latency, peak memory (RSS), and CPU utilization across pipeline stages."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.metrics: List[StageMetrics] = []

    @contextmanager
    def measure(self, stage_name: str, items_count: int = 0):
        """Context manager to measure latency and memory during a code block."""
        # Initial stats
        self.process.cpu_percent(interval=None)
        mem_before = self.process.memory_info().rss / (1024 * 1024)
        start_time = time.perf_counter()

        try:
            yield
        finally:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000.0
            mem_after = self.process.memory_info().rss / (1024 * 1024)
            cpu_usage = self.process.cpu_percent(interval=None)

            stage_metric = StageMetrics(
                stage_name=stage_name,
                latency_ms=round(latency_ms, 2),
                peak_rss_mb=round(max(mem_before, mem_after), 2),
                cpu_percent=round(cpu_usage, 2),
                items_processed=items_count
            )
            self.metrics.append(stage_metric)
            logger.info(
                "stage_profiled",
                stage=stage_name,
                latency_ms=stage_metric.latency_ms,
                rss_mb=stage_metric.peak_rss_mb,
                cpu_pct=stage_metric.cpu_percent
            )

    def generate_report(self) -> BenchmarkReport:
        """Summarize all recorded stages."""
        total_lat = sum(m.latency_ms for m in self.metrics)
        max_rss = max((m.peak_rss_mb for m in self.metrics), default=0.0)

        return BenchmarkReport(
            run_id=f"run_{int(time.time())}",
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            stages=self.metrics,
            total_latency_ms=round(total_lat, 2),
            max_rss_mb=round(max_rss, 2)
        )
