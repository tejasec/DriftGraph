"""
tests/test_deletion.py

Unit and pipeline tests for:
- Module A: Soft delete, instant undo, bulk delete, bulk undo, empty trash, and atomic cascade purge.
- Module B: Static asset physics worker serving and layout performance invariants.
"""

import json
import pytest
import numpy as np
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from driftgraph.config import config as global_config
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.graph.models import Node, Edge, Community
from driftgraph.graph.vector_store import VectorIndex
from driftgraph.serve.app import app


@pytest.mark.asyncio
async def test_soft_delete_and_instant_undo(tmp_path):
    db_file = tmp_path / "soft_del_test.db"
    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    # 1. Populate mock notes, chunks, nodes
    async with storage._connect() if hasattr(storage, "_connect") else __import__("aiosqlite").connect(str(db_file)) as db:
        await db.execute("INSERT INTO notes (id, title, raw_content) VALUES ('n1', 'Note One', 'Content 1')")
        await db.execute("INSERT INTO notes (id, title, raw_content) VALUES ('n2', 'Note Two', 'Content 2')")
        await db.execute("INSERT INTO chunks (id, note_id, text) VALUES ('c1', 'n1', 'Chunk 1')")
        await db.execute("INSERT INTO chunks (id, note_id, text) VALUES ('c2', 'n2', 'Chunk 2')")
        await db.execute("INSERT INTO chunks_fts (chunk_id, note_id, text, title) VALUES ('c1', 'n1', 'Chunk 1', 'Note One')")
        await db.execute("INSERT INTO chunks_fts (chunk_id, note_id, text, title) VALUES ('c2', 'n2', 'Chunk 2', 'Note Two')")
        await db.commit()

    # Nodes: node1 belongs solely to n1; node2 belongs solely to n2; shared belongs to both
    n1 = Node(id="ent1", name="Alpha", type="ENTITY", degree=1, provenance_chunk_ids=["c1"])
    n2 = Node(id="ent2", name="Beta", type="ENTITY", degree=1, provenance_chunk_ids=["c2"])
    n_shared = Node(id="ent_shared", name="Shared", type="CONCEPT", degree=2, provenance_chunk_ids=["c1", "c2"])
    e1 = Edge(id="e1", source="ent1", target="ent_shared", predicate="RELATES", provenance_chunk_ids=["c1"])
    e2 = Edge(id="e2", source="ent2", target="ent_shared", predicate="RELATES", provenance_chunk_ids=["c2"])

    await storage.save_graph([n1, n2, n_shared], [e1, e2], [])

    # Verify baseline
    active_nodes = await storage.get_all_nodes(include_deleted=False)
    assert len(active_nodes) == 3
    active_edges = await storage.get_all_edges(include_deleted=False)
    assert len(active_edges) == 2

    # 2. Soft delete n1
    del_count = await storage.soft_delete_notes(["n1"])
    assert del_count == 1

    # Verify soft deleted IDs
    soft_notes = await storage.get_soft_deleted_note_ids()
    assert "n1" in soft_notes
    soft_chunks = await storage.get_soft_deleted_chunk_ids()
    assert "c1" in soft_chunks

    # 3. Graph filtering: ent1 is hidden because all its provenance chunks are soft deleted
    filtered_nodes = await storage.get_all_nodes(include_deleted=False)
    node_ids = {n.id for n in filtered_nodes}
    assert "ent1" not in node_ids
    assert "ent2" in node_ids
    assert "ent_shared" in node_ids

    # Edge connected to ent1 is also hidden
    filtered_edges = await storage.get_all_edges(include_deleted=False)
    assert len(filtered_edges) == 1
    assert filtered_edges[0].id == "e2"

    # With include_deleted=True, all nodes are returned
    all_nodes = await storage.get_all_nodes(include_deleted=True)
    assert len(all_nodes) == 3

    # 4. Instant Restore / Undo
    restore_count = await storage.restore_notes(["n1"])
    assert restore_count == 1
    assert await storage.get_soft_deleted_note_ids() == []

    restored_nodes = await storage.get_all_nodes(include_deleted=False)
    assert len(restored_nodes) == 3
    restored_edges = await storage.get_all_edges(include_deleted=False)
    assert len(restored_edges) == 2


