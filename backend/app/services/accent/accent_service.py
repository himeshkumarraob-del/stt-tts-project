"""Orchestration service for speech accent analysis."""
import os
import tempfile
import logging
from typing import Optional
from app.services.audio_validator import AudioValidatorService
from app.services.accent.features import AcousticFeatureExtractor
from app.services.accent.base import BaseAccentClassifier
from app.services.accent.classifier import DevelopmentBaselineAccentClassifier
from app.schemas.accent import AccentAnalysisResponse
from app.core.logging import logger


class AccentService:
    """Service that coordinates Phase 1 audio validation, acoustic feature extraction, and accent classification."""

    _classifier: Optional[BaseAccentClassifier] = None
    _extractor: Optional[AcousticFeatureExtractor] = None

    @classmethod
    def get_classifier(cls) -> BaseAccentClassifier:
        if cls._classifier is None:
            cls._classifier = DevelopmentBaselineAccentClassifier()
        return cls._classifier

    @classmethod
    def set_classifier(cls, classifier: BaseAccentClassifier) -> None:
        cls._classifier = classifier

    @classmethod
    def get_extractor(cls) -> AcousticFeatureExtractor:
        if cls._extractor is None:
            cls._extractor = AcousticFeatureExtractor()
        return cls._extractor

    @classmethod
    def analyze_accent(
        cls,
        audio_bytes: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> AccentAnalysisResponse:
        """Validate audio bytes, extract acoustic features, and perform accent analysis."""
        logger.info(f"Initiating accent analysis pipeline for '{filename}'...")

        # 1. Phase 1 Audio Validation
        validation_result = AudioValidatorService.validate_audio(
            file_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
        )

        ext = validation_result.metadata.extension or "wav"
        temp_file = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
        temp_path = temp_file.name

        try:
            temp_file.write(audio_bytes)
            temp_file.flush()
            temp_file.close()

            # 2. Extract acoustic and prosodic features
            extractor = cls.get_extractor()
            try:
                features, metadata = extractor.extract_from_file(temp_path)
            except Exception as e:
                logger.error(f"Feature extraction failed on {filename}: {e}")
                from app.core.errors import AudioCorruptError
                raise AudioCorruptError(f"Failed to extract acoustic features from audio '{filename}': {e}")

            # 3. Classify accent and estimate confidence
            classifier = cls.get_classifier()
            accent_label, confidence, model_status, explanation, model_meta = classifier.classify(
                features=features,
                audio_metadata=metadata,
            )

            logger.info(
                f"Accent analysis complete for '{filename}': "
                f"Accent={accent_label.value}, Confidence={confidence}, ModelStatus={model_status.value}"
            )

            return AccentAnalysisResponse(
                accent=accent_label,
                confidence=confidence,
                model_status=model_status,
                features=features,
                explanation=explanation,
                metadata=model_meta,
            )
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_path}: {e}")
