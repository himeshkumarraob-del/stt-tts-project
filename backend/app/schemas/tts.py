"""Pydantic schemas for Text-to-Speech (TTS)."""
from typing import Optional
from pydantic import BaseModel, Field


class TTSSynthesizeRequest(BaseModel):
    """Request schema for speech synthesis."""
    text: str = Field(..., min_length=1, max_length=4096, description="Text string to synthesize into speech")
    voice: Optional[str] = Field("alloy", description="Voice persona (e.g. alloy, echo, fable, onyx, nova, shimmer)")
    audio_format: Optional[str] = Field("mp3", description="Audio output format (mp3, wav, opus, aac)")


class TTSSynthesizeResponse(BaseModel):
    """Response schema containing synthesized audio metadata."""
    audio_base64: Optional[str] = Field(None, description="Base64-encoded audio payload if requested inline")
    format: str = Field(..., description="Audio container format (e.g. mp3, wav)")
    voice: str = Field(..., description="Voice model/persona used")
    provider: str = Field(..., description="TTS provider (e.g. openai, fallback)")
    model: str = Field(..., description="TTS model identifier")
    character_count: int = Field(..., description="Length of synthesized text in characters")
    is_fallback: bool = Field(False, description="Whether fallback synthesis was used")
