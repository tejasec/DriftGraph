"""
Unit and integration tests for LightRAG-style Dual-Level Retrieval and Multi-List RRF.
"""

import os
import pytest
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.graph.models import Node, Edge, Community
from driftgraph.ingest.models import Note, NoteMetadata, Chunk
from driftgraph.graph.vector_store import VectorIndex
from driftgraph.embed.sbert import SBERTEmbedder
from driftgraph.query.dual_level import DualLevelRetriever, DualLevelKeywords
from driftgraph.query.local import LocalSearchEngine
from driftgraph.eval.ablation import AblationStudy


@pytest.fixture
async def sample_db(tmp_path):
    db_path = str(tmp_path / "test_dual_level.db")
    storage = SQLiteStorage(db_path=db_path)
    await storage.initialize_schema()

    # Create test notes & chunks
    note1 = Note(
        id="note_fa2",
        content="ForceAtlas2 is a spatialization algorithm for network graphs.",
        raw_content="# ForceAtlas2\nForceAtlas2 is a spatialization algorithm for network graphs.",
        metadata=NoteMetadata(title="ForceAtlas2 Note", source_file="fa2.md")
    )
    chunk1 = Chunk(
        id="chunk_fa2_1",
        note_id="note_fa2",
        source_file="fa2.md",
        chunk_index=0,
        text="ForceAtlas2 is a spatialization force-directed layout algorithm for network graphs and knowledge bases.",
        start_char=0,
        end_char=100,
        token_count=18,
        metadata={"title": "ForceAtlas2 Note"}
    )

    note2 = Note(
        id="note_leiden",
        content="Leiden detects hierarchical communities in graphs.",
        raw_content="# Leiden Algorithm\nLeiden detects hierarchical communities in graphs.",
        metadata=NoteMetadata(title="Leiden Note", source_file="leiden.md")
    )
    chunk2 = Chunk(
        id="chunk_leiden_1",
        note_id="note_leiden",
        source_file="leiden.md",
        chunk_index=0,
        text="Leiden detects hierarchical communities and clusters in multi-level knowledge networks.",
        start_char=0,
        end_char=90,
        token_count=15,
        metadata={"title": "Leiden Note"}
    )

    await storage.save_notes_and_chunks([note1, note2], [chunk1, chunk2])

    # Create test nodes
    node_fa2 = Node(
        id="n_fa2",
        name="ForceAtlas2",
        type="ALGORITHM",
        description="Graph layout algorithm",
        degree=2,
        community_id=0,
        provenance_chunk_ids=["chunk_fa2_1"],
        layout_x=100.0,
        layout_y=200.0
    )
    node_leiden = Node(
        id="n_leiden",
        name="Leiden",
        type="ALGORITHM",
        description="Community detection algorithm",
        degree=2,
        community_id=1,
        provenance_chunk_ids=["chunk_leiden_1"],
        layout_x=-100.0,
        layout_y=-200.0
    )
    node_viz = Node(
        id="n_viz",
        name="Graph Visualization",
        type="CONCEPT",
        description="Visualizing complex network topology",
        degree=2,
        community_id=0,
        provenance_chunk_ids=["chunk_fa2_1", "chunk_leiden_1"],
        layout_x=0.0,
        layout_y=50.0
    )

    # Create edges (including a cross-community bridge edge)
    edge1 = Edge(
        id="e_fa2_viz",
        source="n_fa2",
        target="n_viz",
        predicate="used_for",
        description="ForceAtlas2 enables graph visualization",
        weight=1.0,
        provenance_chunk_ids=["chunk_fa2_1"]
    )
    edge2 = Edge(
        id="e_viz_leiden",
        source="n_viz",
        target="n_leiden",
        predicate="partitions",
        description="Partitions visual graphs",
        weight=0.9,
        provenance_chunk_ids=["chunk_leiden_1"]
    )

    # Communities
    comm0 = Community(
        id=0,
        level=0,
        name="Visualization & Layouts",
        node_ids=["n_fa2", "n_viz"],
        summary="Community exploring spatial algorithms, Cytoscape renderings, and layout coordinates.",
        findings=["ForceAtlas2 centers nodes well."],
        themes=["graph visualization", "layout physics"]
    )
    comm1 = Community(
        id=1,
        level=0,
        name="Community Partitioning",
        node_ids=["n_leiden"],
        summary="Community covering hierarchical partitioning and modularity optimization.",
        findings=["Leiden guarantees well-connected communities."],
        themes=["clustering", "graph topology"]
    )

    await storage.save_graph([node_fa2, node_leiden, node_viz], [edge1, edge2], [comm0, comm1])
    return storage


