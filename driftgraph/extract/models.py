"""
Data models for Entity and Relation extraction.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Entity(BaseModel):
    name: str
    type: str = "CONCEPT"
    description: Optional[str] = None
    source_chunk_id: Optional[str] = None
    confidence: float = 1.0


class Relation(BaseModel):
    subject: str
    predicate: str
    object: str
    description: Optional[str] = None
    confidence: float = 1.0
    source_chunk_id: Optional[str] = None


class ExtractionResult(BaseModel):
    chunk_id: str
    entities: List[Entity] = Field(default_factory=list)
    relations: List[Relation] = Field(default_factory=list)


class ExtractionConfig(BaseModel):
    model: str = "llama3.1:8b-instruct-q4_K_M"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.1
    timeout: int = 120
    max_retries: int = 3
