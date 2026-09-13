"""Abstract base interface for feedback providers."""
from abc import ABC, abstractmethod
from app.schemas.feedback import FeedbackGenerationRequest, FeedbackResponse


class BaseFeedbackProvider(ABC):
    """Abstract base class for AI Feedback providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the feedback provider."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier used by the provider."""
        pass

    @abstractmethod
    async def generate_feedback(self, request: FeedbackGenerationRequest) -> FeedbackResponse:
        """
        Generate structured, personalized feedback based on assessment inputs.
        
        Args:
            request: FeedbackGenerationRequest containing STT, pronunciation, and accent data.
            
        Returns:
            FeedbackResponse with personalized recommendations, strengths, and exercises.
        """
        pass
