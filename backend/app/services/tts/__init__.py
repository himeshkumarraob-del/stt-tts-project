"""Text-to-Speech package."""
from app.services.tts.base import BaseTTSProvider
from app.services.tts.openai_tts import OpenAITTSProvider
from app.services.tts.fallback_tts import DeterministicFallbackTTSProvider
from app.services.tts.tts_service import TTSService

__all__ = [
    "BaseTTSProvider",
    "OpenAITTSProvider",
    "DeterministicFallbackTTSProvider",
    "TTSService",
]
