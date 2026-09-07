"""
Data models for voice assistant and audio synthesis.
"""

from typing import Optional
from pydantic import BaseModel


class VoiceRequest(BaseModel):
    query: str
    voice_id: Optional[str] = "21m00Tcm4TlvDq8ikWAM"  # Rachel default
    mode: Optional[str] = "auto"


class VoiceResponse(BaseModel):
    query: str
    text_answer: str
    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None
    duration_sec: float = 0.0
