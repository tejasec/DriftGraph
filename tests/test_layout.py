"""
Unit tests for server-side ForceAtlas2 layout computation, fallback, and persistence.
"""

import pytest
import networkx as nx
from driftgraph.graph.models import Node, Edge
from driftgraph.graph.layout import (
    collapse_to_undirected,
    normalize_coordinates,
    compute_forceatlas2_layout,
    compute_galaxy_layout,
    apply_layout_to_nodes
)
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.graph.builder import KnowledgeGraphBuilder


def test_collapse_to_undirected():
    multi_g = nx.MultiDiGraph()
    multi_g.add_node("A")
    multi_g.add_node("B")
    multi_g.add_edge("A", "B", key="e1", weight=1.5)
    multi_g.add_edge("B", "A", key="e2", weight=2.0)
    multi_g.add_edge("A", "B", key="e3", weight=0.5)

    undirected = collapse_to_undirected(multi_g)
    assert not undirected.is_directed()
    assert undirected.has_edge("A", "B")
    assert undirected["A"]["B"]["weight"] == 4.0


def test_normalize_coordinates():
    assert normalize_coordinates({}) == {}
    assert normalize_coordinates({"A": (100.0, 200.0)}) == {"A": (0.0, 0.0)}

    raw = {
        "A": (0.0, 0.0),
        "B": (10.0, 0.0),
        "C": (5.0, 10.0),
    }
    norm = normalize_coordinates(raw, scale=1000.0)
    assert len(norm) == 3
    for x, y in norm.values():
        assert -1000.0 <= x <= 1000.0
        assert -1000.0 <= y <= 1000.0

    xs = [x for x, y in norm.values()]
    ys = [y for x, y in norm.values()]
    assert round((max(xs) + min(xs)) / 2.0, 1) == 0.0
    assert round((max(ys) + min(ys)) / 2.0, 1) == 0.0


def test_compute_forceatlas2_layout():
    g = nx.MultiDiGraph()
    nodes = ["N1", "N2", "N3", "N4"]
    for n in nodes:
        g.add_node(n)
    g.add_edge("N1", "N2", weight=1.0)
    g.add_edge("N2", "N3", weight=2.0)
    g.add_edge("N3", "N4", weight=1.0)
    g.add_edge("N4", "N1", weight=1.5)

    pos = compute_forceatlas2_layout(g, iterations=100, scale=800.0)
    assert len(pos) == 4
    for node_id in nodes:
        assert node_id in pos
        x, y = pos[node_id]
        assert isinstance(x, float)
        assert isinstance(y, float)
        assert -800.0 <= x <= 800.0
        assert -800.0 <= y <= 800.0


def test_apply_layout_to_nodes():
    nodes = [
        Node(id="n1", name="Node 1"),
        Node(id="n2", name="Node 2"),
    ]
    coords = {"n1": (150.25, -300.5), "n2": (-150.25, 300.5)}
    apply_layout_to_nodes(nodes, coords)
    assert nodes[0].layout_x == 150.25
    assert nodes[0].layout_y == -300.5
    assert nodes[1].layout_x == -150.25
    assert nodes[1].layout_y == 300.5


def test_cytoscape_elements_includes_position():
    nodes = [
        Node(id="n1", name="Node 1", layout_x=120.0, layout_y=-45.5),
        Node(id="n2", name="Node 2"),
    ]
    edges = [
        Edge(id="e1", source="n1", target="n2", predicate="links_to")
    ]
    builder = KnowledgeGraphBuilder()
    cy_data = builder.to_cytoscape_elements(nodes, edges)

    assert len(cy_data["nodes"]) == 2
    n1_elem = next(n for n in cy_data["nodes"] if n["data"]["id"] == "n1")
    n2_elem = next(n for n in cy_data["nodes"] if n["data"]["id"] == "n2")

    assert "position" in n1_elem
    assert n1_elem["position"] == {"x": 120.0, "y": -45.5}
    assert "position" not in n2_elem


