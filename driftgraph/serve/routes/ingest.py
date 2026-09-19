"""
Ingestion API route: trigger pipeline on notes directory or uploaded text.
"""

import asyncio
import re
from datetime import date
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import asdict
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from driftgraph.config import config
from driftgraph.ingest import parse_markdown_directory, chunk_notes
from driftgraph.ingest.ocr import (
    ocr_document,
    pages_to_markdown,
    has_text_layer,
    get_installed_languages,
)
from driftgraph.ingest.ocr_engines import list_available_engines
from driftgraph.embed import SBERTEmbedder
from driftgraph.extract import OllamaExtractionClient, APIExtractionClient, get_extraction_client
from driftgraph.extract.models import ExtractionConfig
from driftgraph.graph import (
    KnowledgeGraphBuilder,
    SQLiteStorage,
    VectorIndex,
    EntityDeduplicator,
    CommunityDetector
)
from driftgraph.summarize import CommunitySummarizer
from driftgraph.summarize.models import SummaryConfig
from driftgraph.graph.layout import compute_forceatlas2_layout, apply_layout_to_nodes
from driftgraph.serve.routes.query import invalidate_query_engine

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


class NoteCreateRequest(BaseModel):
    content: str = Field(min_length=1)
    title: Optional[str] = None


class NoteCreateResponse(BaseModel):
    id: str
    filename: str
    title: str
    message: str


class OCRInfoResponse(BaseModel):
    engines: List[Dict[str, Any]]
    installed_languages: List[str]
    speed_modes: List[str] = ["fast", "balanced", "accurate"]
    default_engine: str = "tesseract"
    default_lang: str = "eng"
    default_speed_mode: str = "balanced"


class UploadDocumentResponse(BaseModel):
    id: str
    filename: str
    title: str
    markdown_content: str
    has_text_layer: bool
    pages_count: int
    mean_confidence: float
    source_type: str
    errors_count: int = 0
    tables_count: int = 0
    engine_used: str = "tesseract"
    speed_mode_used: str = "balanced"
    pages: List[Dict[str, Any]] = Field(default_factory=list)
    message: str


class BatchUploadResponse(BaseModel):
    total_documents: int
    successful_documents: int
    failed_documents: int
    total_pages: int
    mean_confidence: float
    total_errors_marked: int
    total_tables_detected: int
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    message: str


class OCRCorrectionRequest(BaseModel):
    filename: str
    old_text: str
    new_text: str


class WebScrapeRequest(BaseModel):
    url: str
    custom_title: Optional[str] = None
    auto_classify: bool = True


