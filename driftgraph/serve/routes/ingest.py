"""
Ingestion API route: trigger pipeline on notes directory or uploaded text.
"""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from driftgraph.config import config
from driftgraph.ingest import parse_markdown_directory, chunk_notes
from driftgraph.embed import SBERTEmbedder
from driftgraph.extract import OllamaExtractionClient
from driftgraph.graph import KnowledgeGraphBuilder, SQLiteStorage, VectorIndex
from driftgraph.summarize import CommunitySummarizer

router = APIRouter(prefix="/api/ingest", tags=["Ingest"])


class IngestRequest(BaseModel):
    notes_dir: Optional[str] = None
    rebuild: bool = True


class IngestResponse(BaseModel):
    status: str
    notes_count: int
    chunks_count: int
    nodes_count: int
    edges_count: int
    communities_count: int
    message: str


@router.post("", response_model=IngestResponse)
async def trigger_ingest(req: IngestRequest):
    """Trigger note parsing, extraction, embedding, and graph generation."""
    target_dir = req.notes_dir or config.paths.notes_dir
    notes_path = Path(target_dir)

    if not notes_path.exists():
        raise HTTPException(status_code=404, detail=f"Notes directory not found: {target_dir}")

    # 1. Ingestion & Chunking
    notes = await parse_markdown_directory(notes_path)
    if not notes:
        return IngestResponse(
            status="empty",
            notes_count=0,
            chunks_count=0,
            nodes_count=0,
            edges_count=0,
            communities_count=0,
            message="No markdown notes found in directory."
        )

    chunks = chunk_notes(notes)

    # 2. Embeddings
    embedder = SBERTEmbedder()
    chunk_texts = [c.text for c in chunks]
    chunk_vectors = embedder.embed_texts(chunk_texts)

    # Vector Index
    vec_index = VectorIndex(dimension=embedder.dimension, index_path=config.database.vector_index_path)
    chunk_ids = [c.id for c in chunks]
    vec_index.add(chunk_ids, chunk_vectors)
    vec_index.save()

    # 3. Extraction
    extractor = OllamaExtractionClient()
    extractions = await extractor.extract_batch(chunks)
    await extractor.close()

    # 4. Knowledge Graph Assembly & Communities
    builder = KnowledgeGraphBuilder(embedder=embedder)
    nodes, edges, communities = builder.build_from_extractions(extractions)

    # 5. Summarization (Hierarchical Map-Reduce)
    summarizer = CommunitySummarizer()
    await summarizer.summarize_all(communities, nodes, edges)
    await summarizer.close()

    # 6. SQLite Persistence
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    await storage.initialize_schema()
    await storage.save_notes_and_chunks(notes, chunks)
    await storage.save_graph(nodes, edges, communities)

    return IngestResponse(
        status="success",
        notes_count=len(notes),
        chunks_count=len(chunks),
        nodes_count=len(nodes),
        edges_count=len(edges),
        communities_count=len(communities),
        message="Knowledge graph successfully built and indexed."
    )
