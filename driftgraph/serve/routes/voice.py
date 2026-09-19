"""driftgraph/serve/routes/voice.py

Voice assistant API routes:
- Voice queries with Quick-Answer mode and Conversational Memory
- Audio-to-text transcription
- Voice-recording into structured Markdown notes
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Response

from driftgraph.voice.models import (
    VoiceRequest,
    VoiceResponse,
    VoiceTranscribeResponse,
    VoiceToNoteResponse,
)
from driftgraph.voice.router import VoiceAssistant, VOICE_AUDIO_CACHE
from driftgraph.serve.routes.query import get_query_engine
from driftgraph.query.engine import QueryEngine

router = APIRouter(prefix="/api/voice", tags=["Voice"])

_voice_assistant: Optional[VoiceAssistant] = None


def get_voice_assistant(engine: QueryEngine = Depends(get_query_engine)) -> VoiceAssistant:
    global _voice_assistant
    if _voice_assistant is None or _voice_assistant.query_engine != engine:
        _voice_assistant = VoiceAssistant(query_engine=engine)
    return _voice_assistant


@router.post("/ask", response_model=VoiceResponse)
async def voice_ask(
    request: VoiceRequest,
    assistant: VoiceAssistant = Depends(get_voice_assistant)
):
    """Execute voice RAG query returning synthesized answer, audio, and cited nodes."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Voice query cannot be empty.")
    return await assistant.process_voice_query(request)


@router.post("/query", response_model=VoiceResponse)
async def voice_query(
    request: VoiceRequest,
    assistant: VoiceAssistant = Depends(get_voice_assistant)
):
    """Alias for /ask."""
    return await voice_ask(request, assistant=assistant)


@router.get("/audio/{audio_id}")
async def stream_voice_audio(audio_id: str):
    """Stream generated voice audio (MP3) for browser playback."""
    audio_bytes = VOICE_AUDIO_CACHE.get(audio_id)
    if not audio_bytes:
        raise HTTPException(status_code=404, detail="Audio expired or not found.")
    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe_audio_file(
    file: UploadFile = File(...),
    language: str = Form("en-US"),
    prompt_hint: Optional[str] = Form(None),
    assistant: VoiceAssistant = Depends(get_voice_assistant)
):
    """Transcribe an uploaded voice recording to text."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")
    return await assistant.transcribe_audio(audio_bytes, language=language, prompt_hint=prompt_hint)


@router.post("/to-note", response_model=VoiceToNoteResponse)
async def voice_to_note(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    language: str = Form("en-US"),
    auto_classify: bool = Form(True),
    assistant: VoiceAssistant = Depends(get_voice_assistant)
):
    """Transcribe voice recording directly into a structured Markdown note."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")
    return await assistant.record_voice_to_note(
        audio_bytes,
        title=title,
        language=language,
        auto_classify=auto_classify
    )


@router.post("/memory/clear")
async def clear_conversational_memory(
    session_id: str = Form("default_session"),
    assistant: VoiceAssistant = Depends(get_voice_assistant)
):
    """Reset conversational memory context for a given session."""
    assistant.memory.clear_session(session_id)
    return {"status": "success", "message": f"Cleared conversational memory for session '{session_id}'."}
