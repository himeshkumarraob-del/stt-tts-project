from typing import Optional
from app.services.pronunciation.base import BasePronunciationAssessor
from app.services.pronunciation.assessor import AcousticPronunciationAssessor
from app.services.audio_validator import AudioValidatorService
from app.schemas.pronunciation import PronunciationAssessmentResponse
from app.core.config import settings
from app.core.errors import TargetTextValidationError
from app.core.logging import logger


class PronunciationService:
    """Orchestrator for Pronunciation Assessment operations."""

    _assessor: Optional[BasePronunciationAssessor] = None

    @classmethod
    def get_assessor(cls) -> BasePronunciationAssessor:
        if cls._assessor is None:
            cls._assessor = AcousticPronunciationAssessor(model_size=settings.STT_MODEL)
        return cls._assessor

    @classmethod
    def assess_pronunciation(
        cls,
        target_text: str,
        audio_bytes: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> PronunciationAssessmentResponse:
        logger.info(f"Initiating pronunciation assessment pipeline for '{filename}'...")

        # 1. Target text validation
        if not target_text or not target_text.strip():
            raise TargetTextValidationError("Target text must not be empty.")

        cleaned_target = target_text.strip()
        if len(cleaned_target) > settings.PRONUNCIATION_MAX_TARGET_LEN:
            raise TargetTextValidationError(
                f"Target text length ({len(cleaned_target)}) exceeds maximum limit of {settings.PRONUNCIATION_MAX_TARGET_LEN} characters."
            )

        # 2. Phase 1 Audio Validation
        validation_result = AudioValidatorService.validate_audio(
            file_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
        )

        audio_duration = validation_result.metadata.duration_seconds or 0.0

        # 3. Pronunciation Assessment
        assessor = cls.get_assessor()
        assessment_result = assessor.assess(
            target_text=cleaned_target,
            audio_bytes=audio_bytes,
            audio_duration_seconds=audio_duration,
            filename=filename,
        )

        logger.info(
            f"Pronunciation assessment complete for '{filename}': "
            f"Score={assessment_result.overall_score}/100, Confidence={assessment_result.confidence}, "
            f"ProcessingTime={assessment_result.processing_time_seconds}s"
        )

        return assessment_result
