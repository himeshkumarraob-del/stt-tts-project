from fastapi import APIRouter, UploadFile, File, status, HTTPException
from app.schemas.audio import AudioValidationResponse
from app.services.audio_validator import AudioValidatorService
from app.core.errors import AppBaseException
from app.core.logging import logger

router = APIRouter()


@router.post(
    "/validate",
    response_model=AudioValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate Audio File",
    description="Accepts an audio file upload, verifies file format/magic bytes, size constraints, and integrity.",
    tags=["Audio"]
)
async def validate_audio_file(
    file: UploadFile = File(..., description="Audio file to validate (wav, mp3, m4a, ogg, flac, webm)")
) -> AudioValidationResponse:
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "No file uploaded or filename is missing."}
        )

    try:
        content = await file.read()
        validation_result = AudioValidatorService.validate_audio(
            file_bytes=content,
            filename=file.filename,
            content_type=file.content_type
        )
        return validation_result
    finally:
        await file.close()

