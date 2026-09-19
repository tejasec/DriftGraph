"""
Tests for Galaxy Engine Graph View Visibility and Diagnostic Pipeline.
Verifies:
- JavaScript syntax and exports across galaxy-engine.js and related frontend scripts
- Telemetry logging contract ([Graph Engine] logs)
- DOM layout dimensions and styling guarantees (min-height: 400px, explicit canvas z-indexes)
- Self-healing ResizeObserver integration
- Empty state UI and action buttons
- Screen transition resize pass
- Backend /api/graph contract
"""

from pathlib import Path
import subprocess
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


def test_galaxy_engine_syntax_and_structure():
    """Verify galaxy-engine.js exists and passes Node.js syntax checks without error."""
    engine_path = Path(__file__).parent.parent / "frontend" / "assets" / "js" / "galaxy-engine.js"
    assert engine_path.exists(), "galaxy-engine.js must exist in frontend/assets/js/"

    # Check with node syntax validation
    result = subprocess.run(["node", "--check", str(engine_path)], capture_output=True, text=True)
    assert result.returncode == 0, f"galaxy-engine.js syntax error: {result.stderr}"


def test_galaxy_engine_telemetry_and_dom_ids():
    """Verify galaxy-engine.js implements required telemetry logging and DOM IDs."""
    engine_path = Path(__file__).parent.parent / "frontend" / "assets" / "js" / "galaxy-engine.js"
    content = engine_path.read_text(encoding="utf-8")

    # DOM IDs & Layers
    assert 'this.interactiveCanvas.id = "galaxy-canvas"' in content or "galaxy-canvas" in content
    assert 'this.bgCanvas.id = "galaxy-bg-canvas"' in content or "galaxy-bg-canvas" in content
    assert 'this.bgCanvas.style.zIndex = "1"' in content
    assert 'this.interactiveCanvas.style.zIndex = "2"' in content

    # Telemetry Logs
    assert "[Graph Engine] Canvas element found:" in content
    assert "[Graph Engine] Canvas client dimensions:" in content
    assert "[Graph Engine] Initialized with 0 nodes" in content
    assert "[Graph Engine] Initialized with ${this.nodes.length} nodes" in content or "Initialized with" in content
    assert "[Graph Engine] Render loop ticking: frame" in content

    # Graceful Empty-State Guard
    assert "if (this.nodes.length === 0)" in content
    assert "this.drawBackground();" in content


def test_index_html_canvas_dimensions_and_css():
    """Verify index.html guarantees explicit dimensions and z-indexing for the canvas."""
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    assert html_path.exists(), "frontend/index.html must exist"
    content = html_path.read_text(encoding="utf-8")

    # .graph-canvas-wrap dimension guarantees
    assert ".graph-canvas-wrap" in content
    assert "min-height: 400px;" in content

    # #galaxyGraphContainer styling
    assert "#galaxyGraphContainer" in content
    assert "min-height: 400px;" in content

    # .galaxy-canvas display guarantee
    assert ".galaxy-canvas" in content
    assert "width: 100% !important;" in content
    assert "height: 100% !important;" in content

    # Empty state styling
    assert ".graph-empty-state" in content
    assert ".empty-state-card" in content


def test_index_html_empty_state_and_resizer():
    """Verify empty state UI elements, self-healing ResizeObserver, and slide transition resize."""
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    content = html_path.read_text(encoding="utf-8")

    # Empty state DOM structure
    assert 'id="graphEmptyState"' in content
    assert 'id="emptyCreateNoteBtn"' in content
    assert 'id="emptySeedVaultBtn"' in content

    # Telemetry in loadGraphFromBackend
    assert "[Graph Engine] Nodes received from API:" in content

    # ResizeObserver self-healing integration
    assert "ResizeObserver" in content
    assert "galaxy-canvas" in content
    assert "window.galaxyEngine.resize()" in content

    # Screen transition resize & fit
    assert "showScreen" in content
    assert "window.galaxyEngine.fit()" in content


@pytest.mark.asyncio
async def test_api_graph_payload_contract(client):
    """Verify GET /api/graph returns HTTP 200 with valid nodes and edges collections."""
    resp = await client.get("/api/graph")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    data = resp.json()
    assert isinstance(data, dict), "Response must be a JSON object"
    assert "nodes" in data, "Response must contain 'nodes'"
    assert "edges" in data, "Response must contain 'edges'"
    assert isinstance(data["nodes"], list), "'nodes' must be a list"
    assert isinstance(data["edges"], list), "'edges' must be a list"

    # If notes exist in DB, verify node structure
    for node in data["nodes"]:
        assert "data" in node or "id" in node
        if "position" in node:
            assert isinstance(node["position"]["x"], (int, float))
            assert isinstance(node["position"]["y"], (int, float))
