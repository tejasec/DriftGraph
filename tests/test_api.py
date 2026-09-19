"""
Tests for FastAPI endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from driftgraph.serve.app import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "DriftGraph"


@pytest.mark.asyncio
async def test_graph_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/graph")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data


@pytest.mark.asyncio
async def test_create_note_endpoint(tmp_path, monkeypatch):
    """POST /api/ingest/notes must write a markdown note to the notes directory."""
    from driftgraph.config import config as global_config
    import os

    notes_dir = tmp_path / "notes"
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/ingest/notes",
            json={"title": "API Smoke", "content": "A real note about hybrid retrieval."}
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["id"].startswith("api_smoke")
        assert payload["filename"].endswith(".md")

        written = list(notes_dir.glob("*.md"))
        assert len(written) == 1
        text = written[0].read_text(encoding="utf-8")
        assert text.startswith("---")
        assert "A real note about hybrid retrieval." in text


@pytest.mark.asyncio
async def test_create_note_endpoint_rejects_blank(tmp_path, monkeypatch):
    from driftgraph.config import config as global_config

    monkeypatch.setattr(global_config.paths, "notes_dir", str(tmp_path / "notes"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/ingest/notes", json={"content": "   "})
        assert resp.status_code == 400
        assert list(tmp_path.glob("*/*.md")) == []  # no note file written


@pytest.mark.asyncio
async def test_layout_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/graph/layout?recompute=true&iterations=100")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
