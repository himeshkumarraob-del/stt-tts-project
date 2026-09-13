"""TTS Service orchestrator."""
import logging
from typing import Optional, Tuple
from app.core.config import settings
from app.schemas.tts import TTSSynthesizeRequest, TTSSynthesizeResponse
from app.services.tts.base import BaseTTSProvider
from app.services.tts.openai_tts import OpenAITTSProvider
from app.services.tts.fallback_tts import DeterministicFallbackTTSProvider

logger = logging.getLogger(__name__)


class TTSService:
    """Service orchestrator for Text-to-Speech synthesis operations."""

    _provider: Optional[BaseTTSProvider] = None

    @classmethod
    def get_provider(cls) -> BaseTTSProvider:
        if cls._provider is None:
            provider_type = (settings.TTS_PROVIDER or "openai").lower()
            if provider_type == "openai":
                cls._provider = OpenAITTSProvider()
            elif provider_type == "fallback":
                cls._provider = DeterministicFallbackTTSProvider()
            else:
                logger.warning(f"Unknown TTS provider '{provider_type}', default to OpenAITTSProvider.")
                cls._provider = OpenAITTSProvider()
        return cls._provider

    @classmethod
    def set_provider(cls, provider: BaseTTSProvider) -> None:
        """Override the active TTS provider (for testing/mocking)."""
        cls._provider = provider

    @classmethod
    async def synthesize(
        cls,
        text: str,
        voice: Optional[str] = None,
        audio_format: Optional[str] = None,
    ) -> Tuple[bytes, TTSSynthesizeResponse]:
        """Synthesize text into speech audio bytes and metadata."""
        if not text or not text.strip():
            raise ValueError("TTS synthesis text cannot be empty.")

        cleaned_text = text.strip()
        if len(cleaned_text) > settings.TTS_MAX_TEXT_LEN:
            raise ValueError(f"Text length ({len(cleaned_text)}) exceeds maximum allowed ({settings.TTS_MAX_TEXT_LEN}) characters.")

        req = TTSSynthesizeRequest(
            text=cleaned_text,
            voice=voice or settings.TTS_VOICE,
            audio_format=audio_format or settings.TTS_AUDIO_FORMAT,
        )

        provider = cls.get_provider()
        audio_bytes, response = await provider.synthesize_speech(req)
        logger.info(
            f"TTS synthesis complete ({len(cleaned_text)} chars) using provider '{response.provider}' "
            f"(model: '{response.model}', is_fallback: {response.is_fallback})"
        )
        return audio_bytes, response