@pytest.mark.asyncio
async def test_fallback_keyword_extraction(sample_db):
    retriever = DualLevelRetriever(storage=sample_db)
    kw = await retriever._fallback_keyword_extraction("How does ForceAtlas2 spatialization work?")
    assert isinstance(kw, DualLevelKeywords)
    assert len(kw.low_level) > 0
    assert len(kw.high_level) > 0
    assert "ForceAtlas2" in kw.low_level or any("ForceAtlas2" in k for k in kw.low_level)


@pytest.mark.asyncio
async def test_dual_level_retriever_low_and_high_channels(sample_db):
    retriever = DualLevelRetriever(storage=sample_db)
    res = await retriever.retrieve("Tell me about ForceAtlas2 and Graph Visualization")

    assert len(res.entities) > 0
    entity_names = [e.name for e in res.entities]
    assert "ForceAtlas2" in entity_names or "Graph Visualization" in entity_names

    # Verify 1-hop expansion
    assert len(res.relations) > 0

    # Verify cross-community bridge edges
    assert len(res.bridge_edges) > 0
    assert res.bridge_edges[0].source != res.bridge_edges[0].target

    # Verify ranked chunks contains chunk_fa2_1
    chunk_ids = [c[0] for c in res.ranked_chunks]
    assert "chunk_fa2_1" in chunk_ids

    # Verify trace is populated
    assert "keywords" in res.trace
    assert "matched_entities" in res.trace
    assert res.trace["expanded_relations"] > 0


@pytest.mark.asyncio
async def test_multi_list_rrf_scoring(sample_db, tmp_path):
    embedder = SBERTEmbedder()
    vec_index = VectorIndex(dimension=embedder.dimension, index_path=str(tmp_path / "test_vec.index"))

    # Embed sample chunks into vector store
    all_notes = await sample_db.get_all_notes()
    chunks_records = [
        await sample_db.get_chunk_by_id("chunk_fa2_1"),
        await sample_db.get_chunk_by_id("chunk_leiden_1")
    ]
    texts = [c["text"] for c in chunks_records if c]
    ids = [c["id"] for c in chunks_records if c]
    embeddings = embedder.embed_texts(texts)
    vec_index.add(ids, embeddings)

    # 1. Test dual-level ENABLED
    engine_dual = LocalSearchEngine(
        embedder=embedder,
        vector_index=vec_index,
        storage=sample_db,
        dual_level=True
    )
    res_dual = await engine_dual.search("ForceAtlas2 visualization", top_k=3)
    assert res_dual.mode_used == "local"
    assert res_dual.retrieval_trace is not None
    assert res_dual.retrieval_trace["dual_level_active"] is True
    assert res_dual.retrieval_trace["channel_counts"]["graph"] > 0
    assert any(c.source_type == "chunk" for c in res_dual.citations)
    assert any(c.source_type == "node" for c in res_dual.citations)

    # 2. Test dual-level DISABLED
    engine_legacy = LocalSearchEngine(
        embedder=embedder,
        vector_index=vec_index,
        storage=sample_db,
        dual_level=False
    )
    res_legacy = await engine_legacy.search("ForceAtlas2 visualization", top_k=3)
    assert res_legacy.retrieval_trace["dual_level_active"] is False
    assert res_legacy.retrieval_trace["channel_counts"]["graph"] == 0


@pytest.mark.asyncio
async def test_ablation_comparison_function(sample_db, tmp_path):
    embedder = SBERTEmbedder()
    vec_index = VectorIndex(dimension=embedder.dimension, index_path=str(tmp_path / "test_vec2.index"))

    c1 = await sample_db.get_chunk_by_id("chunk_fa2_1")
    c2 = await sample_db.get_chunk_by_id("chunk_leiden_1")
    vec_index.add([c1["id"], c2["id"]], embedder.embed_texts([c1["text"], c2["text"]]))

    study = AblationStudy()
    comparison = await study.compare_retrieval_modes(
        query="Graph Visualization and Spatialization",
        storage=sample_db,
        vector_index=vec_index,
        top_k=2
    )

    assert "standard_hybrid" in comparison
    assert "dual_level" in comparison
    assert "metrics" in comparison
    assert "jaccard_similarity" in comparison["metrics"]
    assert "latency_delta_ms" in comparison["metrics"]
    assert comparison["dual_level"]["trace"]["dual_level_active"] is True
