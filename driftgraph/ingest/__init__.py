"""
Ingestion module for parsing and chunking markdown notes.
"""

from driftgraph.ingest.models import Note, NoteMetadata, Chunk
from driftgraph.ingest.parser import parse_markdown_file, parse_markdown_directory
from driftgraph.ingest.chunker import chunk_note, chunk_notes

__all__ = [
    "Note",
    "NoteMetadata",
    "Chunk",
    "parse_markdown_file",
    "parse_markdown_directory",
    "chunk_note",
    "chunk_notes",
]
