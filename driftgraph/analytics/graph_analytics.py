"""driftgraph/analytics/graph_analytics.py

Graph Intelligence & Analytics Engine:
- God node identification (PageRank, degree, betweenness centrality, hub scoring)
- Shortest path & DFS path traversal ("What connects X to Y?", "How does X reach Y?")
- Cross-community bridge detection ("What are the surprising connections in my notes?")
- Automated exploration questions generation from community boundaries
- Topic/Entity subgraph extraction
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple, Any
import networkx as nx

from driftgraph.analytics.models import (
    GodNode,
    PathResult,
    PathStep,
    SurprisingConnection,
    SuggestedQuestion,
    SubgraphData,
    GraphAnalyticsReport,
)
from driftgraph.graph.storage import SQLiteStorage


class GraphAnalyticsEngine:
    """Performs deep topological analysis and intelligence on the knowledge graph."""

    def __init__(self, storage: SQLiteStorage):
        self.storage = storage

    async def _build_nx_graph(self) -> Tuple[nx.MultiDiGraph, Dict[str, Any]]:
        """Construct a NetworkX MultiDiGraph from SQLite storage nodes and edges."""
        nodes = await self.storage.get_all_nodes()
        edges = await self.storage.get_all_edges()

        g = nx.MultiDiGraph()
        node_map = {}
        for n in nodes:
            g.add_node(n.id, name=n.name, type=n.type, description=n.description, community_id=n.community_id)
            node_map[n.id] = n
            node_map[n.name.lower()] = n

        for e in edges:
            rel_type = getattr(e, "predicate", getattr(e, "type", "RELATED"))
            g.add_edge(e.source, e.target, key=e.id, type=rel_type, weight=e.weight, description=e.description)

        return g, node_map

    async def generate_report(self) -> GraphAnalyticsReport:
        """Generate a complete graph intelligence and analytics report."""
        g, node_map = await self._build_nx_graph()
        comms = await self.storage.get_communities()

        n_count = g.number_of_nodes()
        e_count = g.number_of_edges()

        if n_count == 0:
            return GraphAnalyticsReport(
                node_count=0,
                edge_count=0,
                community_count=len(comms),
                density=0.0,
                is_connected=False,
                god_nodes=[],
                top_relations=[],
                surprising_connections=[],
                suggested_questions=[],
            )

        # Basic density
        density = round(nx.density(g), 4)
        is_conn = nx.is_weakly_connected(g) if n_count > 0 else False

        # God nodes
        god_nodes = self._compute_god_nodes(g, node_map, top_n=5)

        # Top relation types
        edge_types = [d.get("type", "RELATED_TO") for _, _, d in g.edges(data=True)]
        type_counts = {}
        for et in edge_types:
            type_counts[et] = type_counts.get(et, 0) + 1
        top_relations = [
            {"type": k, "count": v}
            for k, v in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:6]
        ]

        # Surprising connections (cross-community bridges)
        surprising = self._detect_surprising_connections(g, node_map, comms)

        # Suggested Questions
        suggested = self._generate_suggested_questions(god_nodes, surprising, comms)

        return GraphAnalyticsReport(
            node_count=n_count,
            edge_count=e_count,
            community_count=len(comms),
            density=density,
            is_connected=is_conn,
            god_nodes=god_nodes,
            top_relations=top_relations,
            surprising_connections=surprising,
            suggested_questions=suggested,
        )

    def _compute_god_nodes(
        self,
        g: nx.MultiDiGraph,
        node_map: Dict[str, Any],
        top_n: int = 5
    ) -> List[GodNode]:
        """Identify central 'God Nodes' combining PageRank, Degree, and Betweenness."""
        if g.number_of_nodes() == 0:
            return []

        # Simple graph for algorithms
        simple_g = nx.DiGraph(g)

        # Degree
        degrees = dict(g.degree())
        # PageRank
        try:
            pageranks = nx.pagerank(simple_g, weight="weight", max_iter=200)
        except Exception:
            pageranks = {n: 1.0 / len(g) for n in g.nodes()}

        # Betweenness centrality
        try:
            betweenness = nx.betweenness_centrality(simple_g, weight="weight")
        except Exception:
            betweenness = {n: 0.0 for n in g.nodes()}

        # Composite score
        max_deg = max(degrees.values()) if degrees and max(degrees.values()) > 0 else 1
        max_pr = max(pageranks.values()) if pageranks and max(pageranks.values()) > 0 else 1
        max_bet = max(betweenness.values()) if betweenness and max(betweenness.values()) > 0 else 1

        scored = []
        for nid in g.nodes():
            norm_deg = degrees.get(nid, 0) / max_deg
            norm_pr = pageranks.get(nid, 0) / max_pr
            norm_bet = betweenness.get(nid, 0) / max_bet
            hub_score = round(0.4 * norm_pr + 0.35 * norm_deg + 0.25 * norm_bet, 3)

            n_obj = node_map.get(nid)
            name = n_obj.name if n_obj else nid
            ntype = n_obj.type if n_obj else "Entity"

            scored.append({
                "id": nid,
                "name": name,
                "type": ntype,
                "degree": degrees.get(nid, 0),
                "pagerank": round(pageranks.get(nid, 0), 4),
                "betweenness": round(betweenness.get(nid, 0), 4),
                "hub_score": hub_score,
            })

        scored.sort(key=lambda x: x["hub_score"], reverse=True)

        results = []
        for idx, item in enumerate(scored[:top_n]):
            rank = idx + 1
            expl = (
                f"Rank #{rank} core nexus: Connected to {item['degree']} entities with a "
                f"PageRank of {item['pagerank']:.3f} and hub influence score of {item['hub_score']}."
            )
            results.append(GodNode(
                id=item["id"],
                name=item["name"],
                type=item["type"],
                degree=item["degree"],
                pagerank=item["pagerank"],
                betweenness=item["betweenness"],
                hub_score=item["hub_score"],
                explanation=expl,
            ))

        return results

    async def find_shortest_path(self, source_name: str, target_name: str) -> PathResult:
        """Find shortest connection path between two concepts."""
        g, node_map = await self._build_nx_graph()
        src_id = self._resolve_node_id(source_name, node_map)
        tgt_id = self._resolve_node_id(target_name, node_map)

        if not src_id or not tgt_id:
            return PathResult(
                source=source_name,
                target=target_name,
                path_found=False,
                narrative=f"Could not resolve entity '{source_name if not src_id else target_name}' in the knowledge graph."
            )

        # Convert to undirected for flexible path discovery
        undirected_g = g.to_undirected()
        try:
            path_nodes = nx.shortest_path(undirected_g, source=src_id, target=tgt_id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return PathResult(
                source=source_name,
                target=target_name,
                path_found=False,
                narrative=f"No navigable relationship path found between '{source_name}' and '{target_name}'."
            )

        steps: List[PathStep] = []
        node_names = []
        for n in path_nodes:
            n_obj = node_map.get(n)
            node_names.append(n_obj.name if n_obj else n)

        narrative_parts = [node_names[0]]
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            u_name, v_name = node_names[i], node_names[i + 1]

            # Look up edge
            edge_data = None
            if g.has_edge(u, v):
                edge_data = list(g.get_edge_data(u, v).values())[0]
            elif g.has_edge(v, u):
                edge_data = list(g.get_edge_data(v, u).values())[0]

            rel = edge_data.get("type", "CONNECTED_TO") if edge_data else "CONNECTED_TO"
            steps.append(PathStep(source=u_name, relation=rel, target=v_name))
            narrative_parts.append(f"--[{rel}]--> {v_name}")

        hops = len(steps)
        narrative = f"Connected in {hops} hop(s): " + " ".join(narrative_parts)

        return PathResult(
            source=source_name,
            target=target_name,
            path_found=True,
            hops=hops,
            node_sequence=node_names,
            steps=steps,
            narrative=narrative,
        )

    def _resolve_node_id(self, query: str, node_map: Dict[str, Any]) -> Optional[str]:
        q = query.strip().lower()
        if q in node_map:
            val = node_map[q]
            return val.id if hasattr(val, "id") else q

        # Prefix or substring match
        for key, val in node_map.items():
            if q in key or key in q:
                return val.id if hasattr(val, "id") else key
        return None

    def _detect_surprising_connections(
        self,
        g: nx.MultiDiGraph,
        node_map: Dict[str, Any],
        communities: List[Any],
    ) -> List[SurprisingConnection]:
        """Detect bridge edges connecting different community partitions."""
        node_to_comm = {}
        for c in communities:
            for nid in getattr(c, "node_ids", []):
                node_to_comm[nid] = c.id

        surprising = []
        for u, v, data in g.edges(data=True):
            comm_u = node_to_comm.get(u)
            comm_v = node_to_comm.get(v)

            # If both nodes belong to communities and they are different
            if comm_u and comm_v and comm_u != comm_v:
                u_obj = node_map.get(u)
                v_obj = node_map.get(v)
                u_name = u_obj.name if u_obj else u
                v_name = v_obj.name if v_obj else v
                rel = data.get("type", "RELATED_TO")

                surprising.append(SurprisingConnection(
                    source_name=u_name,
                    source_type=u_obj.type if u_obj else "Entity",
                    target_name=v_name,
                    target_type=v_obj.type if v_obj else "Entity",
                    relation=rel,
                    source_community_id=comm_u,
                    target_community_id=comm_v,
                    rationale=f"Cross-community link bridging partition '{comm_u}' and '{comm_v}' via '{rel}'.",
                ))

        return surprising[:8]

    def _generate_suggested_questions(
        self,
        god_nodes: List[GodNode],
        surprising: List[SurprisingConnection],
        communities: List[Any],
    ) -> List[SuggestedQuestion]:
        """Generate targeted inquiry questions derived from graph topology."""
        questions: List[SuggestedQuestion] = []

        # 1. Cross-community bridge questions
        for bridge in surprising[:3]:
            q_text = f"What is the strategic relationship between {bridge.source_name} and {bridge.target_name} across domains?"
            questions.append(SuggestedQuestion(
                question=q_text,
                category="cross_community",
                entities_involved=[bridge.source_name, bridge.target_name],
                rationale=f"Discovered unexpected bridge relation '{bridge.relation}' connecting separated clusters.",
            ))

        # 2. Central hub questions
        for hub in god_nodes[:3]:
            q_text = f"Why is {hub.name} the most influential entity in this knowledge graph, and what depends on it?"
            questions.append(SuggestedQuestion(
                question=q_text,
                category="central_hub",
                entities_involved=[hub.name],
                rationale=f"Identified as a top God Node with degree {hub.degree} and hub score {hub.hub_score}.",
            ))

        # 3. Community synthesis questions
        for c in communities[:2]:
            title = getattr(c, "title", None) or f"Community {c.id}"
            q_text = f"What are the core principles unifying the '{title}' cluster?"
            questions.append(SuggestedQuestion(
                question=q_text,
                category="boundary",
                entities_involved=[title],
                rationale=f"Hierarchical community partition containing {len(getattr(c, 'node_ids', []))} concepts.",
            ))

        return questions

    async def extract_subgraph(self, entity_name: str, depth: int = 1) -> SubgraphData:
        """Extract local neighborhood subgraph around a specific entity."""
        g, node_map = await self._build_nx_graph()
        center_id = self._resolve_node_id(entity_name, node_map)

        if not center_id or center_id not in g:
            return SubgraphData(center_entity=entity_name, nodes=[], edges=[], depth=depth)

        # Ego graph
        undirected = g.to_undirected()
        sub_nodes = nx.single_source_shortest_path_length(undirected, center_id, cutoff=depth).keys()

        out_nodes = []
        for nid in sub_nodes:
            n_obj = node_map.get(nid)
            out_nodes.append({
                "id": nid,
                "name": n_obj.name if n_obj else nid,
                "type": n_obj.type if n_obj else "Entity",
                "description": n_obj.description if n_obj else "",
            })

        out_edges = []
        for u, v, data in g.edges(sub_nodes, data=True):
            if v in sub_nodes:
                out_edges.append({
                    "source": u,
                    "target": v,
                    "type": data.get("type", "RELATED_TO"),
                    "weight": data.get("weight", 1.0),
                })

        return SubgraphData(
            center_entity=entity_name,
            nodes=out_nodes,
            edges=out_edges,
            depth=depth
        )
