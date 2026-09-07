"""
Data models for the Ingestion pipeline.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NoteMetadata(BaseModel):
    title: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    date: Optional[str] = None
    source_file: str
    extra: Dict[str, Any] = Field(default_factory=dict)


class Note(BaseModel):
    id: str
    content: str
    raw_content: str
    metadata: NoteMetadata


class Chunk(BaseModel):
    id: str
    note_id: str
    source_file: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    token_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