def _slugify(value: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", value).strip().lower()
    slug = re.sub(r"\s+", "_", slug)
    return slug or "note"


@router.post("/web")
async def ingest_web_page(req: WebScrapeRequest):
    """Scrape a web page and ingest it into the notes directory."""
    from driftgraph.sources.web_scraper import scrape_and_create_note
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty.")
    try:
        res = await scrape_and_create_note(req.url, custom_title=req.custom_title, auto_classify=req.auto_classify)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scrape web page: {str(e)}")



@router.get("/ocr/info", response_model=OCRInfoResponse)
async def get_ocr_info():
    """Return available OCR engines, installed languages, and speed mode profiles."""
    return OCRInfoResponse(
        engines=list_available_engines(),
        installed_languages=get_installed_languages(),
        speed_modes=["fast", "balanced", "accurate"],
        default_engine=getattr(config.ocr, "engine", "tesseract"),
        default_lang=getattr(config.ocr, "lang", "eng"),
        default_speed_mode=getattr(config.ocr, "speed_mode", "balanced"),
    )


@router.post("/notes", response_model=NoteCreateResponse)
async def create_note(req: NoteCreateRequest):
    """Persist a new markdown note so it can be ingested into the graph."""
    notes_dir = Path(config.paths.notes_dir)
    notes_dir.mkdir(parents=True, exist_ok=True)

    title = (req.title or "").strip() or _slugify(req.content.splitlines()[0] if req.content.splitlines() else "note")
    body = req.content.strip()
    if not body:
        raise HTTPException(status_code=400, detail="Note content cannot be empty.")

    stamp = "".join(c for c in title if c.isalnum() or c in "_ -")[:40].strip()
    stamp = stamp.replace(" ", "_") or "note"
    filename = f"{stamp}_{date.today().isoformat()}.md"
    file_path = notes_dir / filename

    markdown = (
        "---\n"
        f"title: {title.replace(chr(10), ' ')}\n"
        f"date: {date.today().isoformat()}\n"
        "tags: []\n"
        "---\n\n"
        f"{body}\n"
    )

    await asyncio.to_thread(file_path.write_text, markdown, encoding="utf-8")

    note_id = file_path.stem.lower().replace(" ", "_")
    return NoteCreateResponse(
        id=note_id,
        filename=filename,
        title=title,
        message=f"Note saved to {filename}. Rebuild the graph to index it."
    )


@router.post("/upload", response_model=UploadDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    engine: Optional[str] = Form(None),
    lang: Optional[str] = Form(None),
    speed_mode: Optional[str] = Form(None),
    psm: Optional[int] = Form(None),
):
    """
    Upload and scan a document (PDF or image) or markdown note.
    Runs text-layer detection: text-based PDFs skip OCR entirely.
    Scanned pages are preprocessed and extracted using the selected OCR engine (Tesseract, Google Vision, etc.).
    Extracts confidence scores per word/segment, marks OCR errors, detects tables, and preserves layout.
    """
    filename = file.filename or "uploaded_doc"
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    suffix = Path(filename).suffix.lower()
    notes_dir = Path(config.paths.notes_dir)
    notes_dir.mkdir(parents=True, exist_ok=True)

    use_engine = engine or getattr(config.ocr, "engine", "tesseract")
    use_lang = lang or getattr(config.ocr, "lang", "eng")
    use_speed = speed_mode or getattr(config.ocr, "speed_mode", "balanced")

    if suffix in [".md", ".markdown", ".txt"]:
        text_content = raw_bytes.decode("utf-8", errors="replace").strip()
        if not text_content:
            raise HTTPException(status_code=400, detail="File content is empty.")
        doc_title = (title or "").strip() or Path(filename).stem.replace("_", " ").title()
        stamp = _slugify(doc_title)[:40]
        note_filename = f"{stamp}_{date.today().isoformat()}.md"
        note_path = notes_dir / note_filename

        markdown = (
            "---\n"
            f"title: {doc_title.replace(chr(10), ' ')}\n"
            f"date: {date.today().isoformat()}\n"
            "tags: [\"upload\", \"text\"]\n"
            "source_type: markdown\n"
            "---\n\n"
            f"{text_content}\n"
        )
        await asyncio.to_thread(note_path.write_text, markdown, encoding="utf-8")
        note_id = note_path.stem.lower().replace(" ", "_")

        return UploadDocumentResponse(
            id=note_id,
            filename=note_filename,
            title=doc_title,
            markdown_content=text_content,
            has_text_layer=True,
            pages_count=1,
            mean_confidence=100.0,
            source_type="markdown",
            errors_count=0,
            tables_count=0,
            engine_used=use_engine,
            speed_mode_used=use_speed,
            pages=[],
            message=f"Text note saved to {note_filename}."
        )

    supported_doc_exts = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}
    if suffix not in supported_doc_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Supported: PDF, PNG, JPG, JPEG, TIFF, BMP, WEBP, MD, TXT"
        )

    # Save binary to cache/uploads dir
    upload_dir = Path(config.paths.data_dir) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    import hashlib
    digest = hashlib.sha256(raw_bytes).hexdigest()[:12]
    saved_doc_path = upload_dir / f"{Path(filename).stem}_{digest}{suffix}"
    await asyncio.to_thread(saved_doc_path.write_bytes, raw_bytes)

    # Detect text layer for PDFs
    is_text_pdf = False
    if suffix == ".pdf":
        is_text_pdf = has_text_layer(saved_doc_path)

    # OCR or extract text from document (skipping OCR for text layers, cached by hash)
    pages = await ocr_document(
        saved_doc_path,
        cache_dir=Path(config.ocr.cache_dir),
        engine=use_engine,
        lang=use_lang,
        speed_mode=use_speed,
        psm=psm or getattr(config.ocr, "psm", 6),
    )

    doc_title = (title or "").strip() or Path(filename).stem.replace("_", " ").replace("-", " ").title()
    markdown_content = pages_to_markdown(pages, doc_title)

    stamp = _slugify(doc_title)[:40]
    note_filename = f"{stamp}_{date.today().isoformat()}.md"
    note_path = notes_dir / note_filename

    mean_conf = round(
        sum(p.mean_confidence for p in pages) / max(1, len(pages)), 2
    ) if pages else 0.0

    total_errors = sum(len(p.error_segments) for p in pages)
    total_tables = sum(len(p.tables) for p in pages)

    frontmatter_str = (
        "---\n"
        f"title: {doc_title.replace(chr(10), ' ')}\n"
        f"date: {date.today().isoformat()}\n"
        "tags: [\"ocr\", \"document\"]\n"
        "source_type: ocr\n"
        f"source_file: {saved_doc_path.name}\n"
        f"pages_count: {len(pages)}\n"
        f"mean_confidence: {mean_conf}\n"
        f"has_text_layer: {is_text_pdf}\n"
        f"errors_marked: {total_errors}\n"
        f"tables_detected: {total_tables}\n"
        f"engine: {use_engine}\n"
        f"speed_mode: {use_speed}\n"
        "---\n\n"
        f"{markdown_content}\n"
    )
    await asyncio.to_thread(note_path.write_text, frontmatter_str, encoding="utf-8")

    note_id = note_path.stem.lower().replace(" ", "_")
    scan_desc = "text-layer extraction (OCR skipped)" if is_text_pdf else f"OCR scan ({use_engine}, {use_speed}, {mean_conf}% conf)"

    pages_serialized = [asdict(p) for p in pages]

    return UploadDocumentResponse(
        id=note_id,
        filename=note_filename,
        title=doc_title,
        markdown_content=markdown_content,
        has_text_layer=is_text_pdf,
        pages_count=len(pages),
        mean_confidence=mean_conf,
        source_type="ocr",
        errors_count=total_errors,
        tables_count=total_tables,
        engine_used=use_engine,
        speed_mode_used=use_speed,
        pages=pages_serialized,
        message=f"Document processed via {scan_desc} ({len(pages)} pages). Saved as {note_filename}."
    )


