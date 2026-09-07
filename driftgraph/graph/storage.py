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
            await db.executescript(schema_sql)
            await db.commit()
        logger.info("sqlite_schema_initialized", db_path=str(self.db_path))

    async def save_notes_and_chunks(self, notes: List[Note], chunks: List[Chunk]):
        """Persist Notes and Chunks into relational tables and FTS index."""
        async with aiosqlite.connect(self.db_path) as db:
            # Save notes
            for note in notes:
                await db.execute(
                    """INSERT OR REPLACE INTO notes (id, title, source_file, date, tags, raw_content)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        note.id,
                        note.metadata.title,
                        note.metadata.source_file,
                        note.metadata.date,
                        json.dumps(note.metadata.tags),
                        note.raw_content
                    )
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
                    """INSERT OR REPLACE INTO nodes (id, name, type, description, degree, community_id, community_levels, provenance)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        node.id,
                        node.name,
                        node.type,
                        node.description,
                        node.degree,
                        node.community_id,
                        json.dumps(node.community_levels),
                        json.dumps(node.provenance_chunk_ids)
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
        """Search notes chunks using SQLite FTS5 BM25 match."""
        # Sanitize query for FTS5 syntax
        clean_q = "".join(c for c in query if c.isalnum() or c.isspace()).strip()
        if not clean_q:
            return []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT chunk_id, note_id, text, title, rank
                   FROM chunks_fts
                   WHERE chunks_fts MATCH ?
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

    async def get_all_notes(self) -> List[Dict[str, Any]]:
        """Fetch all notes with their metadata."""
        await self.initialize_schema()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM notes")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_all_nodes(self) -> List[Node]:
        """Fetch all nodes."""
        await self.initialize_schema()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM nodes")
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

    async def get_all_edges(self) -> List[Edge]:
        """Fetch all edges."""
        await self.initialize_schema()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM edges")
            rows = await cursor.fetchall()
            edges = []
            for r in rows:
                edges.append(Edge(
                    id=r["id"],
                    source=r["source"],
                    target=r["target"],
                    predicate=r["predicate"],
                    description=r["description"],
                    weight=r["weight"] or 1.0,
                    confidence=r["confidence"] or 1.0,
                    provenance_chunk_ids=json.loads(r["provenance"] or "[]")
                ))
            return edges

    async def get_communities(self, level: Optional[int] = None) -> List[Community]:
        """Fetch communities filtered optionally by level."""
        await self.initialize_schema()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if level is not None:
                cursor = await db.execute("SELECT * FROM communities WHERE level = ?", (level,))
            else:
                cursor = await db.execute("SELECT * FROM communities")
            rows = await cursor.fetchall()
            comms = []
            for r in rows:
                comms.append(Community(
                    id=r["id"],
                    level=r["level"],
                    parent_id=r["parent_id"],
                    name=r["name"],
                    node_ids=json.loads(r["node_ids"] or "[]"),
                    summary=r["summary"],
                    findings=json.loads(r["findings"] or "[]"),
                    themes=json.loads(r["themes"] or "[]"),
                    confidence=r["confidence"] or 1.0
                ))
            return comms