@pytest.mark.asyncio
async def test_atomic_cascade_permanent_purge(tmp_path):
    db_file = tmp_path / "purge_test.db"
    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    import aiosqlite
    async with aiosqlite.connect(str(db_file)) as db:
        await db.execute("INSERT INTO notes (id, title, raw_content) VALUES ('docA', 'Doc A', 'Content A')")
        await db.execute("INSERT INTO notes (id, title, raw_content) VALUES ('docB', 'Doc B', 'Content B')")
        await db.execute("INSERT INTO chunks (id, note_id, text) VALUES ('cA', 'docA', 'Chunk A text')")
        await db.execute("INSERT INTO chunks (id, note_id, text) VALUES ('cB', 'docB', 'Chunk B text')")
        await db.execute("INSERT INTO chunks_fts (chunk_id, note_id, text, title) VALUES ('cA', 'docA', 'Chunk A text', 'Doc A')")
        await db.execute("INSERT INTO chunks_fts (chunk_id, note_id, text, title) VALUES ('cB', 'docB', 'Chunk B text', 'Doc B')")
        await db.commit()

    # Vector store with FAISS
    vec_path = tmp_path / "faiss.index"
    vec_index = VectorIndex(dimension=4, index_path=str(vec_path))
    vA = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    vB = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    vec_index.add(["cA", "cB"], np.vstack([vA, vB]))
    vec_index.save()

    # Graph elements
    nodeA = Node(id="entA", name="Entity A", type="THING", degree=1, provenance_chunk_ids=["cA"])
    nodeB = Node(id="entB", name="Entity B", type="THING", degree=1, provenance_chunk_ids=["cB"])
    nodeShared = Node(id="entAB", name="Shared Entity", type="THING", degree=2, provenance_chunk_ids=["cA", "cB"])

    edgeA = Edge(id="edgeA", source="entA", target="entAB", predicate="LINK", provenance_chunk_ids=["cA"])
    edgeB = Edge(id="edgeB", source="entB", target="entAB", predicate="LINK", provenance_chunk_ids=["cB"])

    comm = Community(id=1, level=0, name="Community 1", node_ids=["entA", "entB", "entAB"], summary="Test comm")

    await storage.save_graph([nodeA, nodeB, nodeShared], [edgeA, edgeB], [comm])

    # Execute atomic purge of docA
    stats = await storage.purge_notes_atomic(["docA"])
    assert stats["deleted_notes_count"] == 1
    assert "cA" in stats["deleted_chunk_ids"]
    assert stats["deleted_nodes_count"] == 1  # entA has 0 remaining provenance
    assert stats["deleted_edges_count"] == 1  # edgeA deleted

    # Evict vector from FAISS
    vec_index.remove_ids(stats["deleted_chunk_ids"])
    results = vec_index.search(vA, top_k=2)
    result_ids = [r[0] for r in results]
    assert "cA" not in result_ids
    assert "cB" in result_ids

    # Check database state
    async with aiosqlite.connect(str(db_file)) as db:
        # Notes
        cur = await db.execute("SELECT id FROM notes")
        notes_left = [r[0] for r in await cur.fetchall()]
        assert notes_left == ["docB"]

        # Chunks
        cur = await db.execute("SELECT id FROM chunks")
        chunks_left = [r[0] for r in await cur.fetchall()]
        assert chunks_left == ["cB"]

        # FTS5
        cur = await db.execute("SELECT chunk_id FROM chunks_fts")
        fts_left = [r[0] for r in await cur.fetchall()]
        assert fts_left == ["cB"]

        # Nodes: entA deleted, entB and entAB survive
        cur = await db.execute("SELECT id, degree, provenance FROM nodes")
        nodes_rows = {r[0]: (r[1], json.loads(r[2])) for r in await cur.fetchall()}
        assert "entA" not in nodes_rows
        assert "entB" in nodes_rows
        assert "entAB" in nodes_rows

        # Surviving node's provenance pruned to surviving chunks
        assert nodes_rows["entAB"][1] == ["cB"]
        # Degree recomputed: entAB has 1 remaining edge (edgeB)
        assert nodes_rows["entAB"][0] == 1

        # Community membership updated
        cur = await db.execute("SELECT node_ids FROM communities WHERE id = 1")
        row = await cur.fetchone()
        comm_nodes = json.loads(row[0])
        assert "entA" not in comm_nodes
        assert set(comm_nodes) == {"entB", "entAB"}


