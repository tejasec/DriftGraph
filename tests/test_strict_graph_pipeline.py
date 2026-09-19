"""
tests/test_strict_graph_pipeline.py

Verification tests for the Strict Database-Driven Graph Pipeline:
1. Clean Database Test: 0 notes -> empty arrays and exact zeroes in stats.
2. Deterministic Count: Exactly N notes -> exactly N nodes in /api/graph.
3. Strict Referential Integrity:
   - Valid wikilinks ([[Note Title]]) form edges.
   - Dangling links do not produce edges or ghost nodes.
   - Explicit edges table rows between active notes are preserved.
4. Mutation-Driven Graph Reactivity:
   - Modifying note links via PUT dynamically updates edges.
5. Soft-Delete & Purge Isolation:
   - Soft-deleted notes and incident edges are completely excluded.
   - Restoring a note restores its nodes and incident edges.
   - Deleting all notes leaves the graph and stats completely vacant.
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
async def test_clean_database_empty_graph_and_stats(tmp_path, monkeypatch):
    """On a fresh database with 0 notes, /api/graph and /api/graph/stats return empty/zero datasets."""
    db_file = tmp_path / "clean_empty.db"
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Verify GET /api/graph
        resp_graph = await ac.get("/api/graph")
        assert resp_graph.status_code == 200
        graph_data = resp_graph.json()
        assert graph_data == {"nodes": [], "edges": []}

        # 2. Verify GET /api/graph/stats
        resp_stats = await ac.get("/api/graph/stats")
        assert resp_stats.status_code == 200
        stats_data = resp_stats.json()
        assert stats_data["node_count"] == 0
        assert stats_data["edge_count"] == 0
        assert stats_data["community_count"] == 0
        assert stats_data["density"] == 0.0
        assert stats_data["avg_degree"] == 0.0
        assert stats_data["levels"] == [0]

        # 3. Verify GET /api/graph/communities
        resp_comms = await ac.get("/api/graph/communities")
        assert resp_comms.status_code == 200
        assert resp_comms.json() == []


@pytest.mark.asyncio
async def test_deterministic_count_and_referential_integrity(tmp_path, monkeypatch):
    """
    If DB has N notes, /api/graph returns exactly N nodes.
    Wikilinks create edges between active notes, while dangling links are omitted.
    """
    db_file = tmp_path / "deterministic.db"
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create Note A: links to Note B and a nonexistent note [[Ghost Topic]]
        res_a = await ac.post("/api/notes", json={
            "title": "Architecture Overview",
            "content": "# Architecture\n\nSee [[Distributed Cache]] and [[Ghost Topic]]."
        })
        assert res_a.status_code == 201
        note_a = res_a.json()

        # Create Note B: links to Note C
        res_b = await ac.post("/api/notes", json={
            "title": "Distributed Cache",
            "content": "# Distributed Cache\n\nImplemented with [[Raft Consensus]]."
        })
        assert res_b.status_code == 201
        note_b = res_b.json()

        # Create Note C: standalone
        res_c = await ac.post("/api/notes", json={
            "title": "Raft Consensus",
            "content": "# Raft Consensus\n\nLeader election and log replication."
        })
        assert res_c.status_code == 201
        note_c = res_c.json()

        # Fetch /api/graph
        resp_graph = await ac.get("/api/graph")
        assert resp_graph.status_code == 200
        graph = resp_graph.json()

        # Deterministic count: Exactly 3 nodes! No ghost node for [[Ghost Topic]]
        assert len(graph["nodes"]) == 3
        node_ids = {n["data"]["id"] for n in graph["nodes"]}
        assert node_ids == {note_a["id"], note_b["id"], note_c["id"]}

        # Edges: Exactly 2 valid edges (A -> B and B -> C)
        assert len(graph["edges"]) == 2
        edge_pairs = {(e["data"]["source"], e["data"]["target"]) for e in graph["edges"]}
        assert (note_a["id"], note_b["id"]) in edge_pairs
        assert (note_b["id"], note_c["id"]) in edge_pairs

        # Degrees:
        node_map = {n["data"]["id"]: n["data"] for n in graph["nodes"]}
        assert node_map[note_a["id"]]["degree"] == 1  # Out to B
        assert node_map[note_b["id"]]["degree"] == 2  # In from A, out to C
        assert node_map[note_c["id"]]["degree"] == 1  # In from B

        # Stats
        resp_stats = await ac.get("/api/graph/stats")
        stats = resp_stats.json()
        assert stats["node_count"] == 3
        assert stats["edge_count"] == 2
        assert stats["avg_degree"] == round((2.0 * 2) / 3, 2)


@pytest.mark.asyncio
async def test_mutation_reactivity_and_edge_updates(tmp_path, monkeypatch):
    """Updating links in a note dynamically adds or removes edges."""
    db_file = tmp_path / "mutation.db"
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res1 = await ac.post("/api/notes", json={"title": "Alpha", "content": "Initial content with no links."})
        res2 = await ac.post("/api/notes", json={"title": "Beta", "content": "Beta content."})
        n1 = res1.json()
        n2 = res2.json()

        # Initially 0 edges
        g1 = (await ac.get("/api/graph")).json()
        assert len(g1["nodes"]) == 2
        assert len(g1["edges"]) == 0

        # Update Alpha to link to Beta
        await ac.put(f"/api/notes/{n1['id']}", json={
            "title": "Alpha",
            "content": "Now Alpha references [[Beta]] explicitly."
        })

        g2 = (await ac.get("/api/graph")).json()
        assert len(g2["edges"]) == 1
        assert g2["edges"][0]["data"]["source"] == n1["id"]
        assert g2["edges"][0]["data"]["target"] == n2["id"]

        # Remove the link from Alpha
        await ac.put(f"/api/notes/{n1['id']}", json={
            "title": "Alpha",
            "content": "Link removed."
        })

        g3 = (await ac.get("/api/graph")).json()
        assert len(g3["edges"]) == 0


@pytest.mark.asyncio
async def test_soft_delete_and_complete_purge_isolation(tmp_path, monkeypatch):
    """Soft-deleted and purged notes are immediately evicted along with their incident edges."""
    db_file = tmp_path / "delete_isolation.db"
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r1 = await ac.post("/api/notes", json={"title": "NodeOne", "content": "Link to [[NodeTwo]]."})
        r2 = await ac.post("/api/notes", json={"title": "NodeTwo", "content": "Link to [[NodeThree]]."})
        r3 = await ac.post("/api/notes", json={"title": "NodeThree", "content": "Target."})
        n1, n2, n3 = r1.json(), r2.json(), r3.json()

        # 3 nodes, 2 edges
        g_init = (await ac.get("/api/graph")).json()
        assert len(g_init["nodes"]) == 3
        assert len(g_init["edges"]) == 2

        # 1. Soft-delete NodeTwo
        del_res = await ac.delete(f"/api/notes/{n2['id']}?permanent=false")
        assert del_res.status_code == 200

        # Now only 2 nodes (NodeOne, NodeThree), and 0 edges (both edges were connected to NodeTwo)
        g_after_del = (await ac.get("/api/graph")).json()
        assert len(g_after_del["nodes"]) == 2
        active_ids = {n["data"]["id"] for n in g_after_del["nodes"]}
        assert active_ids == {n1["id"], n3["id"]}
        assert len(g_after_del["edges"]) == 0

        # Stats reflect 2 nodes and 0 edges
        stats = (await ac.get("/api/graph/stats")).json()
        assert stats["node_count"] == 2
        assert stats["edge_count"] == 0

        # 2. Restore NodeTwo
        undo_res = await ac.post(f"/api/notes/{n2['id']}/undo")
        assert undo_res.status_code == 200

        g_restored = (await ac.get("/api/graph")).json()
        assert len(g_restored["nodes"]) == 3
        assert len(g_restored["edges"]) == 2

        # 3. Permanent purge of all notes
        for nid in [n1["id"], n2["id"], n3["id"]]:
            await ac.delete(f"/api/notes/{nid}?permanent=true")

        # Must leave the graph completely vacant with no lingering residual points
        g_vacant = (await ac.get("/api/graph")).json()
        assert g_vacant == {"nodes": [], "edges": []}

        stats_vacant = (await ac.get("/api/graph/stats")).json()
        assert stats_vacant["node_count"] == 0
        assert stats_vacant["edge_count"] == 0
        assert stats_vacant["density"] == 0.0
        assert stats_vacant["avg_degree"] == 0.0


@pytest.mark.asyncio
async def test_strict_user_note_navigator_and_graph_parity(tmp_path, monkeypatch):
    """
    Verify 100% parity between the Notes Navigator dataset (GET /api/notes)
    and the interactive Graph View dataset (GET /api/graph & GET /api/graph/notes).
    Orphaned database records with missing disk files are ignored.
    """
    db_file = tmp_path / "parity_test.db"
    notes_dir = tmp_path / "notes_parity"
    notes_dir.mkdir(parents=True, exist_ok=True)

    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Fresh zero-state parity
        nav_empty = (await ac.get("/api/notes")).json()
        graph_empty = (await ac.get("/api/graph")).json()
        notes_api_empty = (await ac.get("/api/graph/notes")).json()

        assert nav_empty == []
        assert graph_empty == {"nodes": [], "edges": []}
        assert notes_api_empty == []

        # 2. Inject ghost/seed records into SQLite pointing to nonexistent files
        async with aiosqlite.connect(str(db_file)) as db:
            await db.execute(
                "INSERT INTO notes (id, title, source_file, raw_content) VALUES ('ghost_1', 'Ghost Note', '/fake/path/ghost.md', 'Fake content')"
            )
            await db.execute(
                "INSERT INTO nodes (id, name, type) VALUES ('ghost_node', 'Ghost Node', 'NOTE')"
            )
            await db.commit()

        # Ghost records must NOT pollute Notes Navigator or Graph View
        nav_ghost = (await ac.get("/api/notes")).json()
        graph_ghost = (await ac.get("/api/graph")).json()
        assert nav_ghost == []
        assert graph_ghost == {"nodes": [], "edges": []}

        # 3. Create a real note via API
        r_user = await ac.post("/api/notes", json={"title": "User Guide", "content": "See [[Architecture]] for details."})
        assert r_user.status_code == 201
        user_id = r_user.json()["id"]

        nav_disk = (await ac.get("/api/notes")).json()
        graph_disk = (await ac.get("/api/graph")).json()
        editor_disk = (await ac.get("/api/graph/notes")).json()

        # Both must show exactly 1 note with matching IDs
        assert len(nav_disk) == 1
        assert len(graph_disk["nodes"]) == 1
        assert len(editor_disk) == 1
        assert nav_disk[0]["id"] == user_id
        assert graph_disk["nodes"][0]["data"]["id"] == user_id
        assert editor_disk[0]["id"] == user_id
        assert len(graph_disk["edges"]) == 0  # Architecture doesn't exist yet

        # 4. Create the target note via API
        r_arch = await ac.post("/api/notes", json={"title": "Architecture", "content": "System design notes."})
        assert r_arch.status_code == 201

        nav_both = (await ac.get("/api/notes")).json()
        graph_both = (await ac.get("/api/graph")).json()
        editor_both = (await ac.get("/api/graph/notes")).json()

        assert len(nav_both) == 2
        assert len(graph_both["nodes"]) == 2
        assert len(editor_both) == 2
        assert len(graph_both["edges"]) == 1  # user_guide -> Architecture edge resolved

        # 5. Clean purge
        for n in nav_both:
            await ac.delete(f"/api/notes/{n['id']}?permanent=true")

        assert (await ac.get("/api/notes")).json() == []
        assert (await ac.get("/api/graph")).json() == {"nodes": [], "edges": []}
        assert (await ac.get("/api/graph/notes")).json() == []

