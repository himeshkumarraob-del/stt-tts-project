"""OpenAI-compatible LLM Feedback Provider with resilient fallback."""
import json
import logging
from typing import Optional, Dict, Any
import httpx

from app.core.config import settings
from app.schemas.feedback import (
    FeedbackGenerationRequest,
    FeedbackResponse,
    PracticeExercise,
    ScoresSummary,
)
from app.services.feedback.base import BaseFeedbackProvider
from app.services.feedback.prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.feedback.fallback_provider import DeterministicFallbackProvider

logger = logging.getLogger(__name__)


class OpenAIFeedbackProvider(BaseFeedbackProvider):
    """
    OpenAI API Feedback Provider.
    Calls OpenAI Chat Completions endpoint with structured JSON mode.
    Automatically and safely falls back to DeterministicFallbackProvider on any error, timeout, or missing key.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model or settings.OPENAI_MODEL
        self._base_url = (base_url or settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self._timeout = timeout or settings.LLM_TIMEOUT_SECONDS
        self._fallback_provider = DeterministicFallbackProvider()

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate_feedback(self, request: FeedbackGenerationRequest) -> FeedbackResponse:
        """Generate feedback via OpenAI API or fallback if unavailable."""
        if not self._api_key or not self._api_key.strip() or self._api_key == "your_openai_api_key_here":
            logger.info("OpenAI API key not configured or placeholder detected. Using deterministic fallback provider.")
            return await self._fallback_provider.generate_feedback(request)

        user_content = build_user_prompt(request)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "temperature": settings.LLM_TEMPERATURE,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

            if resp.status_code != 200:
                logger.warning(f"OpenAI API returned non-200 status {resp.status_code}: {resp.text}. Falling back.")
                return await self._fallback_provider.generate_feedback(request)

            data = resp.json()
            raw_content = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_content)

            # Build exercises
            exercises = []
            for ex in parsed.get("suggested_exercises", []):
                exercises.append(
                    PracticeExercise(
                        title=ex.get("title", "Practice Exercise"),
                        exercise_type=ex.get("exercise_type", "repetition"),
                        target_words=ex.get("target_words", []),
                        instructions=ex.get("instructions", "Practice saying target words."),
                        sample_sentence=ex.get("sample_sentence"),
                    )
                )

            # Preserve authoritative assessment scores
            pron = request.pronunciation_result
            accent = request.accent_result
            correct_words = [w for w in pron.words if w.status.value == "correct"]

            scores_summary = ScoresSummary(
                overall_pronunciation_score=round(pron.overall_score, 1),
                pronunciation_confidence=round(pron.confidence, 3),
                accent_label=accent.accent.value,
                accent_model_status=accent.model_status.value,
                accent_confidence=round(accent.confidence, 3),
                words_total=len(pron.words),
                words_correct=len(correct_words),
                issues_detected_count=len(pron.issues),
            )

            return FeedbackResponse(
                overall_summary=parsed.get("overall_summary", "Assessment summary generated."),
                pronunciation_feedback=parsed.get("pronunciation_feedback", ""),
                accent_feedback=parsed.get("accent_feedback", ""),
                strengths=parsed.get("strengths", []),
                areas_to_improve=parsed.get("areas_to_improve", []),
                practice_recommendations=parsed.get("practice_recommendations", []),
                suggested_exercises=exercises,
                scores_summary=scores_summary,
                is_fallback=False,
                provider=self.provider_name,
                model=self.model_name,
            )

        except Exception as e:
            logger.error(f"Error communicating with OpenAI API: {e}. Gracefully falling back to deterministic generator.")
            return await self._fallback_provider.generate_feedback(request)
