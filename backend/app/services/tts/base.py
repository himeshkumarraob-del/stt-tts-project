"""Abstract base interface for Text-to-Speech (TTS) providers."""
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any
from app.schemas.tts import TTSSynthesizeRequest, TTSSynthesizeResponse


class BaseTTSProvider(ABC):
    """Abstract base class for speech synthesis providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the TTS provider."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier used by the TTS provider."""
        pass

    @abstractmethod
    async def synthesize_speech(
        self,
        request: TTSSynthesizeRequest,
    ) -> Tuple[bytes, TTSSynthesizeResponse]:
        """
        Synthesize text into speech audio bytes.
        
        Returns:
            Tuple of (raw_audio_bytes, TTSSynthesizeResponse_metadata)
        """
        pass
