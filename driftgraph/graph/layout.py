"""
ForceAtlas2 server-side layout computation with graceful spring_layout fallback.
"""

import math
from typing import Dict, Tuple, List, Optional, Any, Union
import networkx as nx
import structlog

from driftgraph.graph.models import Node, Edge

logger = structlog.get_logger(__name__)

try:
    from fa2 import ForceAtlas2
except ImportError:
    try:
        from fa2_modified import ForceAtlas2
    except ImportError:
        ForceAtlas2 = None


def collapse_to_undirected(graph: Union[nx.MultiDiGraph, nx.DiGraph, nx.Graph]) -> nx.Graph:
    """
    Convert directed/multi-graph to simple undirected graph,
    summing parallel edge weights and confidences.
    """
    undirected = nx.Graph()
    for n, data in graph.nodes(data=True):
        undirected.add_node(n, **data)

    if isinstance(graph, (nx.MultiDiGraph, nx.MultiGraph)):
        for u, v, k, data in graph.edges(keys=True, data=True):
            if u == v:
                continue
            weight = float(data.get("weight", 1.0))
            if undirected.has_edge(u, v):
                undirected[u][v]["weight"] += weight
            else:
                undirected.add_edge(u, v, weight=weight)
    else:
        for u, v, data in graph.edges(data=True):
            if u == v:
                continue
            weight = float(data.get("weight", 1.0))
            if undirected.has_edge(u, v):
                undirected[u][v]["weight"] += weight
            else:
                undirected.add_edge(u, v, weight=weight)

    return undirected


def normalize_coordinates(
    raw_positions: Dict[str, Tuple[float, float]],
    scale: float = 1000.0
) -> Dict[str, Tuple[float, float]]:
    """
    Center coordinates at (0, 0) and scale to [-scale, scale].
    """
    if not raw_positions:
        return {}
    if len(raw_positions) == 1:
        single_key = next(iter(raw_positions.keys()))
        return {single_key: (0.0, 0.0)}

    xs = [pos[0] for pos in raw_positions.values()]
    ys = [pos[1] for pos in raw_positions.values()]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    w = max_x - min_x
    h = max_y - min_y

    cx = (max_x + min_x) / 2.0
    cy = (max_y + min_y) / 2.0

    max_dim = max(w, h, 1e-6)
    factor = (2.0 * scale) / max_dim

    return {
        node_id: (
            round((x - cx) * factor, 2),
            round((y - cy) * factor, 2)
        )
        for node_id, (x, y) in raw_positions.items()
    }


def compute_forceatlas2_layout(
    graph: Union[nx.MultiDiGraph, nx.DiGraph, nx.Graph, Tuple[List[Node], List[Edge]]],
    iterations: int = 500,
    scale: float = 1000.0,
    seed: int = 42
) -> Dict[str, Tuple[float, float]]:
    """
    Compute 2D layout coordinates using ForceAtlas2 with fallback to NetworkX spring_layout.

    Returns a dict mapping node_id -> (x, y) in [-scale, scale].
    """
    # 1. Normalize input graph
    if isinstance(graph, tuple) and len(graph) == 2:
        nodes, edges = graph
        nx_graph = nx.MultiDiGraph()
        for n in nodes:
            nx_graph.add_node(n.id, name=n.name, type=n.type, degree=n.degree)
        for e in edges:
            nx_graph.add_edge(e.source, e.target, key=e.id, weight=e.weight, predicate=e.predicate)
    else:
        nx_graph = graph

    if len(nx_graph) == 0:
        return {}
    if len(nx_graph) == 1:
        single_node = next(iter(nx_graph.nodes()))
        return {str(single_node): (0.0, 0.0)}

    undirected_g = collapse_to_undirected(nx_graph)

    raw_pos: Optional[Dict[str, Tuple[float, float]]] = None

    # 2. Try ForceAtlas2
    if ForceAtlas2 is not None:
        try:
            fa2_instance = ForceAtlas2(
                outboundAttractionDistribution=True,
                linLogMode=False,
                adjustSizes=False,
                edgeWeightInfluence=1.0,
                jitterTolerance=1.0,
                barnesHutOptimize=True,
                barnesHutTheta=1.2,
                scalingRatio=2.0,
                strongGravityMode=False,
                gravity=1.0,
                verbose=False
            )
            # fa2 expects dict of initial positions or None
            positions = fa2_instance.forceatlas2_networkx_layout(
                undirected_g,
                pos=None,
                iterations=iterations
            )
            raw_pos = {str(k): (float(v[0]), float(v[1])) for k, v in positions.items()}
            logger.info("forceatlas2_layout_computed", num_nodes=len(raw_pos), iterations=iterations)
        except Exception as e:
            logger.warning("forceatlas2_execution_failed_fallback_spring", error=str(e))
            raw_pos = None

    # 3. Fallback to spring_layout
    if raw_pos is None:
        spring_iters = min(iterations, 100)
        positions = nx.spring_layout(undirected_g, iterations=spring_iters, seed=seed, weight="weight")
        raw_pos = {str(k): (float(v[0]), float(v[1])) for k, v in positions.items()}
        logger.info("spring_layout_computed_as_fallback", num_nodes=len(raw_pos), iterations=spring_iters)

    # 4. Center and normalize to [-scale, scale]
    return normalize_coordinates(raw_pos, scale=scale)


