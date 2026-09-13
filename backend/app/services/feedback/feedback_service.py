"""Feedback Service orchestrator (Phase 5)."""
import logging
from typing import Optional
from app.core.config import settings
from app.schemas.feedback import FeedbackGenerationRequest, FeedbackResponse
from app.services.feedback.base import BaseFeedbackProvider
from app.services.feedback.openai_provider import OpenAIFeedbackProvider
from app.services.feedback.fallback_provider import DeterministicFallbackProvider

logger = logging.getLogger(__name__)


class FeedbackService:
    """Orchestrator for generating personalized learning feedback."""

    _provider: Optional[BaseFeedbackProvider] = None

    @classmethod
    def get_provider(cls) -> BaseFeedbackProvider:
        if cls._provider is None:
            provider_type = (settings.LLM_PROVIDER or "openai").lower()
            if provider_type == "openai":
                cls._provider = OpenAIFeedbackProvider()
            elif provider_type == "fallback":
                cls._provider = DeterministicFallbackProvider()
            else:
                logger.warning(f"Unknown LLM provider '{provider_type}', using OpenAIFeedbackProvider.")
                cls._provider = OpenAIFeedbackProvider()
        return cls._provider

    @classmethod
    def set_provider(cls, provider: BaseFeedbackProvider) -> None:
        """Override active provider (useful for testing and dependency injection)."""
        cls._provider = provider

    @classmethod
    async def generate_feedback(cls, request: FeedbackGenerationRequest) -> FeedbackResponse:
        """Generate structured personalized feedback using the configured provider."""
        logger.info(
            f"Generating personalized feedback for session '{request.session_id or 'default'}' "
            f"(PronScore: {request.pronunciation_result.overall_score}/100, Accent: {request.accent_result.accent.value})..."
        )
        provider = cls.get_provider()
        feedback = await provider.generate_feedback(request)
        logger.info(
            f"Feedback generated successfully using provider '{feedback.provider}' "
            f"(model: '{feedback.model}', is_fallback: {feedback.is_fallback})"
        )
        return feedback
