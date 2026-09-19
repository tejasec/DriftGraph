"""driftgraph/serve/routes/notes.py

Note management API routes:
- Full CRUD for Markdown notes
- Soft-delete and instant undo
- Permanent cascade purge
- Bulk delete and bulk undo
- Empty trash
- Rich metadata (word counts, tags, source types, previews)
- Template listing and instantiation
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import aiosqlite
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import frontmatter
import structlog

from driftgraph.config import config
from driftgraph.sources.templates import list_templates, get_template, render_template
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.graph.models import Node
from driftgraph.graph.vector_store import VectorIndex
from driftgraph.classifier.rule_based import DocumentClassifier
from driftgraph.serve.routes.query import invalidate_query_engine

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/notes", tags=["Notes"])

_classifier = DocumentClassifier()


class NoteSummary(BaseModel):
    id: str
    filename: str
    title: str
    date: str
    source_type: str
    tags: List[str]
    word_count: int
    char_count: int
    preview: str
    top_category: Optional[str] = None
    connected_entities_count: int = 0
    deleted_at: Optional[str] = None


class NoteDetail(BaseModel):
    id: str
    filename: str
    title: str
    date: str
    source_type: str
    tags: List[str]
    content: str
    metadata: Dict[str, Any]
    word_count: int
    char_count: int
    top_category: Optional[str] = None
    connected_entities: List[Dict[str, Any]] = Field(default_factory=list)
    deleted_at: Optional[str] = None


class NoteCreateRequest(BaseModel):
    title: Optional[str] = "Untitled Note"
    content: Optional[str] = ""
    tags: Optional[List[str]] = Field(default_factory=list)
    source_type: Optional[str] = "markdown"


class NoteUpdateRequest(BaseModel):
    content: str
    title: Optional[str] = None
    tags: Optional[List[str]] = None


class TemplateInstantiateRequest(BaseModel):
    values: Dict[str, str] = Field(default_factory=dict)
    custom_title: Optional[str] = None


class BulkDeleteRequest(BaseModel):
    note_ids: List[str]
    permanent: bool = False


class BulkUndoRequest(BaseModel):
    note_ids: List[str]


def _get_notes_dir() -> Path:
    p = Path(config.paths.notes_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _find_note_file(note_id: str) -> Optional[Path]:
    notes_dir = _get_notes_dir()
    for f in notes_dir.glob("*.md"):
        if f.stem.lower().replace(" ", "_") == note_id.lower() or f.name.lower() == note_id.lower():
            return f
    return None


def _evict_vectors_for_chunks(chunk_ids: List[str]) -> None:
    if not chunk_ids:
        return
    try:
        vec_index = VectorIndex(dimension=384, index_path=config.database.vector_index_path)
        if vec_index.load():
            vec_index.remove_ids(chunk_ids)
            logger.info("vector_index_purged_ids", count=len(chunk_ids))
    except Exception as e:
        logger.warning("failed_to_evict_vectors", error=str(e))


@router.get("", response_model=List[NoteSummary])
async def list_notes(include_deleted: bool = Query(False, description="Include soft-deleted notes")):
    """List notes in the repository with summaries, tags, and stats."""
    notes_dir = _get_notes_dir()
    files = list(notes_dir.glob("*.md"))

    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    nodes = await storage.get_all_nodes(include_deleted=include_deleted)
    soft_deleted_ids = set(await storage.get_soft_deleted_note_ids())

    # Map source_id/provenance to count of nodes
    source_node_counts: Dict[str, int] = {}
    for n in nodes:
        src = getattr(n, "source_id", None)
        if src:
            source_node_counts[src] = source_node_counts.get(src, 0) + 1
        for cid in getattr(n, "provenance_chunk_ids", []):
            stem = cid.rsplit("_chunk_", 1)[0] if "_chunk_" in cid else cid
            source_node_counts[stem] = source_node_counts.get(stem, 0) + 1

    summaries: List[NoteSummary] = []
    for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            note_id = f.stem.lower().replace(" ", "_")
            is_deleted = (note_id in soft_deleted_ids) or (f.name in soft_deleted_ids) or (f.stem in soft_deleted_ids)

            if is_deleted and not include_deleted:
                continue

            post = frontmatter.load(str(f))
            meta = post.metadata or {}
            content = post.content.strip()

            title = str(meta.get("title") or f.stem.replace("_", " ").title())
            date_str = str(meta.get("date") or date.fromtimestamp(f.stat().st_mtime).isoformat())
            source_type = str(meta.get("source_type") or "markdown")
            tags = meta.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            words = len(content.split())
            chars = len(content)
            preview = re.sub(r"\s+", " ", content[:240]).strip()
            if len(content) > 240:
                preview += "..."

            ent_count = source_node_counts.get(note_id, 0) or source_node_counts.get(f.name, 0)

            top_cat = meta.get("category")
            if not top_cat and tags:
                for t in tags:
                    if t.lower() in ["legal", "financial", "technical", "research", "academic", "medical", "meeting"]:
                        top_cat = t.title()
                        break

            summaries.append(NoteSummary(
                id=note_id,
                filename=f.name,
                title=title,
                date=date_str,
                source_type=source_type,
                tags=tags,
                word_count=words,
                char_count=chars,
                preview=preview,
                top_category=top_cat,
                connected_entities_count=ent_count,
                deleted_at="deleted" if is_deleted else None
            ))
        except Exception:
            continue

    return summaries


@router.post("", status_code=201)
async def create_note(req: NoteCreateRequest):
    """
    Create a new note with atomic SQLite persistence and FTS5 synchronization.
    """
    notes_dir = _get_notes_dir()
    title = (req.title or "").strip() or "Untitled Note"
    content = req.content if req.content is not None else ""
    tags = req.tags or []
    source_type = req.source_type or "markdown"

    today_iso = date.today().isoformat()
    now_iso = datetime.utcnow().isoformat() + "Z"

    # Generate unique filename and note id
    clean_stem = re.sub(r"[^\w\s-]", "", title).strip().lower()
    clean_stem = re.sub(r"\s+", "_", clean_stem)[:40] or "note"
    filename = f"{clean_stem}_{today_iso}.md"
    file_path = notes_dir / filename
    if file_path.exists():
        filename = f"{clean_stem}_{int(time.time())}.md"
        file_path = notes_dir / filename

    note_id = file_path.stem.lower().replace(" ", "_")

    fm_content = (
        "---\n"
        f"title: \"{title}\"\n"
        f"date: {today_iso}\n"
        f"source_type: {source_type}\n"
        f"tags: {json.dumps(tags)}\n"
        "---\n\n"
        f"{content}\n"
    )

    await asyncio.to_thread(file_path.write_text, fm_content, encoding="utf-8")

    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    await storage.initialize_schema()

    chunk_id = f"{note_id}_chunk_0"
    chunk_text = content.strip() or title

    async with aiosqlite.connect(storage.db_path) as db:
        await db.execute(
            """INSERT OR REPLACE INTO notes (id, title, source_file, source_type, date, tags, raw_content, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                note_id,
                title,
                str(file_path),
                source_type,
                today_iso,
                json.dumps(tags),
                content,
                now_iso
            )
        )
        await db.execute(
            """INSERT OR REPLACE INTO chunks (id, note_id, source_file, chunk_index, text, start_char, end_char, token_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                chunk_id,
                note_id,
                str(file_path),
                0,
                chunk_text,
                0,
                len(chunk_text),
                len(chunk_text.split())
            )
        )
        await db.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (chunk_id,))
        await db.execute(
            """INSERT INTO chunks_fts (chunk_id, note_id, text, title)
               VALUES (?, ?, ?, ?)""",
            (chunk_id, note_id, chunk_text, title)
        )
        await db.commit()

    invalidate_query_engine()

    words = len(content.split())
    chars = len(content)
    preview = re.sub(r"\s+", " ", content[:240]).strip()

    return {
        "id": note_id,
        "filename": filename,
        "title": title,
        "content": content,
        "date": today_iso,
        "created_at": now_iso,
        "source_type": source_type,
        "tags": tags,
        "word_count": words,
        "char_count": chars,
        "preview": preview,
        "top_category": None,
        "connected_entities": [],
        "connected_entities_count": 0,
        "message": f"Created note {note_id}"
    }


@router.get("/templates")
async def get_note_templates():
    """List all available note templates."""
    return list_templates()


@router.post("/templates/{template_id}/instantiate")
async def instantiate_note_template(template_id: str, req: TemplateInstantiateRequest):
    """Create a new note populated from a selected template."""
    tpl = get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found.")

    values = dict(req.values)
    today_iso = date.today().isoformat()
    values.setdefault("date", today_iso)
    title = req.custom_title or values.get("title") or tpl.name
    values["title"] = title

    rendered_markdown = render_template(template_id, values)

    notes_dir = _get_notes_dir()
    clean_stem = re.sub(r"[^\w\s-]", "", title).strip().lower()
    clean_stem = re.sub(r"\s+", "_", clean_stem)[:40] or "note"
    filename = f"{clean_stem}_{today_iso}.md"
    file_path = notes_dir / filename

    fm_content = (
        "---\n"
        f"title: \"{title}\"\n"
        f"date: {today_iso}\n"
        f"source_type: template\n"
        f"tags: {tpl.tags}\n"
        "---\n\n"
        f"{rendered_markdown}\n"
    )

    await asyncio.to_thread(file_path.write_text, fm_content, encoding="utf-8")
    note_id = file_path.stem.lower().replace(" ", "_")

    return {
        "id": note_id,
        "filename": filename,
        "title": title,
        "template_used": template_id,
        "message": f"Instantiated template '{tpl.name}' into {filename}"
    }


@router.get("/{note_id}", response_model=NoteDetail)
async def get_note_detail(note_id: str, include_deleted: bool = Query(False)):
    """Retrieve full content and connected graph entities for a note."""
    target_file = _find_note_file(note_id)
    if not target_file:
        raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")

    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    soft_deleted_ids = set(await storage.get_soft_deleted_note_ids())
    clean_id = target_file.stem.lower().replace(" ", "_")
    is_deleted = (note_id in soft_deleted_ids) or (clean_id in soft_deleted_ids) or (target_file.name in soft_deleted_ids)

    if is_deleted and not include_deleted:
        raise HTTPException(status_code=404, detail=f"Note is in trash: {note_id}")

    post = frontmatter.load(str(target_file))
    meta = post.metadata or {}
    content = post.content

    nodes = await storage.get_all_nodes(include_deleted=include_deleted)

    def _is_node_connected(n: Node) -> bool:
        if getattr(n, "source_id", None) in (note_id, clean_id, target_file.name, target_file.stem):
            return True
        for cid in getattr(n, "provenance_chunk_ids", []):
            stem = cid.rsplit("_chunk_", 1)[0] if "_chunk_" in cid else cid
            if stem in (note_id, clean_id, target_file.name, target_file.stem):
                return True
        return False

    connected = [
        {"id": n.id, "name": n.name, "type": n.type, "description": n.description}
        for n in nodes
        if _is_node_connected(n)
    ]

    title = str(meta.get("title") or target_file.stem.replace("_", " ").title())
    date_str = str(meta.get("date") or date.fromtimestamp(target_file.stat().st_mtime).isoformat())
    source_type = str(meta.get("source_type") or "markdown")
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    cls_res = _classifier.classify_text(content, filename=target_file.name)

    return NoteDetail(
        id=clean_id,
        filename=target_file.name,
        title=title,
        date=date_str,
        source_type=source_type,
        tags=tags,
        content=content,
        metadata=meta,
        word_count=len(content.split()),
        char_count=len(content),
        top_category=cls_res.top_category,
        connected_entities=connected,
        deleted_at="deleted" if is_deleted else None
    )


@router.put("/{note_id}")
async def update_note(note_id: str, req: NoteUpdateRequest):
    """Update a note's markdown content and frontmatter, syncing SQLite and FTS5."""
    target_file = _find_note_file(note_id)
    if not target_file:
        raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")

    post = frontmatter.load(str(target_file))
    meta = post.metadata or {}
    if req.title:
        meta["title"] = req.title
    if req.tags is not None:
        meta["tags"] = req.tags

    new_content = req.content
    post.content = new_content
    post.metadata = meta

    serialized = frontmatter.dumps(post)
    await asyncio.to_thread(target_file.write_text, serialized, encoding="utf-8")

    clean_id = target_file.stem.lower().replace(" ", "_")
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    await storage.initialize_schema()

    chunk_id = f"{clean_id}_chunk_0"
    chunk_text = new_content.strip() or (req.title or target_file.stem)
    tags_json = json.dumps(meta.get("tags") or [])

    async with aiosqlite.connect(storage.db_path) as db:
        await db.execute(
            """UPDATE notes SET raw_content = ?, title = coalesce(?, title), tags = ?
               WHERE id = ? OR source_file = ?""",
            (new_content, req.title, tags_json, clean_id, str(target_file))
        )
        await db.execute(
            """UPDATE chunks SET text = ?, token_count = ?
               WHERE id = ? OR note_id = ?""",
            (chunk_text, len(chunk_text.split()), chunk_id, clean_id)
        )
        await db.execute("DELETE FROM chunks_fts WHERE chunk_id = ? OR note_id = ?", (chunk_id, clean_id))
        await db.execute(
            """INSERT INTO chunks_fts (chunk_id, note_id, text, title)
               VALUES (?, ?, ?, ?)""",
            (chunk_id, clean_id, chunk_text, req.title or meta.get("title") or clean_id)
        )
        await db.commit()

    invalidate_query_engine()

    return {"status": "success", "message": f"Updated note {target_file.name}"}


@router.delete("/{note_id}")
async def delete_note(note_id: str, permanent: bool = Query(False)):
    """
    Delete a note.
    By default (permanent=False), performs soft-delete.
    When permanent=True, executes atomic cascade purge, removes vector embeddings and unlinks markdown file.
    """
    target_file = _find_note_file(note_id)
    clean_id = target_file.stem.lower().replace(" ", "_") if target_file else note_id
    storage = SQLiteStorage(db_path=config.database.sqlite_path)

    if not permanent:
        # Soft delete in SQLite
        # Include possible variations (note_id, clean_id)
        ids_to_mark = list({note_id, clean_id})
        count = await storage.soft_delete_notes(ids_to_mark)
        invalidate_query_engine()
        return {
            "status": "success",
            "action": "soft_delete",
            "id": clean_id,
            "message": f"Soft-deleted note {clean_id}"
        }

    # Permanent cascade purge
    ids_to_purge = list({note_id, clean_id})
    stats = await storage.purge_notes_atomic(ids_to_purge)

    # Evict vector IDs from FAISS index
    del_chunks = stats.get("deleted_chunk_ids", [])
    if del_chunks:
        _evict_vectors_for_chunks(del_chunks)

    # Invalidate query engine cache
    invalidate_query_engine()

    # Remove markdown file from disk
    if target_file and target_file.exists():
        await asyncio.to_thread(target_file.unlink)

    return {
        "status": "success",
        "action": "permanent_purge",
        "id": clean_id,
        "stats": stats,
        "message": f"Permanently purged note {clean_id}"
    }


@router.post("/bulk-delete")
async def bulk_delete_notes(req: BulkDeleteRequest):
    """
    Bulk delete notes: soft-delete or permanent purge.
    """
    if not req.note_ids:
        return {"status": "success", "count": 0, "message": "No note IDs provided"}

    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    all_target_ids = set()
    files_to_delete: List[Path] = []

    for nid in req.note_ids:
        all_target_ids.add(nid)
        f = _find_note_file(nid)
        if f:
            all_target_ids.add(f.stem.lower().replace(" ", "_"))
            files_to_delete.append(f)

    if not req.permanent:
        count = await storage.soft_delete_notes(list(all_target_ids))
        invalidate_query_engine()
        return {
            "status": "success",
            "action": "bulk_soft_delete",
            "count": len(req.note_ids),
            "note_ids": req.note_ids,
            "message": f"Soft-deleted {len(req.note_ids)} notes"
        }

    # Permanent purge
    stats = await storage.purge_notes_atomic(list(all_target_ids))
    del_chunks = stats.get("deleted_chunk_ids", [])
    if del_chunks:
        _evict_vectors_for_chunks(del_chunks)

    invalidate_query_engine()

    for f in files_to_delete:
        if f.exists():
            await asyncio.to_thread(f.unlink)

    return {
        "status": "success",
        "action": "bulk_permanent_purge",
        "count": stats["deleted_notes_count"],
        "stats": stats,
        "note_ids": req.note_ids,
        "message": f"Permanently purged {len(req.note_ids)} notes"
    }


@router.post("/{note_id}/undo")
async def undo_delete_note(note_id: str):
    """Restore a soft-deleted note."""
    target_file = _find_note_file(note_id)
    clean_id = target_file.stem.lower().replace(" ", "_") if target_file else note_id
    storage = SQLiteStorage(db_path=config.database.sqlite_path)

    ids_to_restore = list({note_id, clean_id})
    count = await storage.restore_notes(ids_to_restore)
    invalidate_query_engine()

    return {
        "status": "success",
        "action": "undo",
        "id": clean_id,
        "restored_count": count,
        "message": f"Restored note {clean_id}"
    }


@router.post("/bulk-undo")
async def bulk_undo_notes(req: BulkUndoRequest):
    """Bulk restore soft-deleted notes."""
    if not req.note_ids:
        return {"status": "success", "count": 0, "message": "No note IDs provided"}

    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    all_target_ids = set()
    for nid in req.note_ids:
        all_target_ids.add(nid)
        f = _find_note_file(nid)
        if f:
            all_target_ids.add(f.stem.lower().replace(" ", "_"))

    count = await storage.restore_notes(list(all_target_ids))
    invalidate_query_engine()

    return {
        "status": "success",
        "action": "bulk_undo",
        "restored_count": count,
        "note_ids": req.note_ids,
        "message": f"Restored {len(req.note_ids)} notes"
    }


@router.post("/trash/empty")
async def empty_trash():
    """Permanently purge all soft-deleted notes and cascade cleanup."""
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    soft_deleted_ids = await storage.get_soft_deleted_note_ids()

    if not soft_deleted_ids:
        return {
            "status": "success",
            "action": "trash_emptied",
            "count": 0,
            "message": "Trash is already empty"
        }

    stats = await storage.purge_notes_atomic(soft_deleted_ids)
    del_chunks = stats.get("deleted_chunk_ids", [])
    if del_chunks:
        _evict_vectors_for_chunks(del_chunks)

    invalidate_query_engine()

    for nid in soft_deleted_ids:
        f = _find_note_file(nid)
        if f and f.exists():
            await asyncio.to_thread(f.unlink)

    return {
        "status": "success",
        "action": "trash_emptied",
        "count": stats["deleted_notes_count"],
        "stats": stats,
        "message": f"Permanently emptied trash ({stats['deleted_notes_count']} notes)"
    }