@pytest.mark.asyncio
async def test_sqlite_storage_layout_roundtrip(tmp_path):
    db_path = str(tmp_path / "test_layout.db")
    storage = SQLiteStorage(db_path=db_path)
    await storage.initialize_schema()

    nodes = [
        Node(id="alpha", name="Alpha", layout_x=10.5, layout_y=20.5),
        Node(id="beta", name="Beta", layout_x=-50.0, layout_y=-100.0),
    ]
    await storage.save_graph(nodes, [], [])

    retrieved = await storage.get_all_nodes()
    assert len(retrieved) == 2
    alpha = next(n for n in retrieved if n.id == "alpha")
    beta = next(n for n in retrieved if n.id == "beta")

    assert alpha.layout_x == 10.5
    assert alpha.layout_y == 20.5
    assert beta.layout_x == -50.0
    assert beta.layout_y == -100.0

    # Test update_node_layouts
    await storage.update_node_layouts({"alpha": (333.3, 444.4)})
    updated = await storage.get_all_nodes()
    alpha_up = next(n for n in updated if n.id == "alpha")
    assert alpha_up.layout_x == 333.3
    assert alpha_up.layout_y == 444.4


def test_compute_galaxy_layout_basic():
    g = nx.MultiDiGraph()
    # Core nodes: C1, C2, C3 (triangle with degree 2)
    g.add_edge("C1", "C2")
    g.add_edge("C2", "C3")
    g.add_edge("C3", "C1")
    # Leaf nodes: L1 attached to C1, L2 attached to C2
    g.add_edge("C1", "L1")
    g.add_edge("C2", "L2")
    # Singleton: S1
    g.add_node("S1")

    pos = compute_galaxy_layout(g, scale=1000.0)
    assert len(pos) == 6
    for nid in ["C1", "C2", "C3", "L1", "L2", "S1"]:
        assert nid in pos
        x, y = pos[nid]
        assert -1000.0 <= x <= 1000.0
        assert -1000.0 <= y <= 1000.0


def test_compute_galaxy_layout_tuple_input():
    nodes = [
        Node(id="n1", name="Core 1"),
        Node(id="n2", name="Core 2"),
        Node(id="n3", name="Core 3"),
        Node(id="leaf1", name="Leaf 1"),
    ]
    edges = [
        Edge(id="e1", source="n1", target="n2", predicate="links"),
        Edge(id="e2", source="n2", target="n3", predicate="links"),
        Edge(id="e3", source="n3", target="n1", predicate="links"),
        Edge(id="e4", source="n1", target="leaf1", predicate="links"),
    ]
    pos = compute_galaxy_layout((nodes, edges), scale=600.0)
    assert len(pos) == 4
    for n in nodes:
        assert n.id in pos
        x, y = pos[n.id]
        assert -600.0 <= x <= 600.0
        assert -600.0 <= y <= 600.0


def test_compute_galaxy_layout_empty_and_single():
    assert compute_galaxy_layout(nx.MultiDiGraph()) == {}

    g_single = nx.MultiDiGraph()
    g_single.add_node("only_one")
    pos = compute_galaxy_layout(g_single, scale=500.0)
    assert pos == {"only_one": (0.0, 0.0)}


def test_compute_galaxy_layout_fermat_spiral_growth():
    import math
    # Central hub with 30 leaf nodes
    g = nx.MultiDiGraph()
    g.add_node("HUB")
    for i in range(30):
        leaf = f"leaf_{i}"
        g.add_edge("HUB", leaf)

    pos = compute_galaxy_layout(g, scale=1000.0)
    assert len(pos) == 31
    # Distances from origin should show radial expansion for outer nodes
    radii = [math.hypot(pos[f"leaf_{i}"][0], pos[f"leaf_{i}"][1]) for i in range(30)]
    assert max(radii) > 100.0


@pytest.mark.asyncio
async def test_route_graph_layout_galaxy_engine(tmp_path, monkeypatch):
    from httpx import AsyncClient, ASGITransport
    from driftgraph.serve.app import app
    from driftgraph.config import config as global_config

    db_path = str(tmp_path / "test_galaxy_route.db")
    monkeypatch.setattr(global_config.database, "sqlite_path", db_path)

    storage = SQLiteStorage(db_path=db_path)
    await storage.initialize_schema()

    nodes = [
        Node(id="g1", name="Galaxy Node 1"),
        Node(id="g2", name="Galaxy Node 2"),
        Node(id="g3", name="Galaxy Node 3"),
    ]
    edges = [
        Edge(id="ge1", source="g1", target="g2", predicate="orbits"),
        Edge(id="ge2", source="g2", target="g3", predicate="orbits"),
        Edge(id="ge3", source="g3", target="g1", predicate="orbits"),
    ]
    await storage.save_graph(nodes, edges, [])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/graph/layout?recompute=true&engine=galaxy")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert len(data["nodes"]) == 3
        for n in data["nodes"]:
            assert "position" in n
            assert "x" in n["position"]
            assert "y" in n["position"]

