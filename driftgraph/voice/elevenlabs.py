"""
ElevenLabs Text-to-Speech client integration.
"""

import os
import base64
from typing import Optional
import httpx
import structlog

logger = structlog.get_logger(__name__)


class ElevenLabsClient:
    """ElevenLabs TTS client with environment variable API key support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self._api_key = api_key
        self.default_voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        self.base_url = (base_url or os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io/v1")).rstrip("/")

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key or os.getenv("ELEVENLABS_API_KEY")

    @api_key.setter
    def api_key(self, value: Optional[str]):
        self._api_key = value

    async def text_to_speech_bytes(
        self, text: str, voice_id: Optional[str] = None
    ) -> Optional[bytes]:
        """Convert text to MP3 audio bytes using ElevenLabs TTS."""
        if not self.api_key:
            logger.info("elevenlabs_api_key_not_set_skipping_tts")
            return None

        actual_voice_id = voice_id or self.default_voice_id
        url = f"{self.base_url}/text-to-speech/{actual_voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    return resp.content
                else:
                    logger.warning("elevenlabs_error", status=resp.status_code, text=resp.text)
        except Exception as e:
            logger.warning("elevenlabs_request_failed", error=str(e))

        return None

    async def text_to_speech(
        self, text: str, voice_id: Optional[str] = None
    ) -> Optional[str]:
        """Convert text to MP3 audio and return as Base64 string."""
        audio_bytes = await self.text_to_speech_bytes(text, voice_id=voice_id)
        if audio_bytes:
            return base64.b64encode(audio_bytes).decode("utf-8")
        return None