GOLDEN_ANGLE_RAD = 137.507764 * (math.pi / 180.0)  # ~2.39996323 radians


def compute_galaxy_layout(
    graph: Union[nx.MultiDiGraph, nx.DiGraph, nx.Graph, Tuple[List[Node], List[Edge]]],
    scale: float = 1000.0,
    iterations: int = 300,
    r_core_ratio: float = 0.35,
    seed: int = 42
) -> Dict[str, Tuple[float, float]]:
    """
    Compute Hybrid Concentric/Phyllotaxis (Galaxy) layout:
    1. Partition nodes into Core (degree >= 2) and Peripheral/Leaves (degree <= 1).
    2. Inner Cluster: Force-directed relaxation of core components constrained to inner radius R_core.
    3. Outer Disk: Sunflower phyllotaxis (Fermat's spiral) with golden angle spacing for peripheral nodes,
       with angular offset based on connected core nodes to avoid edge crossings.
    """
    if isinstance(graph, tuple) and len(graph) == 2:
        nodes, edges = graph
        nx_graph = nx.MultiDiGraph()
        for n in nodes:
            nx_graph.add_node(n.id, name=n.name, type=n.type, degree=n.degree)
        for e in edges:
            nx_graph.add_edge(e.source, e.target, key=e.id, weight=e.weight, predicate=e.predicate)
    else:
        nx_graph = graph

    if len(nx_graph) == 0:
        return {}
    if len(nx_graph) == 1:
        single_node = next(iter(nx_graph.nodes()))
        return {str(single_node): (0.0, 0.0)}

    undirected_g = collapse_to_undirected(nx_graph)
    total_nodes = len(undirected_g)

    # 1. Graph Partitioning: Core (degree >= 2) vs Peripheral (degree <= 1)
    degrees = dict(undirected_g.degree())
    core_nodes = [n for n, d in degrees.items() if d >= 2]
    peripheral_nodes = [n for n, d in degrees.items() if d < 2]

    # Handle edge case: if almost all nodes are degree <= 1, partition top 30% by degree
    if len(core_nodes) < 2 and total_nodes > 3:
        sorted_by_deg = sorted(degrees.keys(), key=lambda n: degrees[n], reverse=True)
        split_idx = max(2, int(total_nodes * 0.3))
        core_nodes = sorted_by_deg[:split_idx]
        peripheral_nodes = sorted_by_deg[split_idx:]
    elif not peripheral_nodes and total_nodes > 10:
        sorted_by_deg = sorted(degrees.keys(), key=lambda n: degrees[n], reverse=True)
        split_idx = max(5, int(total_nodes * 0.5))
        core_nodes = sorted_by_deg[:split_idx]
        peripheral_nodes = sorted_by_deg[split_idx:]

    r_core = scale * r_core_ratio
    positions: Dict[str, Tuple[float, float]] = {}

    # 2. Inner Cluster (Force-Directed Relaxation constrained to R_core)
    if core_nodes:
        core_subgraph = undirected_g.subgraph(core_nodes).copy()
        if len(core_subgraph) == 1:
            positions[str(core_nodes[0])] = (0.0, 0.0)
        else:
            raw_core_pos: Optional[Dict[str, Tuple[float, float]]] = None
            if ForceAtlas2 is not None:
                try:
                    fa2_inst = ForceAtlas2(
                        outboundAttractionDistribution=True,
                        linLogMode=False,
                        adjustSizes=False,
                        edgeWeightInfluence=1.0,
                        jitterTolerance=1.0,
                        barnesHutOptimize=True,
                        scalingRatio=2.0,
                        gravity=1.5,
                        verbose=False
                    )
                    c_pos = fa2_inst.forceatlas2_networkx_layout(core_subgraph, iterations=iterations)
                    raw_core_pos = {str(k): (float(v[0]), float(v[1])) for k, v in c_pos.items()}
                except Exception:
                    raw_core_pos = None

            if raw_core_pos is None:
                c_pos = nx.spring_layout(core_subgraph, iterations=min(iterations, 100), seed=seed)
                raw_core_pos = {str(k): (float(v[0]), float(v[1])) for k, v in c_pos.items()}

            # Center core positions and scale inside R_core
            xs = [p[0] for p in raw_core_pos.values()]
            ys = [p[1] for p in raw_core_pos.values()]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            cx = (max_x + min_x) / 2.0
            cy = (max_y + min_y) / 2.0
            max_d = max(math.hypot(x - cx, y - cy) for x, y in raw_core_pos.values())
            scale_factor = (r_core * 0.85) / max(max_d, 1e-6)

            for nid, (x, y) in raw_core_pos.items():
                positions[nid] = (
                    round((x - cx) * scale_factor, 2),
                    round((y - cy) * scale_factor, 2)
                )

    # 3. Outer Disk (Sunflower Phyllotaxis / Fermat's Spiral)
    if peripheral_nodes:
        connected_peripherals = []
        isolated_peripherals = []

        for p in peripheral_nodes:
            neighbors = list(undirected_g.neighbors(p))
            core_neighbors = [nb for nb in neighbors if str(nb) in positions]
            if core_neighbors:
                parent = core_neighbors[0]
                px, py = positions[str(parent)]
                angle = math.atan2(py, px)
                connected_peripherals.append((p, angle))
            else:
                isolated_peripherals.append(p)

        connected_peripherals.sort(key=lambda item: item[1])
        ordered_peripherals = [item[0] for item in connected_peripherals] + isolated_peripherals

        n_outer = len(ordered_peripherals)
        r_max = scale
        c_step = (r_max - r_core) / max(math.sqrt(n_outer), 1.0)

        for i, node_id in enumerate(ordered_peripherals):
            n_idx = i + 1
            theta = n_idx * GOLDEN_ANGLE_RAD
            r = r_core + c_step * math.sqrt(n_idx)

            if i < len(connected_peripherals):
                parent_angle = connected_peripherals[i][1]
                theta = (parent_angle + (i % 5 - 2) * 0.25)

            x = r * math.cos(theta)
            y = r * math.sin(theta)
            positions[str(node_id)] = (round(x, 2), round(y, 2))

    return positions


def apply_layout_to_nodes(
    nodes: List[Node],
    layout_dict: Dict[str, Tuple[float, float]]
) -> List[Node]:
    """Assign x/y coordinates to Node models in-place and return the list."""
    for n in nodes:
        if n.id in layout_dict:
            n.layout_x, n.layout_y = layout_dict[n.id]
    return nodes
