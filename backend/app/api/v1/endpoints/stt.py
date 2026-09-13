from fastapi import APIRouter, UploadFile, File, Form, status, HTTPException
from typing import Optional
from app.schemas.stt import TranscriptionResponse
from app.services.stt import STTService
from app.core.logging import logger

router = APIRouter()


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe Speech to Text",
    description="Transcribes an uploaded audio file into text using the configured STT provider (faster-whisper). "
                "Audio is validated through the Phase 1 validation pipeline before inference.",
    tags=["STT"]
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio recording to transcribe (wav, mp3, m4a, ogg, flac, webm)"),
    language: Optional[str] = Form("en", description="Target language code (defaults to 'en')"),
    provider: Optional[str] = Form(None, description="Optional STT provider override (defaults to configured STT_PROVIDER)")
) -> TranscriptionResponse:
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "No audio file uploaded or filename is missing."}
        )

    try:
        content = await file.read()
        transcription = STTService.transcribe_audio(
            audio_bytes=content,
            filename=file.filename,
            content_type=file.content_type,
            language=language,
            provider_name=provider,
        )
        return transcription
    finally:
        await file.close()
