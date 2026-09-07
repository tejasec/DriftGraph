"""
Tests for Ingestion and Chunking.
"""

import pytest
from pathlib import Path
from driftgraph.ingest import parse_markdown_directory, chunk_notes


@pytest.mark.asyncio
async def test_parse_sample_notes():
    notes_dir = Path("./data/notes")
    notes = await parse_markdown_directory(notes_dir)
    assert len(notes) >= 3

    for note in notes:
        assert note.id
        assert note.content
        assert note.metadata.title


@pytest.mark.asyncio
async def test_chunk_notes():
    notes_dir = Path("./data/notes")
    notes = await parse_markdown_directory(notes_dir)
    chunks = chunk_notes(notes, target_tokens=128, overlap_tokens=20)
    assert len(chunks) >= 3

    for chunk in chunks:
        assert chunk.id
        assert chunk.text
        assert chunk.token_count > 0