@pytest.mark.asyncio
async def test_notes_api_soft_delete_and_undo(tmp_path, monkeypatch):
    notes_dir = tmp_path / "notes_api"
    notes_dir.mkdir(parents=True, exist_ok=True)
    db_file = tmp_path / "notes_api.db"

    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))
    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))

    # Create a note file on disk
    note_path = notes_dir / "quick_note.md"
    note_path.write_text(
        "---\ntitle: Quick Note\ndate: 2026-09-18\nsource_type: markdown\n---\n\nSample body content here.\n",
        encoding="utf-8"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. List notes
        resp = await ac.get("/api/notes")
        assert resp.status_code == 200
        items = resp.json()
        assert any(n["id"] == "quick_note" for n in items)

        # 2. Soft delete note
        del_resp = await ac.delete("/api/notes/quick_note?permanent=false")
        assert del_resp.status_code == 200
        del_data = del_resp.json()
        assert del_data["action"] == "soft_delete"

        # File still exists on disk in soft delete
        assert note_path.exists()

        # Hidden by default from note listing
        resp2 = await ac.get("/api/notes")
        assert not any(n["id"] == "quick_note" for n in resp2.json())

        # Included when include_deleted=True
        resp_incl = await ac.get("/api/notes?include_deleted=true")
        assert any(n["id"] == "quick_note" for n in resp_incl.json())

        # 3. Undo / restore
        undo_resp = await ac.post("/api/notes/quick_note/undo")
        assert undo_resp.status_code == 200
        assert undo_resp.json()["action"] == "undo"

        # Note is visible again
        resp3 = await ac.get("/api/notes")
        assert any(n["id"] == "quick_note" for n in resp3.json())

        # 4. Permanent delete
        perm_resp = await ac.delete("/api/notes/quick_note?permanent=true")
        assert perm_resp.status_code == 200
        assert perm_resp.json()["action"] == "permanent_purge"

        # File is unlinked from disk
        assert not note_path.exists()


@pytest.mark.asyncio
async def test_bulk_delete_and_empty_trash_api(tmp_path, monkeypatch):
    notes_dir = tmp_path / "bulk_notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    db_file = tmp_path / "bulk.db"

    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))
    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))

    for name in ["alpha", "beta", "gamma"]:
        p = notes_dir / f"{name}.md"
        p.write_text(f"---\ntitle: Note {name.title()}\n---\n\nContent for {name}\n", encoding="utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Bulk soft delete alpha and beta
        bulk_resp = await ac.post(
            "/api/notes/bulk-delete",
            json={"note_ids": ["alpha", "beta"], "permanent": False}
        )
        assert bulk_resp.status_code == 200
        assert bulk_resp.json()["action"] == "bulk_soft_delete"

        # List notes: only gamma remains
        list_resp = await ac.get("/api/notes")
        ids = [n["id"] for n in list_resp.json()]
        assert "gamma" in ids
        assert "alpha" not in ids
        assert "beta" not in ids

        # Bulk undo beta
        undo_resp = await ac.post("/api/notes/bulk-undo", json={"note_ids": ["beta"]})
        assert undo_resp.status_code == 200
        list_resp2 = await ac.get("/api/notes")
        ids2 = [n["id"] for n in list_resp2.json()]
        assert "beta" in ids2
        assert "alpha" not in ids2

        # Empty trash: permanently purges alpha
        trash_resp = await ac.post("/api/notes/trash/empty")
        assert trash_resp.status_code == 200
        assert trash_resp.json()["action"] == "trash_emptied"
        assert not (notes_dir / "alpha.md").exists()
        assert (notes_dir / "beta.md").exists()
        assert (notes_dir / "gamma.md").exists()

        # Calling empty trash again on empty trash
        empty_again = await ac.post("/api/notes/trash/empty")
        assert empty_again.status_code == 200
        assert empty_again.json()["count"] == 0


@pytest.mark.asyncio
async def test_static_assets_worker_served():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Served at /static/assets/js/graph-worker.js
        resp1 = await ac.get("/static/assets/js/graph-worker.js")
        assert resp1.status_code == 200
        assert "graph-worker.js" in resp1.text
        assert "initSimulation" in resp1.text

        # Also served at /assets/js/graph-worker.js
        resp2 = await ac.get("/assets/js/graph-worker.js")
        assert resp2.status_code == 200
        assert "initSimulation" in resp2.text
