"""API endpoints for Personalized STT Correction Memory."""
from fastapi import APIRouter, status, Body, HTTPException, Path
from app.schemas.correction import (
    CorrectionConfirmRequest,
    CorrectionResponse,
    CorrectionListResponse,
)
from app.services.correction import CorrectionService
from app.core.logging import logger

router = APIRouter()


@router.post(
    "/confirm",
    response_model=CorrectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm Personalized STT Correction",
    description="Stores or updates a user-specific STT correction (e.g. 'image' -> 'Himesh' when context is 'my name is'). "
                "Increments occurrence frequency, updates confidence weighting, and ensures future transcripts apply this replacement.",
    tags=["Corrections"]
)
async def confirm_correction(
    request: CorrectionConfirmRequest = Body(..., description="Correction payload")
) -> CorrectionResponse:
    """Store or update a user-specific correction."""
    if not request.user_id or not request.user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": True, "message": "user_id is required."}
        )
    if not request.incorrect_text or not request.incorrect_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": True, "message": "incorrect_text is required."}
        )
    if not request.correct_text or not request.correct_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": True, "message": "correct_text is required."}
        )

    try:
        correction = CorrectionService.confirm_correction(request)
        return correction
    except Exception as e:
        logger.error(f"Failed to confirm correction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": True, "message": f"Failed to save correction: {str(e)}"}
        )


@router.get(
    "/{user_id}",
    response_model=CorrectionListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User Corrections",
    description="Retrieves all active personalized STT corrections stored for the specified user.",
    tags=["Corrections"]
)
async def get_user_corrections(
    user_id: str = Path(..., description="Unique user identifier")
) -> CorrectionListResponse:
    """List all personalized corrections for a user."""
    corrections = CorrectionService.get_user_corrections(user_id)
    return CorrectionListResponse(
        user_id=user_id,
        total_count=len(corrections),
        corrections=corrections,
    )
