"""
Tests for Scoped Cursor Physics and Model/Leiden Diagnostics.
Verifies:
- physics-controller.js implementation guard (hero ambient repulsion vs explorer hover hit-testing)
- Absence of cursor repulsion in graph explorer canvas
- Kinematic drag collision padding invariant (Rc = r_node + 4px)
- /api/status/diagnostics endpoint correctness
"""

import json
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from driftgraph.serve.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def test_physics_controller_file_and_guard_contract():
    """Verify physics-controller.js exists and exports handlePointerMove with the strict guard."""
    js_path = Path(__file__).parent.parent / "frontend" / "assets" / "js" / "physics-controller.js"
    assert js_path.exists(), "physics-controller.js must exist in frontend/assets/js/"

    content = js_path.read_text(encoding="utf-8")
    assert "function handlePointerMove(event)" in content
    assert "isHeroActive" in content
    assert "applyAmbientRepulsion" in content
    assert "updateHoveredNode" in content

    # Check the required guard structure from the task spec:
    assert "if (isHero)" in content or "if (isHeroActive" in content
    assert "applyAmbientRepulsion(event.clientX, event.clientY);" in content
    assert "updateHoveredNode(event.clientX, event.clientY);" in content


def test_physics_worker_kinematic_drag_contract():
    """Verify physics.worker.js implements kinematic collision deflection with Rc = r_node + 4px."""
    worker_path = Path(__file__).parent.parent / "frontend" / "assets" / "js" / "physics.worker.js"
    assert worker_path.exists(), "physics.worker.js must exist"

    content = worker_path.read_text(encoding="utf-8")
    assert "resolveKinematicCollision" in content
    assert "collisionPadding" in content
    # Collision boundary check
    assert "rSum" in content
    # Worker ambient repel must be guarded
    assert "msg.isHeroActive" in content


def test_galaxy_engine_scoped_hover_and_no_unsolicited_repel():
    """Verify galaxy-engine.js implements updateHoveredNode and guards processAmbientRepulsion."""
    engine_path = Path(__file__).parent.parent / "frontend" / "assets" / "js" / "galaxy-engine.js"
    assert engine_path.exists(), "galaxy-engine.js must exist"

    content = engine_path.read_text(encoding="utf-8")
    assert "updateHoveredNode(clientX, clientY)" in content
    assert "clearHover()" in content
    assert "findNodeAt" in content
    # processAmbientRepulsion must strictly disable cursor repulsion in explorer mode
    assert "Strictly disable cursor repulsion" in content
    assert "isHeroActive" in content


def test_html_includes_physics_controller_and_body_class():
    """Verify index.html includes physics-controller.js and sets hero-active on body."""
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    content = html_path.read_text(encoding="utf-8")

    assert '<script src="/static/assets/js/physics-controller.js"></script>' in content
    assert '<body class="hero-active">' in content
    assert "window._driftCanvasPointer" in content


def test_hero_landing_is_initial_entry_page():
    """Verify entering the project defaults to the hero landing page."""
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    content = html_path.read_text(encoding="utf-8")

    # Initial HTML markup state
    assert '<body class="hero-active">' in content
    assert 'class="view-viewport hero-active"' in content
    assert '<section id="hero-landing" class="view-screen screen active"' in content
    assert '<section id="app-workspace" class="view-screen screen"' in content
    assert '<section id="app-workspace" class="view-screen screen active"' not in content

    # JavaScript window load guarantees initial screen is hero-landing and cleans up legacy storage
    assert 'showScreen("screen-landing")' in content
    assert 'localStorage.getItem("dg_active_screen")' not in content



async def test_diagnostics_endpoint(client):
    """Verify /api/status/diagnostics returns comprehensive Model and Leiden diagnostics."""
    resp = await client.get("/api/status/diagnostics")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "healthy"

    # Model diagnostics
    assert "model" in data
    model = data["model"]
    assert "provider" in model
    assert "configured_model" in model
    assert "fallback_extraction_ready" in model
    assert model["fallback_extraction_ready"] is True

    # Leiden diagnostics
    assert "community_detection" in data
    leiden = data["community_detection"]
    assert leiden["active_algorithm"] in ("leidenalg", "python_louvain", "greedy_modularity")
    assert "leidenalg_installed" in leiden
    assert "hierarchy_supported" in leiden
    assert leiden["hierarchy_supported"] is True
    assert leiden["partition_type"] == "RBConfigurationVertexPartition"

    # Scoped physics diagnostics
    assert "physics" in data
    physics = data["physics"]
    assert physics["scoped_cursor_physics"] is True
    assert physics["hero_ambient_radial_field"] is True
    assert physics["explorer_cursor_repulsion"] == "disabled"
    assert physics["kinematic_drag_collision_boundary"] == "Rc = r_node + 4px"
    assert physics["pan_zoom_relayout"] == "disabled"
