"""
Hierarchical community detection for Knowledge Graphs (Leiden / Louvain / Modularity).
"""

from typing import Dict, List, Set, Tuple, Optional
import networkx as nx
import structlog
from driftgraph.graph.models import Community

logger = structlog.get_logger(__name__)


class CommunityDetector:
    """Detects hierarchical community structures from a NetworkX graph."""

    def __init__(self, resolution: float = 1.0, min_community_size: int = 2, max_levels: int = 3):
        self.resolution = resolution
        self.min_community_size = min_community_size
        self.max_levels = max_levels

    def detect_communities(self, graph: nx.Graph) -> Tuple[List[Community], Dict[str, Dict[int, int]]]:
        """
        Partition graph into hierarchical communities.
        Returns:
            - List of Community objects
            - node_community_map: {node_id: {level: community_id}}
        """
        undirected_g = graph.to_undirected() if graph.is_directed() else graph.copy()
        nodes = list(undirected_g.nodes())
        if not nodes:
            return [], {}

        if undirected_g.number_of_edges() == 0:
            # All isolated nodes in one community
            c = Community(
                id=0,
                level=0,
                name="General Community",
                node_ids=nodes,
                summary=f"Community of {len(nodes)} entities."
            )
            node_map = {n: {0: 0} for n in nodes}
            return [c], node_map

        communities_list: List[Community] = []
        node_community_map: Dict[str, Dict[int, int]] = {n: {} for n in nodes}
        community_id_counter = 0

        # Try Leiden or NetworkX Louvain / Greedy modularity
        partitions_by_level: List[Dict[str, int]] = []
        used_algorithm = "unknown"

        # 1) Leiden (preferred)
        try:
            import igraph as ig
            import leidenalg

            node_labels = list(undirected_g.nodes())
            node_index = {label: idx for idx, label in enumerate(node_labels)}

            g = ig.Graph(n=len(node_labels), directed=False)
            g.vs["label"] = node_labels
            g.add_edges([(node_index[u], node_index[v]) for u, v in undirected_g.edges()])

            leiden_partition = leidenalg.find_partition(
                g,
                leidenalg.RBConfigurationVertexPartition,
                weights=None,
                n_iterations=2,
                seed=0,
                resolution_parameter=self.resolution,
            )
            partition = {
                node_labels[vertex_index]: membership
                for vertex_index, membership in enumerate(leiden_partition.membership)
            }
            partitions_by_level.append(partition)
            used_algorithm = "leidenalg"
        except Exception as e:
            logger.warning("leiden_community_detection_unavailable", error=str(e))
            try:
                # 2) python-louvain (community) partition
                import community as community_louvain
                partition = community_louvain.best_partition(undirected_g, resolution=self.resolution)
                partitions_by_level.append(partition)
                used_algorithm = "python_louvain"
            except Exception:
                try:
                    # 3) NetworkX built-in greedy modularity
                    from networkx.algorithms.community import greedy_modularity_communities
                    comm_sets = greedy_modularity_communities(undirected_g)
                    partition = {}
                    for idx, cset in enumerate(comm_sets):
                        for n in cset:
                            partition[n] = idx
                    partitions_by_level.append(partition)
                    used_algorithm = "greedy_modularity"
                except Exception as e:
                    logger.warning("community_detection_fallback_connected_components", error=str(e))
                    # Fallback: connected components
                    components = list(nx.connected_components(undirected_g))
                    partition = {}
                    for idx, cset in enumerate(components):
                        for n in cset:
                            partition[n] = idx
                    partitions_by_level.append(partition)
                    used_algorithm = "connected_components"

        logger.info("community_detection_method", algorithm=used_algorithm)

        # Build Level 0 (Coarse) Communities
        level_0_partition = partitions_by_level[0]
        group_to_nodes: Dict[int, List[str]] = {}
        for n, group_id in level_0_partition.items():
            group_to_nodes.setdefault(group_id, []).append(n)

        level_0_comm_id_map: Dict[int, int] = {}
        for group_id, member_nodes in group_to_nodes.items():
            cid = community_id_counter
            community_id_counter += 1
            level_0_comm_id_map[group_id] = cid

            top_node_names = member_nodes[:3]
            comm_name = f"Community {cid}: {', '.join(top_node_names)}"

            comm = Community(
                id=cid,
                level=0,
                parent_id=None,
                name=comm_name,
                node_ids=member_nodes,
                findings=[],
                themes=[n for n in top_node_names],
                confidence=0.9
            )
            communities_list.append(comm)

            for n in member_nodes:
                node_community_map[n][0] = cid

        # Build Sub-communities (Level 1) for large clusters
        for group_id, member_nodes in group_to_nodes.items():
            if len(member_nodes) >= self.min_community_size * 2:
                sub_g = undirected_g.subgraph(member_nodes)
                try:
                    from networkx.algorithms.community import greedy_modularity_communities
                    sub_comms = greedy_modularity_communities(sub_g)
                    if len(sub_comms) > 1:
                        parent_cid = level_0_comm_id_map[group_id]
                        for sub_cset in sub_comms:
                            sub_nodes = list(sub_cset)
                            sub_cid = community_id_counter
                            community_id_counter += 1
                            sub_name = f"Sub-community {sub_cid}: {', '.join(sub_nodes[:2])}"
                            sub_comm = Community(
                                id=sub_cid,
                                level=1,
                                parent_id=parent_cid,
                                name=sub_name,
                                node_ids=sub_nodes,
                                themes=sub_nodes[:2],
                                confidence=0.85
                            )
                            communities_list.append(sub_comm)
                            for n in sub_nodes:
                                node_community_map[n][1] = sub_cid
                except Exception:
                    pass

        return communities_list, node_community_map
