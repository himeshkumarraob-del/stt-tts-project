from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    audio,
    stt,
    pronunciation,
    accent,
    feedback,
    tts,
    corrections,
    voice_learning,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="", tags=["System"])
api_router.include_router(audio.router, prefix="/audio", tags=["Audio"])
api_router.include_router(stt.router, prefix="/stt", tags=["STT"])
api_router.include_router(pronunciation.router, prefix="/pronunciation", tags=["Pronunciation"])
api_router.include_router(accent.router, prefix="/accent", tags=["Accent"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(tts.router, prefix="/tts", tags=["TTS"])
api_router.include_router(corrections.router, prefix="/corrections", tags=["Corrections"])
api_router.include_router(voice_learning.router, prefix="/voice-learning", tags=["Voice Learning Loop"])