@router.post("/upload-batch", response_model=BatchUploadResponse)
async def upload_documents_batch(
    files: List[UploadFile] = File(...),
    engine: Optional[str] = Form(None),
    lang: Optional[str] = Form(None),
    speed_mode: Optional[str] = Form(None),
):
    """
    Batch process multiple uploaded documents concurrently with progress tracking.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    use_engine = engine or getattr(config.ocr, "engine", "tesseract")
    use_lang = lang or getattr(config.ocr, "lang", "eng")
    use_speed = speed_mode or getattr(config.ocr, "speed_mode", "balanced")

    upload_dir = Path(config.paths.data_dir) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    notes_dir = Path(config.paths.notes_dir)
    notes_dir.mkdir(parents=True, exist_ok=True)

    semaphore = asyncio.Semaphore(getattr(config.ocr, "batch_concurrency", 3))
    import hashlib

    async def _process_single(up_file: UploadFile) -> Dict[str, Any]:
        async with semaphore:
            fn = up_file.filename or "doc"
            try:
                content = await up_file.read()
                if not content:
                    return {"filename": fn, "status": "failed", "error": "Empty file"}

                sfx = Path(fn).suffix.lower()
                digest = hashlib.sha256(content).hexdigest()[:12]
                saved_path = upload_dir / f"{Path(fn).stem}_{digest}{sfx}"
                await asyncio.to_thread(saved_path.write_bytes, content)

                if sfx in [".md", ".markdown", ".txt"]:
                    text_content = content.decode("utf-8", errors="replace").strip()
                    if not text_content:
                        return {"filename": fn, "status": "failed", "error": "Empty file"}
                    doc_title = Path(fn).stem.replace("_", " ").replace("-", " ").title()
                    stamp = _slugify(doc_title)[:40]
                    note_fn = f"{stamp}_{digest[:8]}_{date.today().isoformat()}.md"
                    note_p = notes_dir / note_fn

                    markdown = (
                        "---\n"
                        f"title: {doc_title}\n"
                        f"date: {date.today().isoformat()}\n"
                        "tags: [\"upload\", \"text\"]\n"
                        "source_type: markdown\n"
                        "---\n\n"
                        f"{text_content}\n"
                    )
                    await asyncio.to_thread(note_p.write_text, markdown, encoding="utf-8")

                    return {
                        "filename": fn,
                        "saved_note": note_fn,
                        "status": "success",
                        "pages_count": 1,
                        "mean_confidence": 100.0,
                        "errors_count": 0,
                        "tables_count": 0,
                        "title": doc_title,
                    }

                pages = await ocr_document(
                    saved_path,
                    cache_dir=Path(config.ocr.cache_dir),
                    engine=use_engine,
                    lang=use_lang,
                    speed_mode=use_speed,
                )

                doc_title = Path(fn).stem.replace("_", " ").replace("-", " ").title()
                md = pages_to_markdown(pages, doc_title)
                stamp = _slugify(doc_title)[:40]
                note_fn = f"{stamp}_{date.today().isoformat()}.md"
                note_p = notes_dir / note_fn

                mean_c = round(sum(p.mean_confidence for p in pages) / max(1, len(pages)), 2)
                err_c = sum(len(p.error_segments) for p in pages)
                tbl_c = sum(len(p.tables) for p in pages)

                fm = (
                    "---\n"
                    f"title: {doc_title}\n"
                    f"date: {date.today().isoformat()}\n"
                    "tags: [\"ocr\", \"batch\"]\n"
                    "source_type: ocr\n"
                    f"pages_count: {len(pages)}\n"
                    f"mean_confidence: {mean_c}\n"
                    f"engine: {use_engine}\n"
                    f"speed_mode: {use_speed}\n"
                    "---\n\n"
                    f"{md}\n"
                )
                await asyncio.to_thread(note_p.write_text, fm, encoding="utf-8")

                return {
                    "filename": fn,
                    "saved_note": note_fn,
                    "status": "success",
                    "pages_count": len(pages),
                    "mean_confidence": mean_c,
                    "errors_count": err_c,
                    "tables_count": tbl_c,
                    "title": doc_title,
                }
            except Exception as e:
                return {
                    "filename": fn,
                    "status": "failed",
                    "error": str(e),
                    "pages_count": 0,
                    "mean_confidence": 0.0,
                    "errors_count": 0,
                    "tables_count": 0,
                }

    results = await asyncio.gather(*[_process_single(f) for f in files])
    succ = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    tot_pages = sum(r["pages_count"] for r in succ)
    avg_c = round(sum(r["mean_confidence"] for r in succ) / max(1, len(succ)), 2) if succ else 0.0
    tot_errs = sum(r["errors_count"] for r in succ)
    tot_tbls = sum(r["tables_count"] for r in succ)

    return BatchUploadResponse(
        total_documents=len(files),
        successful_documents=len(succ),
        failed_documents=len(failed),
        total_pages=tot_pages,
        mean_confidence=avg_c,
        total_errors_marked=tot_errs,
        total_tables_detected=tot_tbls,
        documents=results,
        message=f"Batch processed {len(files)} files: {len(succ)} succeeded, {len(failed)} failed.",
    )


@router.post("/ocr/correct")
async def correct_ocr_text(req: OCRCorrectionRequest):
    """
    Apply a user review correction to a saved OCR note.
    """
    notes_dir = Path(config.paths.notes_dir)
    target_file = notes_dir / req.filename
    if not target_file.exists():
        raise HTTPException(status_code=404, detail=f"Note file not found: {req.filename}")

    text = await asyncio.to_thread(target_file.read_text, encoding="utf-8")
    if req.old_text not in text:
        raise HTTPException(status_code=400, detail="Target text snippet not found in note.")

    updated_text = text.replace(req.old_text, req.new_text, 1)
    await asyncio.to_thread(target_file.write_text, updated_text, encoding="utf-8")
    return {"status": "success", "message": f"Updated text snippet in {req.filename}"}


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

    # CPU-bound work (SBERT embedding, NetworkX assembly) runs off the event loop.
    # 2. Embeddings
    embedder = SBERTEmbedder()
    chunk_texts = [c.text for c in chunks]
    chunk_vectors = await asyncio.to_thread(embedder.embed_texts, chunk_texts)

    # Vector Index
    vec_index = VectorIndex(dimension=embedder.dimension, index_path=config.database.vector_index_path)
    chunk_ids = [c.id for c in chunks]
    vec_index.add(chunk_ids, chunk_vectors)
    await asyncio.to_thread(vec_index.save)

    # 3. Extraction (async I/O against configured LLM provider)
    extractor = get_extraction_client()
    extractions = await extractor.extract_batch(chunks)
    await extractor.close()

    # 4. Knowledge Graph Assembly & Communities
    builder = KnowledgeGraphBuilder(
        embedder=embedder,
        deduplicator=EntityDeduplicator(similarity_threshold=config.graph.similarity_threshold),
        community_detector=CommunityDetector(
            resolution=config.graph.community_resolution,
            min_community_size=config.graph.min_community_size,
            max_levels=config.graph.max_levels
        )
    )
    nodes, edges, communities = await asyncio.to_thread(
        builder.build_from_extractions, extractions
    )

    # 4b. Compute Server-Side ForceAtlas2 Layout
    layout_coords = await asyncio.to_thread(compute_forceatlas2_layout, (nodes, edges))
    apply_layout_to_nodes(nodes, layout_coords)

    # 5. Summarization (Hierarchical Map-Reduce)
    summarizer = CommunitySummarizer(SummaryConfig(
        provider=config.llm.provider,
        model=config.llm.model,
        base_url=config.llm.base_url,
        api_key=config.llm.get_api_key(),
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
        timeout=config.llm.timeout
    ))
    summary_result = await summarizer.summarize_all(communities, nodes, edges)
    await summarizer.close()

    # 6. SQLite Persistence
    storage = SQLiteStorage(db_path=config.database.sqlite_path)
    await storage.initialize_schema()
    await storage.save_notes_and_chunks(notes, chunks)
    await storage.save_graph(nodes, edges, communities)
    if summary_result.global_summary:
        await storage.save_meta("global_summary", summary_result.global_summary)
    if summary_result.key_themes:
        await storage.save_meta("key_themes", summary_result.key_themes)

    # 7. Drop any cached query engine so the fresh index/schema is used.
    invalidate_query_engine()

    return IngestResponse(
        status="success",
        notes_count=len(notes),
        chunks_count=len(chunks),
        nodes_count=len(nodes),
        edges_count=len(edges),
        communities_count=len(communities),
        message="Knowledge graph successfully built and indexed."
    )