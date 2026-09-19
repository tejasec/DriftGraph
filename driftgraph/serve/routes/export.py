"""driftgraph/serve/routes/export.py

Export API route:
- Graph export in JSON, RDF Turtle, JSON-LD, CSV, and Markdown digest format
- Embedding vector export for downstream ML pipelines
- Notes repository export in JSON or Markdown format
"""

import io
import csv
import json
from pathlib import Path
from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, Query, Response

from driftgraph.config import config
from driftgraph.graph.storage import SQLiteStorage
from driftgraph.graph.builder import KnowledgeGraphBuilder
from driftgraph.graph.vector_store import VectorIndex

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.get("")
async def export_graph(format: Literal["json", "ttl", "jsonld", "csv", "markdown"] = Query("json")):
    """Export the knowledge graph in JSON, RDF Turtle, JSON-LD, CSV, or Markdown digest."""
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    nodes = await storage.get_all_nodes()
    edges = await storage.get_all_edges()
    comms = await storage.get_communities()
    builder = KnowledgeGraphBuilder()

    if format == "ttl":
        ttl_content = builder.to_rdf_turtle(nodes, edges)
        return Response(
            content=ttl_content,
            media_type="text/turtle",
            headers={"Content-Disposition": "attachment; filename=driftgraph.ttl"}
        )

    elif format == "jsonld":
        jsonld_doc = {
            "@context": {
                "name": "http://schema.org/name",
                "description": "http://schema.org/description",
                "dg": "http://driftgraph.org/"
            },
            "@graph": [
                {"@id": f"dg:{n.id}", "name": n.name, "type": n.type, "description": n.description}
                for n in nodes
            ]
        }
        return Response(
            content=json.dumps(jsonld_doc, indent=2),
            media_type="application/ld+json",
            headers={"Content-Disposition": "attachment; filename=driftgraph.jsonld"}
        )

    elif format == "csv":
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["record_type", "id", "source_or_name", "target_or_type", "relation_or_desc", "weight"])
        for n in nodes:
            writer.writerow(["node", n.id, n.name, n.type, n.description or "", "1.0"])
        for e in edges:
            rel = getattr(e, "predicate", getattr(e, "type", "RELATED"))
            writer.writerow(["edge", e.id, e.source, e.target, rel, str(e.weight)])
        return Response(
            content=out.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=driftgraph.csv"}
        )

    elif format == "markdown":
        lines = [
            "# DriftGraph Knowledge Graph Digest",
            f"Total Nodes: {len(nodes)} | Total Edges: {len(edges)} | Communities: {len(comms)}",
            "",
            "## Entities & Concepts",
        ]
        for n in nodes:
            lines.append(f"- **{n.name}** (`{n.type}`): {n.description or 'No description'}")

        lines.extend(["", "## Relationships"])
        for e in edges:
            rel = getattr(e, "predicate", getattr(e, "type", "RELATED"))
            lines.append(f"- {e.source} --[{rel} (w={e.weight})]--> {e.target}")

        if comms:
            lines.extend(["", "## Communities"])
            for c in comms:
                lines.append(f"### {c.name or f'Community {c.id}'} (Level {c.level})")
                if c.summary:
                    lines.append(f"{c.summary}\n")
                lines.append(f"**Member Nodes**: {', '.join(c.node_ids[:10])}\n")

        return Response(
            content="\n".join(lines),
            media_type="text/markdown",
            headers={"Content-Disposition": "attachment; filename=driftgraph_digest.md"}
        )

    else:
        elements = builder.to_cytoscape_elements(nodes, edges)
        return Response(
            content=json.dumps(elements, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=driftgraph.json"}
        )


@router.get("/embeddings")
async def export_embeddings():
    """Export FAISS vector embeddings and corresponding chunk IDs for downstream ML pipelines."""
    vec_index = VectorIndex(dimension=384, index_path=config.database.vector_index_path)
    loaded = vec_index.load()
    
    total = len(vec_index.index_to_id)
    chunk_ids = list(vec_index.id_to_index.keys())
    if total == 0 and vec_index.vectors is not None:
        total = vec_index.vectors.shape[0]

    payload = {
        "dimension": vec_index.dimension,
        "ntotal": total,
        "chunk_ids": chunk_ids,
        "index_type": "IndexFlatIP",
    }
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=driftgraph_embeddings_metadata.json"}
    )


@router.get("/notes")
async def export_notes(format: Literal["json", "markdown"] = Query("json")):
    """Export all markdown notes in repository as consolidated JSON or Markdown."""
    notes_dir = Path(config.paths.notes_dir)
    notes_files = list(notes_dir.glob("*.md"))

    if format == "markdown":
        contents = ["# Consolidated DriftGraph Notes\n"]
        for f in sorted(notes_files):
            text = f.read_text(encoding="utf-8")
            contents.append(f"<!-- NOTE: {f.name} -->\n{text}\n\n---\n")
        return Response(
            content="\n".join(contents),
            media_type="text/markdown",
            headers={"Content-Disposition": "attachment; filename=all_notes_consolidated.md"}
        )
    else:
        all_notes = []
        for f in sorted(notes_files):
            all_notes.append({
                "filename": f.name,
                "content": f.read_text(encoding="utf-8"),
                "size_bytes": f.stat().st_size,
            })
        return Response(
            content=json.dumps(all_notes, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=driftgraph_notes.json"}
        )
