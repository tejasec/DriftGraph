"""driftgraph/voice/router.py

Voice query & recording pipeline:
- Voice-powered queries with Quick-Answer mode
- Conversational memory for multi-turn dialogues
- Audio-to-text transcription for voice recording into structured notes
- TTS speech synthesis via ElevenLabs
"""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from typing import Optional, List, Dict, Any
import structlog

from driftgraph.config import config
from driftgraph.query.engine import QueryEngine
from driftgraph.query.models import QueryRequest
import uuid
import base64
from driftgraph.voice.elevenlabs import ElevenLabsClient
from driftgraph.voice.memory import ConversationMemoryManager
from driftgraph.voice.transcriber import AudioTranscriber
from driftgraph.voice.models import (
    VoiceRequest,
    VoiceResponse,
    VoiceTranscribeResponse,
    VoiceToNoteResponse,
)
from driftgraph.classifier.rule_based import DocumentClassifier

logger = structlog.get_logger(__name__)

# In-memory audio cache for streaming audio playback
VOICE_AUDIO_CACHE: Dict[str, bytes] = {}


class VoiceAssistant:
    """End-to-end voice assistant for Knowledge Graph Q&A and Note Recording."""

    def __init__(
        self,
        query_engine: QueryEngine,
        tts_client: Optional[ElevenLabsClient] = None,
        memory_manager: Optional[ConversationMemoryManager] = None,
        transcriber: Optional[AudioTranscriber] = None,
    ):
        self.query_engine = query_engine
        self.tts = tts_client or ElevenLabsClient()
        self.memory = memory_manager or ConversationMemoryManager()
        self.transcriber = transcriber or AudioTranscriber()
        self.classifier = DocumentClassifier()

    async def process_voice_query(self, request: VoiceRequest) -> VoiceResponse:
        """
        Process voice query:
        - If quick_answer or quick_mode is True: answer directly from graph nodes/FTS without full LLM pipeline.
        - If conversational session_id is provided: inject history for contextual memory.
        - Synthesize audio if TTS is configured.
        - Identify cited node IDs for canvas highlighting.
        """
        query_text = request.query.strip()
        session_id = request.session_id or "default_session"
        is_quick = request.quick_mode if request.quick_mode is not None else request.quick_answer

        # 1. Quick-answer mode: fast lookup directly from the graph
        if is_quick:
            answer, sources, cited_node_ids = await self._quick_answer_lookup(query_text)
            mode_used = "quick"
            citations = sources
        else:
            # Multi-turn conversational context injection
            history_prefix = self.memory.format_history_prompt(session_id)
            contextual_query = f"{history_prefix}Current Question: {query_text}" if history_prefix else query_text

            q_req = QueryRequest(query=contextual_query, mode=request.mode or "auto")
            q_res = await self.query_engine.query(q_req)
            answer = q_res.answer
            mode_used = getattr(q_res, "mode_used", "auto")

            raw_citations = getattr(q_res, "citations", None)
            if raw_citations is not None:
                citations = [c.model_dump() if hasattr(c, "model_dump") else c for c in raw_citations]
            else:
                citations = getattr(q_res, "sources", [])
            sources = citations

            # Resolve cited node IDs for canvas illumination
            cited_node_ids = []
            for c in citations:
                c_type = c.get("source_type") if isinstance(c, dict) else getattr(c, "source_type", None)
                cid = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
                if c_type == "node" and cid:
                    cited_node_ids.append(cid)

            # Match entities in storage if none direct
            if hasattr(self.query_engine, "storage"):
                try:
                    matched_nodes = await self.query_engine.storage.search_nodes(query_text, limit=5)
                    for n in matched_nodes:
                        if n.id not in cited_node_ids:
                            cited_node_ids.append(n.id)
                except Exception as ex:
                    logger.debug("voice_entity_search_error", error=str(ex))

        # Record in conversational memory
        self.memory.add_user_message(session_id, query_text)
        self.memory.add_assistant_message(session_id, answer)

        # 2. Text-to-Speech synthesis
        audio_b64 = None
        audio_url = None
        voice_id = request.voice_id or os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        if self.tts.api_key:
            audio_bytes = await self.tts.text_to_speech_bytes(answer, voice_id=voice_id)
            if audio_bytes:
                audio_id = str(uuid.uuid4())
                VOICE_AUDIO_CACHE[audio_id] = audio_bytes
                audio_url = f"/api/voice/audio/{audio_id}"
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return VoiceResponse(
            query=request.query,
            text_answer=answer,
            answer=answer,
            audio_base64=audio_b64,
            audio_url=audio_url,
            duration_sec=0.0,
            session_id=session_id,
            mode_used=mode_used,
            sources=sources,
            citations=citations,
            cited_node_ids=cited_node_ids,
        )

    async def _quick_answer_lookup(self, query: str) -> tuple[str, List[Dict[str, Any]], List[str]]:
        """Direct graph answer without heavy LLM map-reduce."""
        storage = getattr(self.query_engine, "storage", None) or getattr(getattr(self.query_engine, "local_engine", None), "storage", None)
        if not storage:
            return (
                f"Quick Answer: Knowledge graph storage unavailable.",
                [],
                []
            )
        nodes = await storage.search_nodes(query, limit=5)
        if not nodes:
            return (
                f"Quick Answer: No direct entity match found for '{query}' in the knowledge graph.",
                [],
                []
            )

        top_node = nodes[0]
        desc = top_node.description or "No description recorded."
        sources = [{"id": top_node.id, "name": top_node.name, "type": top_node.type, "community_id": top_node.community_id, "source_type": "node"}]
        cited_node_ids = [n.id for n in nodes[:3]]

        other_names = [n.name for n in nodes[1:4]]
        also_related = f" Related concepts: {', '.join(other_names)}." if other_names else ""

        return (
            f"Quick Answer: {top_node.name} ({top_node.type}) — {desc}{also_related}",
            sources,
            cited_node_ids
        )

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        language: str = "en-US",
        prompt_hint: Optional[str] = None
    ) -> VoiceTranscribeResponse:
        """Transcribe voice audio bytes to text."""
        duration, sr_rate, channels = self.transcriber.get_audio_info(audio_bytes)
        transcript = await self.transcriber.transcribe(audio_bytes, language=language, prompt_hint=prompt_hint)
        return VoiceTranscribeResponse(
            transcript=transcript,
            duration_sec=duration,
            sample_rate=sr_rate,
            channels=channels,
            status="success"
        )

    async def record_voice_to_note(
        self,
        audio_bytes: bytes,
        title: Optional[str] = None,
        language: str = "en-US",
        auto_classify: bool = True
    ) -> VoiceToNoteResponse:
        """
        Transcribe voice recording and write a new structured note into notes_dir.
        Optionally classifies and auto-tags the transcribed text.
        """
        transcript = await self.transcriber.transcribe(audio_bytes, language=language)
        if not transcript:
            transcript = "Empty voice recording."

        today_iso = date.today().isoformat()
        base_title = (title or "").strip() or transcript.splitlines()[0][:30].strip() or "Voice Note"
        clean_title = "".join(c for c in base_title if c.isalnum() or c in " _-")[:40].strip() or "voice_note"

        tags = ["voice", "transcript"]
        top_cat = None

        if auto_classify:
            cls_res = self.classifier.classify_text(transcript, filename=f"{clean_title}.wav")
            top_cat = cls_res.top_category
            tags.extend(cls_res.auto_tags[:4])

        notes_dir = Path(config.paths.notes_dir)
        notes_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{clean_title.replace(' ', '_').lower()}_{today_iso}.md"
        note_path = notes_dir / filename

        md_content = (
            "---\n"
            f"title: \"{base_title}\"\n"
            f"date: {today_iso}\n"
            f"source_type: voice\n"
            f"tags: {tags}\n"
            "---\n\n"
            f"### Voice Transcript\n\n"
            f"{transcript}\n"
        )
        await asyncio.to_thread(note_path.write_text, md_content, encoding="utf-8")

        note_id = note_path.stem.lower().replace(" ", "_")
        return VoiceToNoteResponse(
            id=note_id,
            filename=filename,
            title=base_title,
            transcript=transcript,
            tags=tags,
            top_category=top_cat,
            message="Transcribed voice recording and created markdown note."
        )
