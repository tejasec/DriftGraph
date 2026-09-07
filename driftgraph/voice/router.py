"""
Voice query pipeline: query processing -> GraphRAG answer synthesis -> TTS audio generation.
"""

from typing import Optional
import structlog

from driftgraph.query.engine import QueryEngine
from driftgraph.query.models import QueryRequest
from driftgraph.voice.elevenlabs import ElevenLabsClient
from driftgraph.voice.models import VoiceRequest, VoiceResponse

logger = structlog.get_logger(__name__)


class VoiceAssistant:
    """End-to-end voice assistant for Knowledge Graph Q&A."""

    def __init__(self, query_engine: QueryEngine, tts_client: Optional[ElevenLabsClient] = None):
        self.query_engine = query_engine
        self.tts = tts_client or ElevenLabsClient()

    async def process_voice_query(self, request: VoiceRequest) -> VoiceResponse:
        """Process voice query: answer from graph, then synthesize audio."""
        q_req = QueryRequest(query=request.query, mode=request.mode or "auto")
        q_res = await self.query_engine.query(q_req)

        audio_b64 = None
        if self.tts.api_key:
            audio_b64 = await self.tts.text_to_speech(q_res.answer, voice_id=request.voice_id or "21m00Tcm4TlvDq8ikWAM")

        return VoiceResponse(
            query=request.query,
            text_answer=q_res.answer,
            audio_base64=audio_b64,
            duration_sec=0.0
        )
