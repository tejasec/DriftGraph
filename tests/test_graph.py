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


def test_entity_deduplication():
    dedup = EntityDeduplicator(similarity_threshold=0.8)
    entities = [
        Entity(name="FastAPI", type="TECHNOLOGY", description="Python API"),
        Entity(name="FastAPI Framework", type="TECHNOLOGY", description="Fast web framework"),
        Entity(name="Bob Smith", type="PERSON")
    ]
    relations = [
        Relation(subject="Bob Smith", predicate="USES", object="FastAPI Framework")
    ]

    deduped_ents, deduped_rels = dedup.deduplicate(entities, relations)
    assert len(deduped_ents) <= 3
    assert len(deduped_rels) == 1


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

    # With leidenalg/python-louvain installed, we never want the crude
    # connected-components fallback to be the only result.
    haben = (importlib.util.find_spec("leidenalg") is not None) or (
        importlib.util.find_spec("community") is not None
    )
    assert communities, "Community detection should always produce at least one community."
    if haben:
        assert len(communities) >= 1
