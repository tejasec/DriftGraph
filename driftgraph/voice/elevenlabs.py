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

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.base_url = "https://api.elevenlabs.io/v1"

    async def text_to_speech(self, text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> Optional[str]:
        """Convert text to MP3 audio and return as Base64 string."""
        if not self.api_key:
            logger.info("elevenlabs_api_key_not_set_skipping_tts")
            return None

        url = f"{self.base_url}/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    return base64.b64encode(resp.content).decode("utf-8")
                else:
                    logger.warning("elevenlabs_error", status=resp.status_code, text=resp.text)
        except Exception as e:
            logger.warning("elevenlabs_request_failed", error=str(e))

        return None
