"""Pydantic schemas for the complete End-to-End Voice Learning Loop."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.schemas.pronunciation import PronunciationAssessmentResponse
from app.schemas.accent import AccentAnalysisResponse
from app.schemas.feedback import FeedbackResponse
from app.schemas.tts import TTSSynthesizeResponse


class PipelineTimings(BaseModel):
    """Execution latency breakdown in seconds across pipeline components."""
    audio_validation_seconds: float = Field(..., description="Audio validation time in seconds")
    stt_seconds: float = Field(..., description="Speech-to-Text transcription time in seconds")
    correction_seconds: float = Field(..., description="Personalized STT correction memory time in seconds")
    pronunciation_seconds: float = Field(..., description="Pronunciation assessment time in seconds")
    accent_seconds: float = Field(..., description="Accent analysis time in seconds")
    feedback_seconds: float = Field(..., description="AI feedback generation time in seconds")
    tts_seconds: float = Field(0.0, description="Text-to-speech synthesis time in seconds")
    total_pipeline_seconds: float = Field(..., description="Total end-to-end execution latency in seconds")


class VoiceLearningProcessResponse(BaseModel):
    """Unified response payload for the complete End-to-End Voice Learning workflow."""
    attempt_id: str = Field(..., description="Unique persistent identifier for this speech attempt")
    user_id: Optional[str] = Field(None, description="User identifier associated with this practice attempt")
    original_transcript: str = Field(..., description="Unaltered verbatim transcript directly from STT")
    corrected_transcript: str = Field(..., description="Transcript after applying personalized context-aware correction memory")
    applied_corrections: List[Dict[str, Any]] = Field(default_factory=list, description="List of corrections triggered and applied")
    pronunciation_result: PronunciationAssessmentResponse = Field(..., description="Verified Pronunciation Assessment (Phase 3)")
    accent_result: AccentAnalysisResponse = Field(..., description="Verified Accent Analysis (Phase 4)")
    feedback_result: FeedbackResponse = Field(..., description="Personalized AI Feedback & Drills (Phase 5)")
    tts_result: Optional[TTSSynthesizeResponse] = Field(None, description="Optional Text-to-Speech audio result (Phase 6)")
    timings: PipelineTimings = Field(..., description="Detailed component and total latency metrics")
