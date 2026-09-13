from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.schemas.pronunciation import PronunciationAssessmentResponse


class BasePronunciationAssessor(ABC):
    """Abstract interface for Pronunciation Assessment Models & Algorithms."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name or description of the pronunciation assessment engine."""
        pass

    @abstractmethod
    def assess(
        self,
        target_text: str,
        audio_bytes: bytes,
        audio_duration_seconds: float,
        filename: Optional[str] = None,
    ) -> PronunciationAssessmentResponse:
        """Perform acoustic analysis, word alignment, phoneme assessment, and pronunciation scoring."""
        pass
