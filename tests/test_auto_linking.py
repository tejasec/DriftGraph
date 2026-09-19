"""
tests/test_auto_linking.py

Comprehensive tests for:
1. Automated note linking via shared extracted entities from the Knowledge Graph.
2. Automated note linking via cross-note entity relationships.
3. Automated latent semantic connections via SBERT cosine similarity.
4. Dynamic threshold control for semantic linking.
5. Soft-delete and restoration reactivity for automated links.
6. HTML/CSS structure verification for the screen-wide slide transition.
"""

import json
from pathlib import Path
import aiosqlite
import pytest
from httpx import AsyncClient, ASGITransport

from driftgraph.config import config as global_config
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.graph.models import Node, Edge
from driftgraph.serve.app import app


@pytest.mark.asyncio
async def test_automated_linking_via_shared_entities(tmp_path, monkeypatch):
    """
    Two notes that share an extracted entity automatically discover an edge
    without requiring manual [[wikilinks]].
    """
    db_file = tmp_path / "shared_ent.db"
    notes_dir = tmp_path / "notes_shared"
    notes_dir.mkdir(parents=True, exist_ok=True)

    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create Note 1: discusses Sentence-BERT embeddings
        r1 = await ac.post("/api/notes", json={
            "title": "Dense Vector Search",
            "content": "Using FAISS index for high-dimensional nearest neighbor vector search."
        })
        assert r1.status_code == 201
        n1 = r1.json()

        # Create Note 2: discusses similarity retrieval
        r2 = await ac.post("/api/notes", json={
            "title": "Vector Similarity",
            "content": "Cosine distance comparison against indexed representations."
        })
        assert r2.status_code == 201
        n2 = r2.json()

        # Before adding shared KG entity, notes have no wikilinks
        # Now seed a shared entity node in the Knowledge Graph with provenance in both notes
        shared_ent = Node(
            id="concept_vector_index",
            name="Vector Index",
            type="TECHNOLOGY",
            description="High-dimensional indexing structure",
            degree=2,
            provenance_chunk_ids=[f"{n1['id']}_chunk_0", f"{n2['id']}_chunk_0"]
        )
        await storage.save_graph([shared_ent], [], [])

        # Query /api/graph
        resp_graph = await ac.get("/api/graph")
        assert resp_graph.status_code == 200
        graph = resp_graph.json()

        assert len(graph["nodes"]) == 2
        # Automatically discovered edge between n1 and n2 via shared entity
        assert len(graph["edges"]) == 1
        edge = graph["edges"][0]["data"]
        assert edge["source"] in (n1["id"], n2["id"])
        assert edge["target"] in (n1["id"], n2["id"])
        assert edge["label"] == "shares_entity"
        assert "Vector Index" in edge["description"]


@pytest.mark.asyncio
async def test_automated_linking_via_cross_note_entity_relations(tmp_path, monkeypatch):
    """
    When Entity A in Note 1 is connected to Entity B in Note 2 in the edges table,
    an automated graph edge connects Note 1 and Note 2.
    """
    db_file = tmp_path / "entity_rel.db"
    notes_dir = tmp_path / "notes_rel"
    notes_dir.mkdir(parents=True, exist_ok=True)

    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r1 = await ac.post("/api/notes", json={
            "title": "Machine Learning Model",
            "content": "Supervised training of neural networks."
        })
        n1 = r1.json()

        r2 = await ac.post("/api/notes", json={
            "title": "GPU Acceleration",
            "content": "Hardware acceleration using CUDA cores."
        })
        n2 = r2.json()

        # Seed entity A (from Note 1) and entity B (from Note 2) and an edge between them
        node_a = Node(id="neural_net", name="Neural Network", type="MODEL", provenance_chunk_ids=[f"{n1['id']}_chunk_0"])
        node_b = Node(id="cuda", name="CUDA", type="HARDWARE", provenance_chunk_ids=[f"{n2['id']}_chunk_0"])
        edge_ab = Edge(
            id="e_nn_cuda",
            source="neural_net",
            target="cuda",
            predicate="accelerated_by",
            description="Neural networks are accelerated by CUDA",
            weight=0.9
        )
        await storage.save_graph([node_a, node_b], [edge_ab], [])

        resp_graph = await ac.get("/api/graph")
        assert resp_graph.status_code == 200
        graph = resp_graph.json()

        assert len(graph["nodes"]) == 2
        assert len(graph["edges"]) == 1
        edge = graph["edges"][0]["data"]
        assert edge["label"] == "accelerated_by"
        assert n1["id"] in (edge["source"], edge["target"])
        assert n2["id"] in (edge["source"], edge["target"])


