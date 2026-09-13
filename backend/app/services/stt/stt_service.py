from typing import Optional, Dict
from app.services.stt.base import BaseSTTProvider
from app.services.stt.whisper_provider import FasterWhisperProvider
from app.services.audio_validator import AudioValidatorService
from app.schemas.stt import TranscriptionResponse
from app.core.config import settings
from app.core.errors import STTConfigurationError
from app.core.logging import logger


class STTService:
    """Orchestrator for Speech-to-Text operations ensuring audio validation precedes transcription."""

    _providers: Dict[str, BaseSTTProvider] = {}

    @classmethod
    def get_provider(cls, provider_name: Optional[str] = None) -> BaseSTTProvider:
        """Factory method to get or instantiate the configured STT provider."""
        provider_key = (provider_name or settings.STT_PROVIDER).lower().strip()

        if provider_key in cls._providers:
            return cls._providers[provider_key]

        if provider_key in ["faster-whisper", "whisper", "local"]:
            provider = FasterWhisperProvider(
                model_size=settings.STT_MODEL,
                device=settings.STT_DEVICE,
                compute_type=settings.STT_COMPUTE_TYPE,
            )
            cls._providers[provider_key] = provider
            return provider
        else:
            raise STTConfigurationError(
                f"Unsupported STT provider '{provider_key}'. Supported providers: ['faster-whisper']"
            )

    @classmethod
    def transcribe_audio(
        cls,
        audio_bytes: bytes,
        filename: str,
        content_type: Optional[str] = None,
        language: Optional[str] = "en",
        provider_name: Optional[str] = None,
    ) -> TranscriptionResponse:
        """Full pipeline: Audio Ingestion -> Phase 1 Validation -> STT Provider -> Normalized Transcription."""
        logger.info(f"Initiating STT transcription pipeline for '{filename}'...")

        # Step 1: Execute Phase 1 Validation (reused directly, raising structured exceptions on violation)
        validation_result = AudioValidatorService.validate_audio(
            file_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
        )

        audio_duration = validation_result.metadata.duration_seconds or 0.0

        # Step 2: Retrieve Provider
        provider = cls.get_provider(provider_name=provider_name)

        # Step 3: Execute Transcription
        transcription_result = provider.transcribe(
            audio_bytes=audio_bytes,
            audio_duration_seconds=audio_duration,
            language=language,
            filename=filename,
        )

        logger.info(
            f"Successfully transcribed '{filename}' ({transcription_result.duration_seconds}s) "
            f"in {transcription_result.processing_time_seconds}s using {provider.provider_name}:{provider.model_name}"
        )

        return transcription_result
