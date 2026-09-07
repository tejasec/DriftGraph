"""
Knowledge Graph Builder using NetworkX, embeddings, and community detection.
"""

from typing import List, Dict, Tuple, Any, Optional
import networkx as nx
import numpy as np
import structlog

from driftgraph.extract.models import Entity, Relation, ExtractionResult
from driftgraph.embed.base import BaseEmbedder
from driftgraph.graph.models import Node, Edge, Community
from driftgraph.graph.dedup import EntityDeduplicator, normalize_entity_name
from driftgraph.graph.communities import CommunityDetector

logger = structlog.get_logger(__name__)


class KnowledgeGraphBuilder:
    """Builds and enriches the Knowledge Graph from extracted entities, relations, and embeddings."""

    def __init__(
        self,
        embedder: Optional[BaseEmbedder] = None,
        deduplicator: Optional[EntityDeduplicator] = None,
        community_detector: Optional[CommunityDetector] = None
    ):
        self.embedder = embedder
        self.deduplicator = deduplicator or EntityDeduplicator()
        self.community_detector = community_detector or CommunityDetector()
        self.graph = nx.MultiDiGraph()

    def build_from_extractions(
        self,
        extractions: List[ExtractionResult]
    ) -> Tuple[List[Node], List[Edge], List[Community]]:
        """
        1. Collect all entities & relations across chunks
        2. Deduplicate & resolve entities
        3. Build NetworkX graph
        4. Detect Leiden / Louvain communities
        5. Generate node/edge models
        """
        all_entities: List[Entity] = []
        all_relations: List[Relation] = []

        for ext in extractions:
            all_entities.extend(ext.entities)
            all_relations.extend(ext.relations)

        # 1. Deduplicate
        deduped_entities, deduped_relations = self.deduplicator.deduplicate(all_entities, all_relations)

        # 2. Reset NetworkX graph
        self.graph.clear()

        # Map entities by canonical normalized key
        node_lookup: Dict[str, Entity] = {}
        for ent in deduped_entities:
            node_key = normalize_entity_name(ent.name)
            node_lookup[node_key] = ent
            self.graph.add_node(
                node_key,
                name=ent.name,
                type=ent.type,
                description=ent.description,
                source_chunk_id=ent.source_chunk_id
            )

        # Add edges
        edge_list: List[Edge] = []
        for rel in deduped_relations:
            src_key = normalize_entity_name(rel.subject)
            tgt_key = normalize_entity_name(rel.object)

            # Ensure nodes exist
            if src_key not in self.graph:
                self.graph.add_node(src_key, name=rel.subject, type="CONCEPT", description=None)
            if tgt_key not in self.graph:
                self.graph.add_node(tgt_key, name=rel.object, type="CONCEPT", description=None)

            edge_id = f"{src_key}_{rel.predicate}_{tgt_key}"
            self.graph.add_edge(
                src_key,
                tgt_key,
                key=edge_id,
                predicate=rel.predicate,
                description=rel.description,
                weight=rel.confidence,
                confidence=rel.confidence
            )

            edge_list.append(Edge(
                id=edge_id,
                source=src_key,
                target=tgt_key,
                predicate=rel.predicate,
                description=rel.description,
                weight=rel.confidence,
                confidence=rel.confidence,
                provenance_chunk_ids=[rel.source_chunk_id] if rel.source_chunk_id else []
            ))

        # 3. Detect Communities
        communities, node_comm_map = self.community_detector.detect_communities(self.graph)

        # 4. Generate Node models with embeddings
        node_models: List[Node] = []
        node_names_for_embedding: List[str] = []
        node_keys: List[str] = list(self.graph.nodes())

        for k in node_keys:
            name = self.graph.nodes[k].get("name", k)
            desc = self.graph.nodes[k].get("description", "")
            node_names_for_embedding.append(f"{name}: {desc}" if desc else name)

        embeddings_matrix = None
        if self.embedder is not None and node_names_for_embedding:
            embeddings_matrix = self.embedder.embed_texts(node_names_for_embedding)

        for i, k in enumerate(node_keys):
            node_data = self.graph.nodes[k]
            degree = self.graph.degree(k)
            comm_levels = node_comm_map.get(k, {0: 0})
            primary_comm = comm_levels.get(0, 0)

            emb = embeddings_matrix[i].tolist() if embeddings_matrix is not None else None

            node_obj = Node(
                id=k,
                name=node_data.get("name", k),
                type=node_data.get("type", "CONCEPT"),
                description=node_data.get("description"),
                embedding=emb,
                degree=int(degree),
                community_id=primary_comm,
                community_levels=comm_levels,
                provenance_chunk_ids=[node_data.get("source_chunk_id")] if node_data.get("source_chunk_id") else []
            )
            node_models.append(node_obj)

        logger.info(
            "knowledge_graph_assembled",
            num_nodes=len(node_models),
            num_edges=len(edge_list),
            num_communities=len(communities)
        )

        return node_models, edge_list, communities

    def to_cytoscape_elements(self, nodes: List[Node], edges: List[Edge]) -> Dict[str, Any]:
        """Convert Knowledge Graph to Cytoscape.js compatible JSON format."""
        cy_nodes = []
        for n in nodes:
            cy_nodes.append({
                "data": {
                    "id": n.id,
                    "label": n.name,
                    "type": n.type,
                    "description": n.description or "",
                    "degree": n.degree,
                    "community": n.community_id if n.community_id is not None else 0,
                    "community_levels": n.community_levels
                }
            })

        cy_edges = []
        for e in edges:
            cy_edges.append({
                "data": {
                    "id": e.id,
                    "source": e.source,
                    "target": e.target,
                    "label": e.predicate,
                    "description": e.description or "",
                    "weight": e.weight
                }
            })

        return {"nodes": cy_nodes, "edges": cy_edges}

    def to_rdf_turtle(self, nodes: List[Node], edges: List[Edge]) -> str:
        """Export triples to standard RDF Turtle format."""
        lines = [
            "@prefix dg: <http://driftgraph.org/resource/> .",
            "@prefix dgp: <http://driftgraph.org/predicate/> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
        ]

        for n in nodes:
            safe_id = n.id.replace(" ", "_")
            lines.append(f'dg:{safe_id} rdf:type dg:{n.type} ;')
            lines.append(f'    rdfs:label "{n.name}" .')

        for e in edges:
            safe_src = e.source.replace(" ", "_")
            safe_tgt = e.target.replace(" ", "_")
            safe_pred = e.predicate.lower().replace(" ", "_")
            lines.append(f'dg:{safe_src} dgp:{safe_pred} dg:{safe_tgt} .')

        return "\n".join(lines)
