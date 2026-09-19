"""driftgraph/voice/models.py

Data models for voice assistant, audio transcription, conversational memory, and voice-to-note pipeline.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VoiceRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    voice_id: Optional[str] = "21m00Tcm4TlvDq8ikWAM"  # Rachel default
    mode: Optional[str] = "auto"  # auto, local, global, quick
    quick_answer: bool = False
    quick_mode: Optional[bool] = None
    language: str = "en-US"


class VoiceResponse(BaseModel):
    query: str
    text_answer: str
    answer: str = ""
    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None
    duration_sec: float = 0.0
    session_id: Optional[str] = None
    mode_used: str = "auto"
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    cited_node_ids: List[str] = Field(default_factory=list)


class VoiceTranscribeResponse(BaseModel):
    transcript: str
    duration_sec: float
    sample_rate: int
    channels: int
    status: str = "success"


class VoiceToNoteResponse(BaseModel):
    id: str
    filename: str
    title: str
    transcript: str
    source_type: str = "voice"
    tags: List[str] = Field(default_factory=list)
    top_category: Optional[str] = None
    message: str = "Voice note created successfully."
