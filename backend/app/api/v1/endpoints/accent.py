"""API endpoint for Indian-English Accent Analysis."""
from fastapi import APIRouter, UploadFile, File, status, HTTPException
from app.schemas.accent import AccentAnalysisResponse
from app.services.accent import AccentService
from app.core.logging import logger

router = APIRouter()


@router.post(
    "/analyze",
    response_model=AccentAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Accent Characteristics",
    description="Accepts an audio file upload, validates audio integrity, extracts acoustic/prosodic/spectral features "
                "(MFCCs, pitch/F0 variation, speech/articulation rate, spectral brightness, zero-crossing rate), "
                "and performs accent analysis with explicit calibration status.",
    tags=["Accent"]
)
async def analyze_accent(
    file: UploadFile = File(..., description="User recorded audio file (wav, mp3, m4a, ogg, flac, webm)")
) -> AccentAnalysisResponse:
    """Analyze audio recording for accent and acoustic speech characteristics."""
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "No audio file uploaded or filename is missing."}
        )

    try:
        content = await file.read()
        analysis = AccentService.analyze_accent(
            audio_bytes=content,
            filename=file.filename,
            content_type=file.content_type,
        )
        return analysis
    finally:
        await file.close()
