"""
Graph module for Knowledge Graph construction, deduplication, communities, and persistence.
"""

from driftgraph.graph.models import Node, Edge, Community
from driftgraph.graph.dedup import EntityDeduplicator, normalize_entity_name
from driftgraph.graph.communities import CommunityDetector
from driftgraph.graph.vector_store import VectorIndex
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.graph.builder import KnowledgeGraphBuilder

__all__ = [
    "Node",
    "Edge",
    "Community",
    "EntityDeduplicator",
    "normalize_entity_name",
    "CommunityDetector",
    "VectorIndex",
    "SQLiteStorage",
    "KnowledgeGraphBuilder",
]
