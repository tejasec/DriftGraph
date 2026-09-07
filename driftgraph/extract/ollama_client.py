"""
Async Ollama client with retry logic, timeouts, and fallback for entity/relation extraction.
"""

from typing import Optional, List
import asyncio
import httpx
import structlog

from driftgraph.extract.models import ExtractionConfig, ExtractionResult
from driftgraph.extract.prompts import ENTITY_RELATION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT_TEMPLATE
from driftgraph.extract.parser import parse_llm_extraction_response, fallback_heuristic_extraction
from driftgraph.ingest.models import Chunk

logger = structlog.get_logger(__name__)


class OllamaExtractionClient:
    """Ollama-based extractor with graceful fallbacks and batch processing."""

    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or ExtractionConfig()
        self.client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=float(self.config.timeout)
        )

    async def is_available(self) -> bool:
        """Check if Ollama server is active and reachable."""
        try:
            resp = await self.client.get("/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    async def extract_from_chunk(self, chunk: Chunk) -> ExtractionResult:
        """Extract entities and relations from a single text chunk."""
        prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(text=chunk.text)

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": ENTITY_RELATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "options": {
                "temperature": self.config.temperature,
            },
            "stream": False,
            "format": "json"
        }

        for attempt in range(1, self.config.max_retries + 1):
            try:
                resp = await self.client.post("/api/chat", json=payload)
                if resp.status_code == 200:
                    result_data = resp.json()
                    raw_content = result_data.get("message", {}).get("content", "")
                    return parse_llm_extraction_response(raw_content, chunk.id)
                else:
                    logger.warning("ollama_http_error", status=resp.status_code, attempt=attempt)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt == 1:
                    logger.warning("ollama_server_offline_using_heuristics", error=str(e))
                break
            except Exception as e:
                logger.warning("ollama_extraction_error", error=str(e), attempt=attempt)
                await asyncio.sleep(0.5 * attempt)

        # If Ollama is unavailable or failed, use fast heuristic extraction
        return fallback_heuristic_extraction(chunk.text, chunk.id)

    async def extract_batch(self, chunks: List[Chunk], max_concurrency: int = 4) -> List[ExtractionResult]:
        """Extract entities and relations concurrently from multiple chunks."""
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _bounded_extract(c: Chunk) -> ExtractionResult:
            async with semaphore:
                return await self.extract_from_chunk(c)

        tasks = [_bounded_extract(c) for c in chunks]
        return await asyncio.gather(*tasks)

    async def close(self):
        await self.client.aclose()
