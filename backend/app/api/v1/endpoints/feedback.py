"""API endpoint for AI Feedback & Personalized Learning (Phase 5)."""
from fastapi import APIRouter, status, Body
from app.schemas.feedback import FeedbackGenerationRequest, FeedbackResponse
from app.services.feedback import FeedbackService
from app.core.logging import logger

router = APIRouter()


@router.post(
    "/generate",
    response_model=FeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Personalized AI Learning Feedback",
    description="Accepts verified STT, Pronunciation Assessment, and Accent Analysis results, "
                "and generates structured, personalized learning recommendations, strength highlights, "
                "targeted phoneme/word guidance, and concrete practice drills.",
    tags=["Feedback"]
)
async def generate_feedback(
    request: FeedbackGenerationRequest = Body(..., description="Assessment results payload")
) -> FeedbackResponse:
    """Generate structured feedback and practice exercises from assessment outputs."""
    feedback = await FeedbackService.generate_feedback(request)
    return feedback
