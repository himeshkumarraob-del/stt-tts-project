"""OpenAI TTS Provider with resilient fallback."""
import base64
import logging
from typing import Optional, Tuple
import httpx

from app.core.config import settings
from app.schemas.tts import TTSSynthesizeRequest, TTSSynthesizeResponse
from app.services.tts.base import BaseTTSProvider
from app.services.tts.fallback_tts import DeterministicFallbackTTSProvider

logger = logging.getLogger(__name__)


class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI Text-to-Speech provider with automatic fallback on failure."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model or settings.TTS_MODEL
        self._base_url = (base_url or settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self._timeout = timeout or settings.TTS_TIMEOUT_SECONDS
        self._fallback = DeterministicFallbackTTSProvider()

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def synthesize_speech(
        self,
        request: TTSSynthesizeRequest,
    ) -> Tuple[bytes, TTSSynthesizeResponse]:
        """Synthesize speech using OpenAI API or fallback if unavailable."""
        if not self._api_key or not self._api_key.strip() or self._api_key == "your_openai_api_key_here":
            logger.info("OpenAI API key not configured or placeholder detected for TTS. Using deterministic fallback.")
            return await self._fallback.synthesize_speech(request)

        voice = request.voice or settings.TTS_VOICE or "alloy"
        fmt = request.audio_format or settings.TTS_AUDIO_FORMAT or "mp3"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": request.text,
            "voice": voice,
            "response_format": fmt,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/audio/speech",
                    headers=headers,
                    json=payload,
                )

            if resp.status_code != 200:
                logger.warning(f"OpenAI TTS API returned non-200 status {resp.status_code}: {resp.text}. Falling back.")
                return await self._fallback.synthesize_speech(request)

            audio_bytes = resp.content
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            response = TTSSynthesizeResponse(
                audio_base64=audio_b64,
                format=fmt,
                voice=voice,
                provider=self.provider_name,
                model=self.model_name,
                character_count=len(request.text),
                is_fallback=False,
            )
            return audio_bytes, response

        except Exception as e:
            logger.error(f"Error communicating with OpenAI TTS API: {e}. Gracefully falling back.")
            return await self._fallback.synthesize_speech(request)
