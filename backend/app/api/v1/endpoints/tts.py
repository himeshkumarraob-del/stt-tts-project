"""API endpoint for Text-to-Speech (TTS) Synthesis."""
from fastapi import APIRouter, status, Body, HTTPException, Response
from app.schemas.tts import TTSSynthesizeRequest, TTSSynthesizeResponse
from app.services.tts import TTSService
from app.core.logging import logger

router = APIRouter()


@router.post(
    "/synthesize",
    response_model=TTSSynthesizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Synthesize Text to Speech",
    description="Synthesizes input text into speech audio with selectable voice and format. "
                "Returns audio payload in base64 format with metadata, or raw audio stream if requested.",
    tags=["TTS"]
)
async def synthesize_speech(
    request: TTSSynthesizeRequest = Body(..., description="Speech synthesis request payload"),
    raw_audio: bool = False,
):
    """Synthesize text into speech audio."""
    try:
        audio_bytes, response_meta = await TTSService.synthesize(
            text=request.text,
            voice=request.voice,
            audio_format=request.audio_format,
        )

        if raw_audio:
            media_type = f"audio/{request.audio_format or 'mpeg'}"
            return Response(
                content=audio_bytes,
                media_type=media_type,
                headers={"X-TTS-Provider": response_meta.provider, "X-TTS-Model": response_meta.model},
            )

        return response_meta

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": True, "message": str(e)}
        )
    except Exception as e:
        logger.error(f"TTS synthesis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": True, "message": f"Speech synthesis failed: {str(e)}"}
        )
