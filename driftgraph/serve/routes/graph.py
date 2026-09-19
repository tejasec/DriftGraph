import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

import aiosqlite
import frontmatter
import networkx as nx
import numpy as np
import structlog
from fastapi import APIRouter, HTTPException, Query

from driftgraph.config import config
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.graph.builder import KnowledgeGraphBuilder
from driftgraph.graph.models import Community, Node, Edge
from driftgraph.graph.layout import compute_forceatlas2_layout, compute_galaxy_layout, apply_layout_to_nodes
from driftgraph.embed.sbert import SBERTEmbedder
from driftgraph.graph.vector_store import VectorIndex
from driftgraph.graph.dedup import normalize_entity_name

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/graph", tags=["Graph"])


def _clean_stem(s: str) -> str:
    """Normalize a note title, filename, or id into a canonical lowercase lookup key."""
    if not s:
        return ""
    if s.lower().endswith(".md"):
        s = s[:-3]
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[\s-]+", "_", s)


async def build_active_notes_graph(
    storage: SQLiteStorage,
    similarity_threshold: Optional[float] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    """
    Query active notes (WHERE deleted_at IS NULL) and resolve:
    1. Explicit wikilinks with strict referential integrity.
    2. Explicit relational edges from the database.
    3. Automated Shared Entity Relations (notes sharing extracted entities or relational bridges).
    4. Automated Latent Semantic Connections (pairwise cosine similarity on SBERT embeddings).
    
    Returns:
        (nodes_list, edges_list, community_count)
    """
    await storage.initialize_schema()
    active_notes = await storage.get_all_notes(include_deleted=False)

    # 0. Enforce strict disk parity:
    # (a) If notes exist on disk in notes_dir that are not soft-deleted and not yet in SQLite, sync them.
    notes_dir = Path(config.paths.notes_dir)
    soft_deleted_ids = set(await storage.get_soft_deleted_note_ids())
    existing_ids = {str(n["id"]) for n in active_notes}

    if notes_dir.exists():
        for f in sorted(notes_dir.glob("*.md")):
            clean_stem = f.stem.lower().replace(" ", "_")
            if clean_stem not in existing_ids and clean_stem not in soft_deleted_ids and f.name not in soft_deleted_ids:
                try:
                    post = frontmatter.load(str(f))
                    content = post.content.strip()
                    title = str(post.metadata.get("title") or f.stem.replace("_", " ").title())
                    date_val = str(post.metadata.get("date") or "")
                    tags_val = json.dumps(post.metadata.get("tags") or [])
                    stype = str(post.metadata.get("source_type") or "markdown")
                    async with aiosqlite.connect(storage.db_path) as db:
                        await db.execute(
                            """INSERT OR REPLACE INTO notes (id, title, source_file, source_type, date, tags, raw_content)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (clean_stem, title, str(f), stype, date_val, tags_val, content)
                        )
                        await db.commit()
                    active_notes.append({
                        "id": clean_stem,
                        "title": title,
                        "source_file": str(f),
                        "source_type": stype,
                        "date": date_val,
                        "tags": tags_val,
                        "raw_content": content,
                        "deleted_at": None
                    })
                    existing_ids.add(clean_stem)
                except Exception:
                    pass

    # (b) Filter out notes whose source_file is specified but does not exist on disk
    filtered_notes = []
    for n in active_notes:
        sf = n.get("source_file")
        if sf:
            p = Path(sf)
            if not p.exists() and not (notes_dir / p.name).exists():
                continue
        filtered_notes.append(n)
    active_notes = filtered_notes

    if not active_notes:
        return [], [], 0

    # 1. Build resolution indices
    note_by_id: Dict[str, Dict[str, Any]] = {}
    id_by_alias: Dict[str, str] = {}

    for n in active_notes:
        nid = str(n["id"])
        note_by_id[nid] = n

        # Match exact ID (case-insensitive)
        id_by_alias[nid.lower()] = nid
        # Match cleaned stem of ID
        id_by_alias[_clean_stem(nid)] = nid

        title = str(n.get("title") or "").strip()
        if title:
            id_by_alias[title.lower()] = nid
            id_by_alias[_clean_stem(title)] = nid

        src_file = n.get("source_file")
        if src_file:
            p = Path(src_file)
            id_by_alias[p.name.lower()] = nid
            id_by_alias[p.stem.lower()] = nid
            id_by_alias[_clean_stem(p.stem)] = nid

    def resolve_target(raw_target: str) -> Optional[str]:
        target = raw_target.strip().lower()
        if not target:
            return None
        if target in id_by_alias:
            return id_by_alias[target]
        stemmed = _clean_stem(target)
        if stemmed in id_by_alias:
            return id_by_alias[stemmed]
        return None

    def _is_connected(a: str, b: str) -> bool:
        return (a, b) in seen_pairs or (b, a) in seen_pairs

    valid_edges: List[Dict[str, Any]] = []
    seen_pairs: Set[Tuple[str, str]] = set()

    # 2. Extract relationships from explicit wikilinks in raw_content
    wikilink_pattern = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")

    for n in active_notes:
        src_id = str(n["id"])
        content = str(n.get("raw_content") or "")
        matches = wikilink_pattern.findall(content)
        for raw_target in matches:
            tgt_id = resolve_target(raw_target)
            if tgt_id and tgt_id != src_id and tgt_id in note_by_id:
                if not _is_connected(src_id, tgt_id):
                    seen_pairs.add((src_id, tgt_id))
                    valid_edges.append({
                        "id": f"{src_id}__links_to__{tgt_id}",
                        "source": src_id,
                        "target": tgt_id,
                        "predicate": "links_to",
                        "description": f"Wikilink [[{raw_target.strip()}]]",
                        "weight": 1.0
                    })

    # 3. Incorporate explicit relational edges from the edges table (filtering dangling ones)
    db_edges = await storage.get_all_edges(include_deleted=False)
    for e in db_edges:
        if e.source in note_by_id and e.target in note_by_id and e.source != e.target:
            if not _is_connected(e.source, e.target):
                seen_pairs.add((e.source, e.target))
                valid_edges.append({
                    "id": e.id or f"{e.source}__{e.predicate}__{e.target}",
                    "source": e.source,
                    "target": e.target,
                    "predicate": e.predicate or "relates",
                    "description": e.description or "",
                    "weight": e.weight or 1.0
                })

    # 4. Automated Semantic Linking: Shared Entity Relations & Knowledge Graph Bridges
    try:
        chunk_to_note: Dict[str, str] = {}
        async with aiosqlite.connect(storage.db_path) as db:
            async with db.execute("SELECT id, note_id FROM chunks WHERE note_id IS NOT NULL") as cur:
                chunk_rows = await cur.fetchall()
                chunk_to_note = {r[0]: str(r[1]) for r in chunk_rows}

        kg_nodes = await storage.get_all_nodes(include_deleted=False)
        ent_to_notes: Dict[str, Set[str]] = {}

        for kn in kg_nodes:
            notes_for_kn: Set[str] = set()
            for cid in (kn.provenance_chunk_ids or []):
                nid = chunk_to_note.get(cid)
                if not nid and "_chunk_" in cid:
                    nid = cid.rsplit("_chunk_", 1)[0]
                if nid and nid in note_by_id:
                    notes_for_kn.add(nid)

            clean_name = (kn.name or "").strip()
            if len(clean_name) >= 4 and not clean_name.lower().startswith("untitled"):
                name_pattern = re.compile(r"\b" + re.escape(clean_name) + r"\b", re.IGNORECASE)
                for nid, n_dict in note_by_id.items():
                    if nid not in notes_for_kn:
                        text_to_check = f"{n_dict.get('title', '')} {n_dict.get('raw_content', '')}"
                        if name_pattern.search(text_to_check):
                            notes_for_kn.add(nid)

            if notes_for_kn:
                ent_to_notes[kn.id] = notes_for_kn
                if len(notes_for_kn) >= 2:
                    notes_sorted = sorted(list(notes_for_kn))
                    for i in range(len(notes_sorted)):
                        for j in range(i + 1, len(notes_sorted)):
                            src_n, tgt_n = notes_sorted[i], notes_sorted[j]
                            if not _is_connected(src_n, tgt_n):
                                seen_pairs.add((src_n, tgt_n))
                                valid_edges.append({
                                    "id": f"{src_n}__shares__{normalize_entity_name(kn.name)}__{tgt_n}",
                                    "source": src_n,
                                    "target": tgt_n,
                                    "predicate": "shares_entity",
                                    "description": f"Shared concept: {kn.name}",
                                    "weight": 0.85
                                })

        for e in db_edges:
            notes_src = ent_to_notes.get(e.source, set())
            notes_tgt = ent_to_notes.get(e.target, set())
            for n_src in notes_src:
                for n_tgt in notes_tgt:
                    if n_src != n_tgt and not _is_connected(n_src, n_tgt):
                        seen_pairs.add((n_src, n_tgt))
                        valid_edges.append({
                            "id": f"{n_src}__{e.predicate}__{n_tgt}",
                            "source": n_src,
                            "target": n_tgt,
                            "predicate": e.predicate or "relates_to",
                            "description": f"{e.source} {e.predicate} {e.target}",
                            "weight": round(e.weight or 0.8, 2)
                        })
    except Exception as e_err:
        logger.warning("shared_entity_linking_skipped", error=str(e_err))

    # 5. Automated Semantic Linking: Latent Semantic Connections (Cosine Similarity on SBERT Embeddings)
    thresh = similarity_threshold if similarity_threshold is not None else float(getattr(config.graph, "similarity_threshold", 0.70))
    if len(active_notes) >= 2:
        try:
            vec_index = VectorIndex(dimension=384, index_path=config.database.vector_index_path)
            has_vec_index = vec_index.load()
            note_vectors: Dict[str, np.ndarray] = {}

            if has_vec_index and vec_index.vectors is not None:
                for nid in note_by_id:
                    cid = f"{nid}_chunk_0"
                    if cid in vec_index.id_to_index:
                        idx = vec_index.id_to_index[cid]
                        note_vectors[nid] = vec_index.vectors[idx]

            missing_nids = [nid for nid in note_by_id if nid not in note_vectors]
            if missing_nids:
                texts = [f"{note_by_id[nid].get('title', '')} {note_by_id[nid].get('raw_content', '')}".strip() for nid in missing_nids]
                embedder = SBERTEmbedder()
                computed_vecs = await asyncio.to_thread(embedder.embed_texts, texts)
                for i, nid in enumerate(missing_nids):
                    v = computed_vecs[i]
                    norm = np.linalg.norm(v)
                    if norm > 0:
                        v = v / norm
                    note_vectors[nid] = v

            note_ids_list = list(note_by_id.keys())
            for i in range(len(note_ids_list)):
                nid_a = note_ids_list[i]
                vec_a = note_vectors.get(nid_a)
                if vec_a is None:
                    continue
                for j in range(i + 1, len(note_ids_list)):
                    nid_b = note_ids_list[j]
                    vec_b = note_vectors.get(nid_b)
                    if vec_b is None:
                        continue

                    if _is_connected(nid_a, nid_b):
                        continue

                    sim = float(np.dot(vec_a, vec_b))
                    if sim >= thresh:
                        seen_pairs.add((nid_a, nid_b))
                        valid_edges.append({
                            "id": f"{nid_a}__semantic__{nid_b}",
                            "source": nid_a,
                            "target": nid_b,
                            "predicate": "semantic_similarity",
                            "description": f"Semantic similarity ({sim:.2f})",
                            "weight": round(sim, 3)
                        })
        except Exception as sim_err:
            logger.warning("latent_semantic_linking_skipped", error=str(sim_err))

    # 4. Compute accurate degree for each note
    degree_map: Dict[str, int] = {nid: 0 for nid in note_by_id}
    for e in valid_edges:
        degree_map[e["source"]] += 1
        degree_map[e["target"]] += 1

    # 5. Communities: partition active notes graph
    comm_map: Dict[str, int] = {nid: 0 for nid in note_by_id}
    community_count = 0

    if valid_edges:
        try:
            g = nx.Graph()
            for nid in note_by_id:
                g.add_node(nid)
            for e in valid_edges:
                g.add_edge(e["source"], e["target"], weight=e["weight"])

            communities = list(nx.community.louvain_communities(g, seed=42))
            for c_idx, comm_nodes in enumerate(communities):
                for nid in comm_nodes:
                    comm_map[nid] = c_idx
            community_count = len(communities)
        except Exception:
            comm_map = {nid: 0 for nid in note_by_id}
            community_count = 1 if active_notes else 0
    else:
        community_count = 1 if len(active_notes) > 0 else 0

    # 6. Retrieve persistent layout coordinates if available
    coords_map: Dict[str, Tuple[float, float]] = {}
    try:
        async with aiosqlite.connect(storage.db_path) as db:
            async with db.execute("SELECT id, layout_x, layout_y FROM nodes WHERE layout_x IS NOT NULL AND layout_y IS NOT NULL") as cur:
                rows = await cur.fetchall()
                coords_map = {r[0]: (float(r[1]), float(r[2])) for r in rows}
    except Exception:
        coords_map = {}

    # 7. Assemble Cytoscape / Galaxy formatted JSON elements
    cy_nodes = []
    for n in active_notes:
        nid = str(n["id"])
        title = str(n.get("title") or nid)
        stype = str(n.get("source_type") or "NOTE").upper()
        deg = degree_map.get(nid, 0)
        comm = comm_map.get(nid, 0)

        tags_val = n.get("tags")
        tags_list = []
        if tags_val:
            try:
                tags_list = json.loads(tags_val) if isinstance(tags_val, str) else tags_val
            except Exception:
                tags_list = []

        node_data = {
            "id": nid,
            "label": title,
            "title": title,
            "type": stype,
            "degree": deg,
            "community": comm,
            "community_levels": {0: comm},
            "date": str(n.get("date") or ""),
            "tags": tags_list
        }
        node_payload: Dict[str, Any] = {"data": node_data}

        if nid in coords_map:
            node_payload["position"] = {"x": coords_map[nid][0], "y": coords_map[nid][1]}

        cy_nodes.append(node_payload)

    cy_edges = []
    for e in valid_edges:
        cy_edges.append({
            "data": {
                "id": e["id"],
                "source": e["source"],
                "target": e["target"],
                "label": e["predicate"],
                "description": e["description"],
                "weight": e["weight"]
            }
        })

    return cy_nodes, cy_edges, community_count


@router.post("/layout")
async def compute_or_recompute_layout(
    recompute: bool = Query(False, description="Force recompute layout even if positions exist"),
    iterations: int = Query(500, description="Number of layout iterations"),
    engine: str = Query("galaxy", description="Layout engine: 'galaxy' (Hybrid Concentric/Phyllotaxis) or 'forceatlas2'")
) -> Dict[str, Any]:
    """Compute layout server-side (Galaxy or ForceAtlas2) and persist coordinates to SQLite."""
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    active_notes = await storage.get_all_notes(include_deleted=False)

    if active_notes:
        cy_nodes, cy_edges, _ = await build_active_notes_graph(storage)
        if not cy_nodes:
            return {"nodes": [], "edges": []}

        has_coords = all("position" in n for n in cy_nodes)
        if not recompute and has_coords:
            return {"nodes": cy_nodes, "edges": cy_edges}

        node_models = [
            Node(
                id=n["data"]["id"],
                name=n["data"]["label"],
                type=n["data"]["type"],
                degree=n["data"]["degree"],
                community_id=n["data"]["community"],
                layout_x=n.get("position", {}).get("x"),
                layout_y=n.get("position", {}).get("y")
            )
            for n in cy_nodes
        ]
        edge_models = [
            Edge(
                id=e["data"]["id"],
                source=e["data"]["source"],
                target=e["data"]["target"],
                predicate=e["data"]["label"],
                weight=e["data"]["weight"]
            )
            for e in cy_edges
        ]

        if engine.lower() in ("galaxy", "phyllotaxis", "concentric"):
            layout_coords = await asyncio.to_thread(
                compute_galaxy_layout,
                (node_models, edge_models),
                iterations=iterations
            )
        else:
            layout_coords = await asyncio.to_thread(
                compute_forceatlas2_layout,
                (node_models, edge_models),
                iterations=iterations
            )

        await storage.update_node_layouts(layout_coords)

        for n in cy_nodes:
            nid = n["data"]["id"]
            if nid in layout_coords:
                n["position"] = {"x": layout_coords[nid][0], "y": layout_coords[nid][1]}

        return {"nodes": cy_nodes, "edges": cy_edges}
    else:
        # Fallback for unit tests that seed `nodes` table directly without `notes`
        nodes = await storage.get_all_nodes()
        edges = await storage.get_all_edges()
        builder = KnowledgeGraphBuilder()

        if not nodes:
            return {"nodes": [], "edges": []}

        nodes_with_coords = [n for n in nodes if n.layout_x is not None and n.layout_y is not None]
        if not recompute and (len(nodes_with_coords) / len(nodes) >= 0.9):
            return builder.to_cytoscape_elements(nodes, edges)

        if engine.lower() in ("galaxy", "phyllotaxis", "concentric"):
            layout_coords = await asyncio.to_thread(
                compute_galaxy_layout,
                (nodes, edges),
                iterations=iterations
            )
        else:
            layout_coords = await asyncio.to_thread(
                compute_forceatlas2_layout,
                (nodes, edges),
                iterations=iterations
            )

        apply_layout_to_nodes(nodes, layout_coords)
        await storage.update_node_layouts(layout_coords)

        return builder.to_cytoscape_elements(nodes, edges)


@router.get("")
async def get_graph_elements(
    threshold: Optional[float] = Query(None, description="Similarity threshold for automated semantic linking")
) -> Dict[str, Any]:
    """Return Cytoscape.js compatible {nodes: [], edges: []} graph payload of active notes."""
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    nodes, edges, _ = await build_active_notes_graph(storage, similarity_threshold=threshold)
    return {"nodes": nodes, "edges": edges}


@router.get("/communities", response_model=List[Community])
async def get_communities(level: Optional[int] = None):
    """Return detected hierarchical communities."""
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    active_notes = await storage.get_all_notes(include_deleted=False)
    if not active_notes:
        return []
    return await storage.get_communities(level=level)


@router.get("/notes")
async def get_notes() -> List[Dict[str, Any]]:
    """Return all active notes for the frontend editor."""
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    nodes, _, _ = await build_active_notes_graph(storage)
    active_ids = {n["data"]["id"] for n in nodes}
    active_notes = await storage.get_all_notes(include_deleted=False)
    return [n for n in active_notes if str(n["id"]) in active_ids]


@router.get("/stats")
async def get_graph_stats(
    threshold: Optional[float] = Query(None, description="Similarity threshold for automated semantic linking")
) -> Dict[str, Any]:
    """Return graph metrics strictly aggregated from non-deleted notes and valid intra-database edges."""
    try:
        storage = SQLiteStorage(db_path=config.database.sqlite_path)
        nodes, edges, comm_count = await build_active_notes_graph(storage, similarity_threshold=threshold)

        n_count = len(nodes)
        e_count = len(edges)
        density = (2.0 * e_count) / (n_count * (n_count - 1)) if n_count > 1 else 0.0
        avg_deg = (2.0 * e_count) / n_count if n_count > 0 else 0.0

        levels = [0]
        if comm_count > 0:
            levels = list(range(comm_count)) if comm_count > 1 else [0]

        return {
            "node_count": n_count,
            "edge_count": e_count,
            "community_count": comm_count,
            "density": round(density, 4),
            "avg_degree": round(avg_deg, 2),
            "levels": levels
        }
    except Exception:
        return {
            "node_count": 0,
            "edge_count": 0,
            "community_count": 0,
            "density": 0.0,
            "avg_degree": 0.0,
            "levels": [0]
        }
