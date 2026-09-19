"""
Async OpenAI-compatible LLM client for entity/relation extraction and pipeline querying.
Supports any OpenAI-compatible endpoint (OpenAI, Groq, Together, DeepSeek, local Ollama /v1).
"""

import asyncio
import os
from typing import Optional, List, Dict, Any
import structlog
from openai import (
    AsyncOpenAI,
    APIStatusError,
    RateLimitError,
    InternalServerError,
    APIConnectionError,
    APITimeoutError
)

from driftgraph.extract.models import ExtractionConfig, ExtractionResult
from driftgraph.extract.prompts import ENTITY_RELATION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT_TEMPLATE
from driftgraph.extract.parser import parse_llm_extraction_response, fallback_heuristic_extraction
from driftgraph.ingest.models import Chunk

logger = structlog.get_logger(__name__)


class APIExtractionClient:
    """Async OpenAI-compatible extractor with exponential backoff retries and heuristic fallback."""

    def __init__(self, config: Optional[ExtractionConfig] = None):
        self.config = config or ExtractionConfig()
        api_key = self.config.api_key
        if not api_key:
            from driftgraph.config import config as app_config
            api_key = app_config.llm.get_api_key() or "ollama"

        # Ensure base_url has no trailing slash issues
        base_url = str(self.config.base_url).rstrip("/")

        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=float(self.config.timeout),
            max_retries=0,  # Explicit retry loop with backoff on 429 and 5xx
        )

    async def is_available(self) -> bool:
        """Check if LLM API server is reachable."""
        try:
            # Check model list with short timeout
            await asyncio.wait_for(self.client.models.list(), timeout=4.0)
            return True
        except Exception as e:
            logger.debug("api_client_availability_check_failed", error=str(e.__class__.__name__))
            return False

    async def extract_from_chunk(self, chunk: Chunk) -> ExtractionResult:
        """Extract entities and relations from a single text chunk with retry and fallback."""
        prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(text=chunk.text)
        messages = [
            {"role": "system", "content": ENTITY_RELATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    response_format={"type": "json_object"},
                )
                raw_content = response.choices[0].message.content or ""
                return parse_llm_extraction_response(raw_content, chunk.id)
            except (RateLimitError, InternalServerError, APIStatusError) as e:
                status_code = getattr(e, "status_code", None)
                if status_code == 429 or (status_code is not None and status_code >= 500):
                    backoff = min(8.0, 0.5 * (2 ** (attempt - 1)))
                    logger.warning(
                        "api_extraction_rate_limited_or_server_error",
                        status=status_code,
                        attempt=attempt,
                        backoff=backoff
                    )
                    if attempt < self.config.max_retries:
                        await asyncio.sleep(backoff)
                        continue
                logger.warning("api_extraction_http_error", status=status_code, attempt=attempt)
                break
            except (APIConnectionError, APITimeoutError) as e:
                logger.warning("api_extraction_connection_error", error=str(e.__class__.__name__), attempt=attempt)
                if attempt < self.config.max_retries:
                    await asyncio.sleep(0.5 * attempt)
                    continue
                break
            except Exception as e:
                # If provider does not support response_format json_object, retry once without it
                err_str = str(e).lower()
                if "response_format" in err_str and attempt == 1:
                    try:
                        response = await self.client.chat.completions.create(
                            model=self.config.model,
                            messages=messages,
                            temperature=self.config.temperature,
                        )
                        raw_content = response.choices[0].message.content or ""
                        return parse_llm_extraction_response(raw_content, chunk.id)
                    except Exception:
                        pass
                logger.warning("api_extraction_failed", error=str(e.__class__.__name__), attempt=attempt)
                break

        # If LLM API fails or retries are exhausted, use heuristic fallback
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
        """Close underlying AsyncOpenAI HTTP transport."""
        await self.client.close()


async def call_chat_completion(
    messages: List[Dict[str, str]],
    model: str,
    base_url: str,
    api_key: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
    timeout: float = 60.0,
    response_format: Optional[Dict[str, str]] = None,
    max_retries: int = 3,
) -> Optional[str]:
    """Reusable OpenAI-compatible chat completion caller with retry and backoff."""
    client = AsyncOpenAI(
        base_url=str(base_url).rstrip("/"),
        api_key=api_key or "ollama",
        timeout=timeout,
        max_retries=0,
    )
    try:
        for attempt in range(1, max_retries + 1):
            try:
                kwargs: Dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens
                if response_format:
                    kwargs["response_format"] = response_format

                response = await client.chat.completions.create(**kwargs)
                return (response.choices[0].message.content or "").strip()
            except (RateLimitError, InternalServerError, APIStatusError) as e:
                status_code = getattr(e, "status_code", None)
                if status_code == 429 or (status_code is not None and status_code >= 500):
                    backoff = min(8.0, 0.5 * (2 ** (attempt - 1)))
                    if attempt < max_retries:
                        await asyncio.sleep(backoff)
                        continue
                break
            except (APIConnectionError, APITimeoutError):
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * attempt)
                    continue
                break
            except Exception as e:
                if response_format and "response_format" in str(e).lower():
                    try:
                        kwargs.pop("response_format", None)
                        response = await client.chat.completions.create(**kwargs)
                        return (response.choices[0].message.content or "").strip()
                    except Exception:
                        pass
                break
        return None
    finally:
        await client.close()
