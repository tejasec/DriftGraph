"""
SQLite persistence with FTS5 search support for DriftGraph.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json
import aiosqlite
import structlog

from driftgraph.ingest.models import Note, Chunk
from driftgraph.graph.models import Node, Edge, Community

logger = structlog.get_logger(__name__)


class SQLiteStorage:
    """Async SQLite storage with FTS5 full text search capabilities."""

    def __init__(self, db_path: str = "./data/driftgraph.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize_schema(self, schema_file: Optional[str] = None):
        """Execute schema.sql to ensure all tables and FTS5 virtual tables exist."""
        if schema_file and Path(schema_file).exists():
            schema_sql = Path(schema_file).read_text(encoding="utf-8")
        else:
            default_schema_path = Path(__file__).parent / "schema.sql"
            if default_schema_path.exists():
                schema_sql = default_schema_path.read_text(encoding="utf-8")
            else:
                schema_sql = ""

        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute("PRAGMA table_info(notes)")
                cols = [row[1] for row in await cursor.fetchall()]
                if cols and "deleted_at" not in cols:
                    await db.execute("ALTER TABLE notes ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL")
                if cols and "source_type" not in cols:
                    await db.execute("ALTER TABLE notes ADD COLUMN source_type TEXT DEFAULT 'markdown'")
            except Exception:
                pass
            await db.executescript(schema_sql)
            try:
                await db.execute("ALTER TABLE notes ADD COLUMN source_type TEXT DEFAULT 'markdown'")
            except Exception:
                pass
            try:
                cursor = await db.execute("PRAGMA table_info(nodes)")
                cols = [row[1] for row in await cursor.fetchall()]
                if "layout_x" not in cols:
                    await db.execute("ALTER TABLE nodes ADD COLUMN layout_x REAL")
                if "layout_y" not in cols:
                    await db.execute("ALTER TABLE nodes ADD COLUMN layout_y REAL")
            except Exception:
                pass
            try:
                cursor = await db.execute("PRAGMA table_info(notes)")
                cols = [row[1] for row in await cursor.fetchall()]
                if "deleted_at" not in cols:
                    await db.execute("ALTER TABLE notes ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_notes_deleted_at ON notes(deleted_at)")
            except Exception:
                pass
            await db.commit()
        logger.info("sqlite_schema_initialized", db_path=str(self.db_path))

    async def save_notes_and_chunks(self, notes: List[Note], chunks: List[Chunk]):
        """Persist Notes and Chunks into relational tables and FTS index."""
        async with aiosqlite.connect(self.db_path) as db:
            # Save notes
            for note in notes:
                await db.execute(
                    """INSERT OR REPLACE INTO notes (id, title, source_file, source_type, date, tags, raw_content)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        note.id,
                        note.metadata.title,
                        note.metadata.source_file,
                        getattr(note.metadata, "source_type", "markdown"),
                        note.metadata.date,
                        json.dumps(note.metadata.tags),
                        note.raw_content
                    )
                )

            # Stale FTS rows (chunks_fts has no triggers, so INSERT OR REPLACE
            # on chunks does not cascade to the virtual table)
            chunk_ids = [c.id for c in chunks]
            if chunk_ids:
                placeholders = ",".join("?" for _ in chunk_ids)
                await db.execute(
                    f"DELETE FROM chunks_fts WHERE chunk_id IN ({placeholders})",
                    chunk_ids
                )

            # Save chunks
            for chunk in chunks:
                await db.execute(
                    """INSERT OR REPLACE INTO chunks (id, note_id, source_file, chunk_index, text, start_char, end_char, token_count)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        chunk.id,
                        chunk.note_id,
                        chunk.source_file,
                        chunk.chunk_index,
                        chunk.text,
                        chunk.start_char,
                        chunk.end_char,
                        chunk.token_count
                    )
                )
                # Index in FTS5
                await db.execute(
                    """INSERT INTO chunks_fts (chunk_id, note_id, text, title)
                       VALUES (?, ?, ?, ?)""",
                    (
                        chunk.id,
                        chunk.note_id,
                        chunk.text,
                        chunk.metadata.get("title", "")
                    )
                )

            await db.commit()

    async def save_graph(
        self,
        nodes: List[Node],
        edges: List[Edge],
        communities: List[Community]
    ):
        """Save Knowledge Graph nodes, edges, and communities."""
        async with aiosqlite.connect(self.db_path) as db:
            # Nodes
            for node in nodes:
                await db.execute(
                    """INSERT OR REPLACE INTO nodes (id, name, type, description, degree, community_id, community_levels, provenance, layout_x, layout_y)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        node.id,
                        node.name,
                        node.type,
                        node.description,
                        node.degree,
                        node.community_id,
                        json.dumps(node.community_levels),
                        json.dumps(node.provenance_chunk_ids),
                        node.layout_x,
                        node.layout_y
                    )
                )

            # Edges
            for edge in edges:
                await db.execute(
                    """INSERT OR REPLACE INTO edges (id, source, target, predicate, description, weight, confidence, provenance)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        edge.id,
                        edge.source,
                        edge.target,
                        edge.predicate,
                        edge.description,
                        edge.weight,
                        edge.confidence,
                        json.dumps(edge.provenance_chunk_ids)
                    )
                )

            # Stale FTS rows for rebuilt community summaries
            community_ids = [c.id for c in communities if c.summary]
            if community_ids:
                placeholders = ",".join("?" for _ in community_ids)
                await db.execute(
                    f"DELETE FROM communities_fts WHERE community_id IN ({placeholders})",
                    community_ids
                )

            # Communities
            for comm in communities:
                await db.execute(
                    """INSERT OR REPLACE INTO communities (id, level, parent_id, name, node_ids, summary, findings, themes, confidence)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        comm.id,
                        comm.level,
                        comm.parent_id,
                        comm.name,
                        json.dumps(comm.node_ids),
                        comm.summary,
                        json.dumps(comm.findings),
                        json.dumps(comm.themes),
                        comm.confidence
                    )
                )
                # FTS for communities
                if comm.summary:
                    await db.execute(
                        """INSERT INTO communities_fts (community_id, level, name, summary, themes)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            comm.id,
                            comm.level,
                            comm.name,
                            comm.summary,
                            json.dumps(comm.themes)
                        )
                    )

            await db.commit()

    async def search_chunks_fts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search notes chunks using SQLite FTS5 BM25 match (excludes soft-deleted notes)."""
        await self.initialize_schema()
        # Sanitize query for FTS5 syntax
        clean_q = "".join(c for c in query if c.isalnum() or c.isspace()).strip()
        if not clean_q:
            return []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT chunks_fts.chunk_id, chunks_fts.note_id, chunks_fts.text, chunks_fts.title, MIN(chunks_fts.rank) AS rank
                   FROM chunks_fts
                   JOIN notes ON chunks_fts.note_id = notes.id
                   WHERE chunks_fts MATCH ? AND notes.deleted_at IS NULL
                   GROUP BY chunks_fts.chunk_id
                   ORDER BY rank LIMIT ?""",
                (clean_q, limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Fetch chunk by its unique ID."""
        await self.initialize_schema()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_notes(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """Fetch all notes with their metadata (excludes soft-deleted by default)."""
        await self.initialize_schema()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if include_deleted:
                cursor = await db.execute("SELECT * FROM notes")
            else:
                cursor = await db.execute("SELECT * FROM notes WHERE deleted_at IS NULL")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_note_by_id(self, note_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Fetch a single note by ID."""
        await self.initialize_schema()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if include_deleted:
                cursor = await db.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            else:
                cursor = await db.execute("SELECT * FROM notes WHERE id = ? AND deleted_at IS NULL", (note_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def soft_delete_notes(self, note_ids: List[str]) -> int:
        """Mark notes as soft-deleted by setting deleted_at (upserting if not yet in SQLite)."""
        if not note_ids:
            return 0
        await self.initialize_schema()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            count = 0
            for nid in note_ids:
                cursor = await db.execute(
                    "UPDATE notes SET deleted_at = CURRENT_TIMESTAMP WHERE id = ? AND deleted_at IS NULL",
                    (nid,)
                )
                if cursor.rowcount > 0:
                    count += cursor.rowcount
                else:
                    check_cur = await db.execute("SELECT id FROM notes WHERE id = ?", (nid,))
                    existing = await check_cur.fetchone()
                    if not existing:
                        clean_nid = nid[:-3] if nid.endswith(".md") else nid
                        clean_check = await db.execute("SELECT id FROM notes WHERE id = ?", (clean_nid,))
                        if not await clean_check.fetchone():
                            await db.execute(
                                """INSERT INTO notes (id, title, deleted_at)
                                   VALUES (?, ?, CURRENT_TIMESTAMP)
                                   ON CONFLICT(id) DO UPDATE SET deleted_at = CURRENT_TIMESTAMP""",
                                (clean_nid, clean_nid)
                            )
                            count += 1
            await db.commit()
            return count

    async def restore_notes(self, note_ids: List[str]) -> int:
        """Restore soft-deleted notes by clearing deleted_at."""
        if not note_ids:
            return 0
        await self.initialize_schema()
        placeholders = ",".join("?" for _ in note_ids)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"UPDATE notes SET deleted_at = NULL WHERE id IN ({placeholders}) AND deleted_at IS NOT NULL",
                note_ids
            )
            count = cursor.rowcount
            await db.commit()
            return count

    async def get_soft_deleted_note_ids(self) -> List[str]:
        """Fetch all note IDs currently in soft-deleted state."""
        await self.initialize_schema()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT id FROM notes WHERE deleted_at IS NOT NULL")
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

    async def get_soft_deleted_chunk_ids(self) -> List[str]:
        """Fetch all chunk IDs belonging to soft-deleted notes."""
        await self.initialize_schema()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT chunks.id FROM chunks 
                   JOIN notes ON chunks.note_id = notes.id 
                   WHERE notes.deleted_at IS NOT NULL"""
            )
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

    async def get_all_nodes(self, include_deleted: bool = False) -> List[Node]:
        """Fetch all nodes (by default excluding nodes whose provenance only consists of soft-deleted chunks)."""
        await self.initialize_schema()
        deleted_chunk_ids = set() if include_deleted else set(await self.get_soft_deleted_chunk_ids())
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM nodes")
            rows = await cursor.fetchall()
            nodes = []
            for r in rows:
                prov = json.loads(r["provenance"] or "[]")
                if not include_deleted and deleted_chunk_ids and prov:
                    active_prov = [cid for cid in prov if cid not in deleted_chunk_ids]
                    if not active_prov:
                        continue
                    prov = active_prov

                nodes.append(Node(
                    id=r["id"],
                    name=r["name"],
                    type=r["type"],
                    description=r["description"],
                    degree=r["degree"] or 0,
                    community_id=r["community_id"],
                    community_levels=json.loads(r["community_levels"] or "{}"),
                    provenance_chunk_ids=prov,
                    layout_x=r["layout_x"] if "layout_x" in r.keys() else None,
                    layout_y=r["layout_y"] if "layout_y" in r.keys() else None
                ))
            return nodes

    async def update_node_layouts(self, layout_dict: Dict[str, Tuple[float, float]]):
        """Batch update node x/y coordinates in the database."""
        await self.initialize_schema()
        async with aiosqlite.connect(self.db_path) as db:
            for node_id, (x, y) in layout_dict.items():
                await db.execute(
                    """INSERT INTO nodes (id, name, type, layout_x, layout_y)
                       VALUES (?, ?, 'NOTE', ?, ?)
                       ON CONFLICT(id) DO UPDATE SET layout_x = excluded.layout_x, layout_y = excluded.layout_y""",
                    (node_id, node_id, x, y)
                )
            await db.commit()

    async def search_nodes(self, query: str, limit: int = 5) -> List[Node]:
        """Search nodes by name or description matching query substring."""
        await self.initialize_schema()
        clean_q = f"%{query.strip().lower()}%"
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM nodes 
                   WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ?
                   ORDER BY degree DESC LIMIT ?""",
                (clean_q, clean_q, limit)
            )
            rows = await cursor.fetchall()
            nodes = []
            for r in rows:
                nodes.append(Node(
                    id=r["id"],
                    name=r["name"],
                    type=r["type"],
                    description=r["description"],
                    degree=r["degree"] or 0,
                    community_id=r["community_id"],
                    community_levels=json.loads(r["community_levels"] or "{}"),
                    provenance_chunk_ids=json.loads(r["provenance"] or "[]")
                ))
            return nodes

    async def get_all_edges(self, include_deleted: bool = False) -> List[Edge]:
        """Fetch all edges (by default excluding edges connected to soft-deleted nodes or with 0 active provenance)."""
        await self.initialize_schema()
        deleted_chunk_ids = set() if include_deleted else set(await self.get_soft_deleted_chunk_ids())
        active_node_ids = None
        if not include_deleted:
            active_nodes = await self.get_all_nodes(include_deleted=False)
            active_node_ids = {n.id for n in active_nodes}

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM edges")
            rows = await cursor.fetchall()
            edges = []
            for r in rows:
                src = r["source"]
                tgt = r["target"]
                if not include_deleted and active_node_ids is not None:
                    if src not in active_node_ids or tgt not in active_node_ids:
                        continue

                prov = json.loads(r["provenance"] or "[]")
                if not include_deleted and deleted_chunk_ids and prov:
                    active_prov = [cid for cid in prov if cid not in deleted_chunk_ids]
                    if not active_prov:
                        continue
                    prov = active_prov

                edges.append(Edge(
                    id=r["id"],
                    source=src,
                    target=tgt,
                    predicate=r["predicate"],
                    description=r["description"],
                    weight=r["weight"] or 1.0,
                    confidence=r["confidence"] or 1.0,
                    provenance_chunk_ids=prov
                ))
            return edges

    async def get_communities(self, level: Optional[int] = None, include_deleted: bool = False) -> List[Community]:
        """Fetch communities filtered optionally by level and excluding inactive nodes."""
        await self.initialize_schema()
        active_node_ids = None
        if not include_deleted:
            active_nodes = await self.get_all_nodes(include_deleted=False)
            active_node_ids = {n.id for n in active_nodes}

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if level is not None:
                cursor = await db.execute("SELECT * FROM communities WHERE level = ?", (level,))
            else:
                cursor = await db.execute("SELECT * FROM communities")
            rows = await cursor.fetchall()
            comms = []
            for r in rows:
                node_ids = json.loads(r["node_ids"] or "[]")
                if not include_deleted and active_node_ids is not None:
                    node_ids = [nid for nid in node_ids if nid in active_node_ids]
                    if not node_ids:
                        continue

                comms.append(Community(
                    id=r["id"],
                    level=r["level"],
                    parent_id=r["parent_id"],
                    name=r["name"],
                    node_ids=node_ids,
                    summary=r["summary"],
                    findings=json.loads(r["findings"] or "[]"),
                    themes=json.loads(r["themes"] or "[]"),
                    confidence=r["confidence"] or 1.0
                ))
            return comms

    async def purge_notes_atomic(self, note_ids: List[str]) -> Dict[str, Any]:
        """
        Permanently cascades deletion of notes, associated chunks, FTS5 rows,
        prunes orphaned nodes/edges with 0 remaining provenance,
        recomputes degree centrality on surviving nodes,
        and updates community memberships within an atomic transaction.
        """
        if not note_ids:
            return {
                "deleted_notes_count": 0,
                "deleted_chunk_ids": [],
                "deleted_nodes_count": 0,
                "deleted_edges_count": 0,
                "pruned_communities_count": 0,
            }
        await self.initialize_schema()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("BEGIN IMMEDIATE")
            try:
                placeholders = ",".join("?" for _ in note_ids)
                db.row_factory = aiosqlite.Row

                # 1. Fetch all chunk IDs associated with these notes
                cursor = await db.execute(
                    f"SELECT id FROM chunks WHERE note_id IN ({placeholders})",
                    note_ids
                )
                chunk_rows = await cursor.fetchall()
                target_chunk_ids = {r["id"] for r in chunk_rows}

                # 2. Delete FTS5 entries
                await db.execute(
                    f"DELETE FROM chunks_fts WHERE note_id IN ({placeholders})",
                    note_ids
                )
                if target_chunk_ids:
                    chunk_placeholders = ",".join("?" for _ in target_chunk_ids)
                    await db.execute(
                        f"DELETE FROM chunks_fts WHERE chunk_id IN ({chunk_placeholders})",
                        list(target_chunk_ids)
                    )

                # 3. Delete chunks
                await db.execute(
                    f"DELETE FROM chunks WHERE note_id IN ({placeholders})",
                    note_ids
                )

                # 4. Delete notes
                note_cursor = await db.execute(
                    f"DELETE FROM notes WHERE id IN ({placeholders})",
                    note_ids
                )
                deleted_notes_count = note_cursor.rowcount

                # 5. Process nodes: prune nodes with 0 remaining provenance
                cursor = await db.execute("SELECT id, provenance FROM nodes")
                all_nodes = await cursor.fetchall()
                deleted_node_ids = set()
                for nr in all_nodes:
                    nid = nr["id"]
                    raw_prov = json.loads(nr["provenance"] or "[]")
                    if raw_prov:
                        intersect = [cid for cid in raw_prov if cid in target_chunk_ids]
                        if intersect:
                            surviving_prov = [cid for cid in raw_prov if cid not in target_chunk_ids]
                            if not surviving_prov:
                                deleted_node_ids.add(nid)
                            else:
                                await db.execute(
                                    "UPDATE nodes SET provenance = ? WHERE id = ?",
                                    (json.dumps(surviving_prov), nid)
                                )

                if deleted_node_ids:
                    dn_placeholders = ",".join("?" for _ in deleted_node_ids)
                    await db.execute(
                        f"DELETE FROM nodes WHERE id IN ({dn_placeholders})",
                        list(deleted_node_ids)
                    )

                # 6. Process edges: delete edges incident to deleted nodes OR
                # edges whose provenance chunks are completely deleted; update provenance for surviving edges
                cursor = await db.execute("SELECT id, source, target, provenance FROM edges")
                all_edges = await cursor.fetchall()
                deleted_edge_ids = set()
                for er in all_edges:
                    eid = er["id"]
                    src = er["source"]
                    tgt = er["target"]
                    if src in deleted_node_ids or tgt in deleted_node_ids:
                        deleted_edge_ids.add(eid)
                        continue

                    raw_prov = json.loads(er["provenance"] or "[]")
                    if raw_prov:
                        intersect = [cid for cid in raw_prov if cid in target_chunk_ids]
                        if intersect:
                            surviving_prov = [cid for cid in raw_prov if cid not in target_chunk_ids]
                            if not surviving_prov:
                                deleted_edge_ids.add(eid)
                            else:
                                await db.execute(
                                    "UPDATE edges SET provenance = ? WHERE id = ?",
                                    (json.dumps(surviving_prov), eid)
                                )

                if deleted_edge_ids:
                    de_placeholders = ",".join("?" for _ in deleted_edge_ids)
                    await db.execute(
                        f"DELETE FROM edges WHERE id IN ({de_placeholders})",
                        list(deleted_edge_ids)
                    )

                # 7. Recompute degree centrality on surviving nodes
                await db.execute(
                    """UPDATE nodes SET degree = (
                        SELECT COUNT(*) FROM edges WHERE edges.source = nodes.id OR edges.target = nodes.id
                    )"""
                )

                # 8. Update or prune communities
                cursor = await db.execute("SELECT id, node_ids FROM communities")
                all_comms = await cursor.fetchall()
                pruned_comm_ids = []
                for cr in all_comms:
                    cid = cr["id"]
                    c_nodes = json.loads(cr["node_ids"] or "[]")
                    surviving_c_nodes = [nid for nid in c_nodes if nid not in deleted_node_ids]
                    if not surviving_c_nodes:
                        pruned_comm_ids.append(cid)
                    elif len(surviving_c_nodes) != len(c_nodes):
                        await db.execute(
                            "UPDATE communities SET node_ids = ? WHERE id = ?",
                            (json.dumps(surviving_c_nodes), cid)
                        )

                if pruned_comm_ids:
                    comm_placeholders = ",".join("?" for _ in pruned_comm_ids)
                    await db.execute(
                        f"DELETE FROM communities WHERE id IN ({comm_placeholders})",
                        pruned_comm_ids
                    )
                    await db.execute(
                        f"DELETE FROM communities_fts WHERE community_id IN ({comm_placeholders})",
                        pruned_comm_ids
                    )

                await db.commit()

                return {
                    "deleted_notes_count": deleted_notes_count,
                    "deleted_chunk_ids": list(target_chunk_ids),
                    "deleted_nodes_count": len(deleted_node_ids),
                    "deleted_edges_count": len(deleted_edge_ids),
                    "pruned_communities_count": len(pruned_comm_ids),
                }
            except Exception:
                await db.rollback()
                raise

    async def save_meta(self, key: str, value: Any):
        """Upsert a metadata key/value pair (used for global summaries, etc.)."""
        await self.initialize_schema()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO graph_meta (key, value, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(key) DO UPDATE SET value = excluded.value,
                                                  updated_at = CURRENT_TIMESTAMP""",
                (key, json.dumps(value))
            )
            await db.commit()

    async def get_meta(self, key: str) -> Optional[Any]:
        """Fetch a metadata value by key; returns None if absent."""
        await self.initialize_schema()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT value FROM graph_meta WHERE key = ?", (key,))
            row = await cursor.fetchone()
            if not row:
                return None
            return json.loads(row["value"])

    async def get_edges_connected_to(self, node_ids: List[str]) -> List[Edge]:
        """Fetch all edges where source or target is in node_ids."""
        if not node_ids:
            return []
        await self.initialize_schema()
        placeholders = ",".join("?" for _ in node_ids)
        query = f"SELECT * FROM edges WHERE source IN ({placeholders}) OR target IN ({placeholders})"
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, node_ids + node_ids)
            rows = await cursor.fetchall()
            return [
                Edge(
                    id=r["id"],
                    source=r["source"],
                    target=r["target"],
                    predicate=r["predicate"],
                    description=r["description"],
                    weight=r["weight"] or 1.0,
                    confidence=r["confidence"] or 1.0,
                    provenance_chunk_ids=json.loads(r["provenance"] or "[]")
                )
                for r in rows
            ]

    async def get_nodes_by_ids(self, node_ids: List[str]) -> List[Node]:
        """Fetch nodes matching a list of IDs."""
        if not node_ids:
            return []
        await self.initialize_schema()
        placeholders = ",".join("?" for _ in node_ids)
        query = f"SELECT * FROM nodes WHERE id IN ({placeholders})"
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, node_ids)
            rows = await cursor.fetchall()
            return [
                Node(
                    id=r["id"],
                    name=r["name"],
                    type=r["type"],
                    description=r["description"],
                    degree=r["degree"] or 0,
                    community_id=r["community_id"],
                    community_levels=json.loads(r["community_levels"] or "{}"),
                    provenance_chunk_ids=json.loads(r["provenance"] or "[]"),
                    layout_x=r["layout_x"] if "layout_x" in r.keys() else None,
                    layout_y=r["layout_y"] if "layout_y" in r.keys() else None
                )
                for r in rows
            ]
