from fastapi import APIRouter, UploadFile, File, Form, status, HTTPException
from app.schemas.pronunciation import PronunciationAssessmentResponse
from app.services.pronunciation import PronunciationService
from app.core.logging import logger

router = APIRouter()


@router.post(
    "/assess",
    response_model=PronunciationAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Assess Pronunciation",
    description="Compares user-spoken audio recording against a target text prompt. "
                "Performs acoustic time-alignment, word-level scoring, phoneme analysis, "
                "omission/substitution detection, and generates an overall pronunciation assessment.",
    tags=["Pronunciation"]
)
async def assess_pronunciation(
    target_text: str = Form(..., description="The target sentence/phrase the user was asked to speak"),
    file: UploadFile = File(..., description="User recorded audio file (wav, mp3, m4a, ogg, flac, webm)")
) -> PronunciationAssessmentResponse:
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "No audio file uploaded or filename is missing."}
        )

    try:
        content = await file.read()
        assessment = PronunciationService.assess_pronunciation(
            target_text=target_text,
            audio_bytes=content,
            filename=file.filename,
            content_type=file.content_type,
        )
        return assessment
    finally:
        await file.close()
