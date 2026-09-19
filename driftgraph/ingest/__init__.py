"""
Ingestion module for parsing and chunking markdown notes.
"""

from driftgraph.ingest.models import Note, NoteMetadata, Chunk
from driftgraph.ingest.parser import parse_markdown_file, parse_markdown_directory
from driftgraph.ingest.chunker import chunk_note, chunk_notes
from driftgraph.ingest.ocr_models import (
    OCRPage,
    TextSegment,
    TableStructure,
    OCROptions,
    BatchOCRResult,
)
from driftgraph.ingest.ocr_engines import (
    BaseOCREngine,
    TesseractEngine,
    GoogleVisionEngine,
    LocalHeuristicEngine,
    get_ocr_engine,
    list_available_engines,
)
from driftgraph.ingest.ocr import (
    has_text_layer,
    preprocess,
    ocr_document,
    batch_ocr_documents,
    pages_to_markdown,
    ocr_pages_to_note,
    process_document_to_note,
    get_installed_languages,
    PSM_BY_LAYOUT,
)

__all__ = [
    "Note",
    "NoteMetadata",
    "Chunk",
    "parse_markdown_file",
    "parse_markdown_directory",
    "chunk_note",
    "chunk_notes",
    "OCRPage",
    "TextSegment",
    "TableStructure",
    "OCROptions",
    "BatchOCRResult",
    "BaseOCREngine",
    "TesseractEngine",
    "GoogleVisionEngine",
    "LocalHeuristicEngine",
    "get_ocr_engine",
    "list_available_engines",
    "has_text_layer",
    "preprocess",
    "ocr_document",
    "batch_ocr_documents",
    "pages_to_markdown",
    "ocr_pages_to_note",
    "process_document_to_note",
    "get_installed_languages",
    "PSM_BY_LAYOUT",
]
