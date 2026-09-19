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
    """Check whether the configured LLM server (Ollama or OpenAI-compatible) is reachable."""
    if config.llm.provider == "openai_compatible":
        from driftgraph.extract.api_client import APIExtractionClient
        from driftgraph.extract.models import ExtractionConfig
        client = APIExtractionClient(ExtractionConfig(
            model=config.llm.model,
            base_url=config.llm.base_url,
            api_key=config.llm.get_api_key(),
            timeout=5
        ))
        is_up = await client.is_available()
        await client.close()
        return {
            "online": is_up,
            "provider": config.llm.provider,
            "configured_model": config.llm.model,
            "configured_model_present": is_up,
        }

    base_url = str(config.llm.base_url).rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=3.0) as client:
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
        return {"online": False, "error": str(e.__class__.__name__)}


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


@router.get("/diagnostics")
async def get_diagnostics() -> Dict[str, Any]:
    """
    Detailed runtime diagnostics for Model (Ollama / OpenAI API) and Leiden community detection.
    Surfaces live algorithm selection, C-extension readiness, and scoped physics parameters.
    """
    # 1. Model / LLM Diagnostics
    llm_info = await _ollama_status()
    model_diag = {
        "provider": config.llm.provider,
        "configured_model": config.llm.model,
        "base_url": str(config.llm.base_url),
        "online": llm_info.get("online", False),
        "details": llm_info,
        "fallback_extraction_ready": True,
        "mode": "api_hosted" if config.llm.provider == "openai_compatible" else "local_ollama",
    }

    # 2. Leiden Community Detection Diagnostics
    has_leidenalg = False
    leiden_version = None
    try:
        import leidenalg
        has_leidenalg = True
        leiden_version = getattr(leidenalg, "__version__", "unknown")
    except Exception:
        pass

    has_igraph = False
    igraph_version = None
    try:
        import igraph
        has_igraph = True
        igraph_version = getattr(igraph, "__version__", "unknown")
    except Exception:
        pass

    has_louvain = False
    try:
        import community  # python-louvain
        has_louvain = True
    except Exception:
        pass

    active_algo = "leidenalg" if (has_leidenalg and has_igraph) else ("python_louvain" if has_louvain else "greedy_modularity")

    leiden_diag = {
        "active_algorithm": active_algo,
        "leidenalg_installed": has_leidenalg,
        "leidenalg_version": leiden_version,
        "igraph_installed": has_igraph,
        "igraph_version": igraph_version,
        "louvain_fallback_installed": has_louvain,
        "networkx_modularity_fallback_available": True,
        "hierarchy_supported": True,
        "default_resolution": 1.0,
        "partition_type": "RBConfigurationVertexPartition",
        "status": "optimal" if active_algo == "leidenalg" else "degraded",
    }

    return {
        "status": "healthy",
        "model": model_diag,
        "community_detection": leiden_diag,
        "physics": {
            "scoped_cursor_physics": True,
            "hero_ambient_radial_field": True,
            "explorer_cursor_repulsion": "disabled",
            "kinematic_drag_collision_boundary": "Rc = r_node + 4px",
            "pan_zoom_relayout": "disabled",
        },
    }
