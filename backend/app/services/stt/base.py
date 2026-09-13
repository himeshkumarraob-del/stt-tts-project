from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.schemas.stt import TranscriptionResponse


class BaseSTTProvider(ABC):
    """Abstract Base Class for all Speech-to-Text providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the STT provider."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name or identifier of the underlying speech model."""
        pass

    @abstractmethod
    def transcribe(
        self,
        audio_bytes: bytes,
        audio_duration_seconds: float,
        language: Optional[str] = "en",
        filename: Optional[str] = None,
    ) -> TranscriptionResponse:
        """Transcribes raw audio bytes and returns structured transcription results."""
        pass