@pytest.mark.asyncio
async def test_automated_latent_semantic_linking(tmp_path, monkeypatch):
    """
    Two notes with strong semantic overlap automatically discover a
    semantic_similarity edge even without explicit wikilinks or extracted entities.
    """
    db_file = tmp_path / "semantic_link.db"
    notes_dir = tmp_path / "notes_sem"
    notes_dir.mkdir(parents=True, exist_ok=True)

    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Note 1: Deep learning transformers
        r1 = await ac.post("/api/notes", json={
            "title": "Transformer Architecture Attention Mechanism",
            "content": "Self-attention layers and multi-head attention mechanisms in deep learning transformers."
        })
        n1 = r1.json()

        # Note 2: Closely related transformer text
        r2 = await ac.post("/api/notes", json={
            "title": "Attention Layers in Transformers",
            "content": "Multi-head attention mechanisms and self-attention in modern transformer models."
        })
        n2 = r2.json()

        # Note 3: Completely unrelated topic
        r3 = await ac.post("/api/notes", json={
            "title": "Baking Sourdough Bread Recipe",
            "content": "Flour, water, wild yeast starter fermentation temperature and sourdough baking crust."
        })
        n3 = r3.json()

        # Query /api/graph with threshold=0.70
        resp_graph = await ac.get("/api/graph?threshold=0.70")
        assert resp_graph.status_code == 200
        graph = resp_graph.json()

        assert len(graph["nodes"]) == 3
        # Notes 1 and 2 should be semantically linked! Note 3 should remain unconnected
        assert len(graph["edges"]) == 1
        edge = graph["edges"][0]["data"]
        assert edge["label"] == "semantic_similarity"
        assert {edge["source"], edge["target"]} == {n1["id"], n2["id"]}
        assert edge["weight"] >= 0.70

        # Now test threshold query parameter: with high threshold 0.99, edge vanishes
        resp_strict = await ac.get("/api/graph?threshold=0.99")
        graph_strict = resp_strict.json()
        assert len(graph_strict["edges"]) == 0


@pytest.mark.asyncio
async def test_soft_delete_reactivity_on_automated_links(tmp_path, monkeypatch):
    """
    Soft-deleting a note removes its automated links; restoring it brings them back.
    """
    db_file = tmp_path / "delete_auto.db"
    notes_dir = tmp_path / "notes_del"
    notes_dir.mkdir(parents=True, exist_ok=True)

    storage = SQLiteStorage(db_path=str(db_file))
    await storage.initialize_schema()

    monkeypatch.setattr(global_config.database, "sqlite_path", str(db_file))
    monkeypatch.setattr(global_config.paths, "notes_dir", str(notes_dir))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r1 = await ac.post("/api/notes", json={
            "title": "Quantum Physics Principles",
            "content": "Quantum superposition, entanglement, and quantum state wavefunctions."
        })
        n1 = r1.json()

        r2 = await ac.post("/api/notes", json={
            "title": "Quantum Superposition and Wavefunctions",
            "content": "Wavefunctions, quantum state entanglement, and superposition in quantum physics."
        })
        n2 = r2.json()

        g_init = (await ac.get("/api/graph?threshold=0.70")).json()
        assert len(g_init["nodes"]) == 2
        assert len(g_init["edges"]) == 1

        # Soft delete Note 1
        await ac.delete(f"/api/notes/{n1['id']}?permanent=false")

        g_del = (await ac.get("/api/graph?threshold=0.70")).json()
        assert len(g_del["nodes"]) == 1
        assert len(g_del["edges"]) == 0

        # Restore Note 1
        await ac.post(f"/api/notes/{n1['id']}/undo")

        g_restored = (await ac.get("/api/graph?threshold=0.70")).json()
        assert len(g_restored["nodes"]) == 2
        assert len(g_restored["edges"]) == 1


def test_html_slide_transition_markup_and_css():
    """
    Verify frontend/index.html defines the required Motion Pipeline CSS
    and top-level view containers for the screen-wide slide transition.
    """
    html_file = Path("frontend/index.html")
    assert html_file.exists()
    content = html_file.read_text(encoding="utf-8")

    # 1. Viewport and motion classes
    assert ".view-viewport" in content
    assert ".view-screen" in content
    assert "transition: transform 450ms cubic-bezier" in content

    # 2. State classes
    assert ".hero-active #hero-landing" in content
    assert ".workspace-active #hero-landing" in content
    assert ".hero-active #app-workspace" in content
    assert ".workspace-active #app-workspace" in content

    # 3. DOM Containers
    assert 'id="hero-landing"' in content
    assert 'id="app-workspace"' in content
    assert 'id="btn-open-explorer"' in content
