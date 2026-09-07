"""
Health / status route: surfaces live pipeline health so silent fallbacks are visible.
"""

from typing import Dict, Any
import httpx
import structlog
from fastapi import APIRouter

from driftgraph.config import config

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/status", tags=["Status"])


async def _ollama_status() -> Dict[str, Any]:
    """Check whether the local Ollama server is reachable."""
    try:
        async with httpx.AsyncClient(base_url=config.llm.base_url, timeout=3.0) as client:
            resp = await client.get("/api/tags")
            if resp.status_code == 200:
                tags = [m["name"] for m in resp.json().get("models", [])]
                return {
                    "online": True,
                    "configured_model": config.llm.model,
                    "installed_models": tags,
                    "configured_model_present": config.llm.model in tags,
                }
            return {"online": False, "status_code": resp.status_code}
    except Exception as e:
        return {"online": False, "error": str(e)}


@router.get("")
async def get_status() -> Dict[str, Any]:
    """Report live status of Ollama, community detection, and eval."""
    ollama = await _ollama_status()

    community_method = "leidenalg"
    try:
        import leidenalg  # noqa: F401
    except Exception:
        community_method = "greedy_modularity (leidenalg not installed)"

    ragas_available = False
    try:
        import ragas  # noqa: F401
        ragas_available = True
    except Exception:
        pass

    return {
        "app": config.app.name,
        "version": config.app.version,
        "debug": config.app.debug,
        "ollama": ollama,
        "llm": {
            "provider": config.llm.provider,
            "model": config.llm.model,
            "base_url": config.llm.base_url,
        },
        "community_detection": {"method": community_method},
        "embedding": {
            "model": config.embedding.model,
            "device": config.embedding.device,
            "dimension": config.embedding.dimension,
        },
        "eval": {"ragas_installed": ragas_available},
        "server": {"host": config.server.host, "port": config.server.port},
    }
