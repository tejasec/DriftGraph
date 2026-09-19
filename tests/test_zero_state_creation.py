"""
tests/test_zero_state_creation.py

Integration and unit tests for:
- Zero-State resilience: /api/graph/stats with 0 nodes, empty canvas indicator
- Unified Note Creation flow: POST /api/notes atomic creation, PUT /api/notes/{id} auto-save
- SQLite and FTS5 synchronization
- Frontend asset delivery with zero-state guards
"""

import json
from pathlib import Path
import aiosqlite
import pytest
from httpx import AsyncClient, ASGITransport

from driftgraph.config import config as global_config
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.serve.app import app


@pytest.mark.asyncio
async def test_zero_state_stats_resilience(tmp_path, monkeypatch):
    """Ensure /api/graph/stats returns 0 values with zero-division safety when DB is empty."""
    db_file = tmp_path / "empty_stats.db"
    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    notes_dir = tmp_path / "empty_notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))
    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/graph/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["node_count"] == 0
        assert data["edge_count"] == 0
        assert data["density"] == 0.0
        assert data["avg_degree"] == 0.0
        assert data["community_count"] == 0
        assert data["levels"] == [0]


@pytest.mark.asyncio
async def test_unified_note_creation_and_fts_sync(tmp_path, monkeypatch):
    """Ensure POST /api/notes atomically creates the markdown file, SQLite note, chunk, and FTS5 entry."""
    db_file = tmp_path / "note_creation.db"
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_payload = {
            "title": "Quantum Computing Notes",
            "content": "# Quantum Computing\n\nQuantum algorithms leverage superposition and entanglement.",
            "tags": ["quantum", "algorithms"],
            "source_type": "markdown"
        }
        resp = await ac.post("/api/notes", json=create_payload)
        assert resp.status_code == 201
        created = resp.json()

        assert created["id"].startswith("quantum_computing")
        assert created["title"] == "Quantum Computing Notes"
        assert created["word_count"] > 0
        assert created["tags"] == ["quantum", "algorithms"]

        # 1. Verify markdown file on disk
        created_file = notes_dir / created["filename"]
        assert created_file.exists()
        content_on_disk = created_file.read_text(encoding="utf-8")
        assert "title: \"Quantum Computing Notes\"" in content_on_disk
        assert "superposition" in content_on_disk

        # 2. Verify SQLite notes & chunks tables
        async with aiosqlite.connect(str(db_file)) as db:
            async with db.execute("SELECT id, title, raw_content FROM notes WHERE id = ?", (created["id"],)) as cur:
                row = await cur.fetchone()
                assert row is not None
                assert row[0] == created["id"]
                assert row[1] == "Quantum Computing Notes"

            async with db.execute("SELECT chunk_id, title, text FROM chunks_fts WHERE note_id = ?", (created["id"],)) as cur:
                fts_row = await cur.fetchone()
                assert fts_row is not None
                assert "superposition" in fts_row[2]

        # 3. Test Auto-Save via PUT /api/notes/{id}
        update_payload = {
            "title": "Quantum Computing Refined",
            "content": "# Quantum Computing Refined\n\nShor and Grover algorithms revolutionized quantum complexity."
        }
        put_resp = await ac.put(f"/api/notes/{created['id']}", json=update_payload)
        assert put_resp.status_code == 200

        # Verify disk and FTS update
        updated_content = created_file.read_text(encoding="utf-8")
        assert "Quantum Computing Refined" in updated_content
        assert "Grover" in updated_content

        async with aiosqlite.connect(str(db_file)) as db:
            async with db.execute("SELECT title, raw_content FROM notes WHERE id = ?", (created["id"],)) as cur:
                updated_row = await cur.fetchone()
                assert updated_row[0] == "Quantum Computing Refined"
                assert "Grover" in updated_row[1]

            async with db.execute("SELECT title, text FROM chunks_fts WHERE note_id = ?", (created["id"],)) as cur:
                updated_fts = await cur.fetchone()
                assert updated_fts[0] == "Quantum Computing Refined"
                assert "Grover" in updated_fts[1]


@pytest.mark.asyncio
async def test_frontend_zero_state_and_assets_delivered():
    """Verify that the frontend and scripts deliver zero-state indicators and the action button."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Index HTML
        resp_ui = await ac.get("/")
        assert resp_ui.status_code == 200
        html = resp_ui.text
        assert 'id="btn-add-note-top"' in html
        assert "Add Note" in html
        assert "createNewNote" in html
        assert "emptySidebarAddNoteBtn" in html
        assert "emptyModalAddNoteBtn" in html

        # Galaxy Engine JS
        resp_engine = await ac.get("/assets/js/galaxy-engine.js")
        assert resp_engine.status_code == 200
        assert "No notes yet. Click 'Add Note' to start building your graph." in resp_engine.text
        assert "onEmptyCanvasClick" in resp_engine.text

        # Physics Worker JS
        resp_worker = await ac.get("/assets/js/physics.worker.js")
        assert resp_worker.status_code == 200
        assert "PhysicsEngine" in resp_worker.text
