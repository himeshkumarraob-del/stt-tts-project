"""Abstract base interface for accent classifiers."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple
from app.schemas.accent import (
    AccentLabel,
    ModelStatus,
    AcousticFeatures,
    AccentMetadata,
)


class BaseAccentClassifier(ABC):
    """Abstract base class for all accent classifiers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the classifier."""
        pass

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Version of the classifier."""
        pass

    @property
    @abstractmethod
    def model_type(self) -> str:
        """Classifier architecture/type."""
        pass

    @property
    @abstractmethod
    def is_calibrated(self) -> bool:
        """Whether the model is calibrated against a validated ground-truth evaluation set."""
        pass

    @abstractmethod
    def classify(
        self,
        features: AcousticFeatures,
        audio_metadata: Dict[str, Any],
    ) -> Tuple[AccentLabel, float, ModelStatus, List[str], AccentMetadata]:
        """
        Classify speech features into an accent category.
        
        Returns:
            Tuple of (AccentLabel, confidence, ModelStatus, explanation_list, AccentMetadata)
        """
        pass
