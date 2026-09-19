"""
Tests for Graph Assembly, Deduplication, and SQLite Persistence.
"""

import pytest
import tempfile
import os
import importlib
import networkx as nx
from driftgraph.extract.models import ExtractionResult, Entity, Relation
from driftgraph.graph import KnowledgeGraphBuilder, EntityDeduplicator, SQLiteStorage, VectorIndex
from driftgraph.graph.communities import CommunityDetector


def test_entity_deduplication_merges_similar():
    dedup = EntityDeduplicator(similarity_threshold=0.8)
    entities = [
        Entity(name="FastAPI", type="TECHNOLOGY", description="Python API"),
        Entity(name="Fast API!", type="TECHNOLOGY", description="Fast web framework"),
        Entity(name="Bob Smith", type="PERSON")
    ]
    relations = [
        Relation(subject="Bob Smith", predicate="USES", object="Fast API!"),
        Relation(subject="Bob Smith", predicate="USES", object="FastAPI")
    ]

    deduped_ents, deduped_rels = dedup.deduplicate(entities, relations)

    # "FastAPI" and "Fast API!" normalize to near-identical names and MUST merge.
    assert len({e.name for e in deduped_ents}) == 2
    assert "Bob Smith" in {e.name for e in deduped_ents}
    # Both relations must be rewritten to the single canonical target.
    assert len({rel.object for rel in deduped_rels}) == 1
    assert len(deduped_rels) == 1


@pytest.mark.asyncio
async def test_storage_fts_search_initializes_schema():
    """search_chunks_fts() must not crash on a fresh database (regression for C1)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        storage = SQLiteStorage(db_path=db_path)
        rows = await storage.search_chunks_fts("anything")
        assert rows == []
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.asyncio
async def test_fts_rows_do_not_accumulate_on_rebuild():
    """Rebuilding must not duplicate FTS rows (regression for C2)."""
    import sqlite3
    from driftgraph.ingest.models import Note, NoteMetadata, Chunk

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        note = Note(
            id="alpha",
            content="Alpha content about FastAPI and GraphRAG.",
            raw_content="Alpha content about FastAPI and GraphRAG.",
            metadata=NoteMetadata(title="Alpha", source_file="/tmp/alpha.md")
        )
        chunk = Chunk(
            id="alpha_c0",
            note_id="alpha",
            source_file="/tmp/alpha.md",
            chunk_index=0,
            text="Alpha content about FastAPI and GraphRAG.",
            start_char=0,
            end_char=40,
            token_count=8,
            metadata={"title": "Alpha"}
        )

        storage = SQLiteStorage(db_path=db_path)
        await storage.initialize_schema()
        for _ in range(2):
            await storage.save_notes_and_chunks([note], [chunk])

        conn = sqlite3.connect(db_path)
        try:
            fts_count = conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0]
            assert fts_count == 1, f"Expected 1 FTS row after rebuild, got {fts_count}"
        finally:
            conn.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.asyncio
async def test_sqlite_storage():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        storage = SQLiteStorage(db_path=db_path)
        await storage.initialize_schema()

        nodes = await storage.get_all_nodes()
        assert len(nodes) == 0
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_community_detection_uses_real_algorithm():
    """Leiden/Louvain should be preferred over the connected-components fallback."""
    g = nx.MultiDiGraph()
    for i in range(10):
        g.add_node(f"n{i}", name=f"Node {i}", type="CONCEPT", description=None)
    for i in range(9):
        g.add_edge(f"n{i}", f"n{i+1}", key=f"e{i}", predicate="RELATES_TO")

    detector = CommunityDetector()
    communities, node_map = detector.detect_communities(g)

    # With leidenalg/python-louvain installed, the detector MUST use them,
    # never the crude connected-components fallback.
    assert communities, "Community detection should always produce at least one community."
    assert detector.last_algorithm is not None

    has_leiden = importlib.util.find_spec("leidenalg") is not None
    has_louvain = importlib.util.find_spec("community") is not None
    if has_leiden:
        assert detector.last_algorithm == "leidenalg", "Leiden should win when available."
    elif has_louvain:
        assert detector.last_algorithm == "python_louvain", "Louvain should win when Leiden is missing."
    else:
        assert detector.last_algorithm in {"greedy_modularity", "connected_components"}
