"""Pydantic schemas for AI Feedback and Personalized Learning (Phase 5)."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.schemas.stt import TranscriptionResponse
from app.schemas.pronunciation import PronunciationAssessmentResponse
from app.schemas.accent import AccentAnalysisResponse


class PracticeExercise(BaseModel):
    """Structured practice exercise or phonetic drill."""
    title: str = Field(..., description="Title of the exercise")
    exercise_type: str = Field(..., description="Type of exercise (e.g. minimal_pair, pacing, intonation, tongue_twister)")
    target_words: List[str] = Field(default_factory=list, description="Key target words to focus on")
    instructions: str = Field(..., description="Step-by-step practice instructions")
    sample_sentence: Optional[str] = Field(None, description="Practice sentence for the user to read aloud")


class ScoresSummary(BaseModel):
    """Preserved, unaltered evaluation scores from Phase 2-4."""
    overall_pronunciation_score: float = Field(..., ge=0.0, le=100.0, description="Unaltered overall pronunciation score")
    pronunciation_confidence: float = Field(..., ge=0.0, le=1.0, description="Pronunciation assessment confidence")
    accent_label: str = Field(..., description="Accent classification label")
    accent_model_status: str = Field(..., description="Accent model calibration status")
    accent_confidence: float = Field(..., ge=0.0, le=1.0, description="Accent classifier confidence")
    words_total: int = Field(..., description="Total words evaluated")
    words_correct: int = Field(..., description="Number of correctly pronounced words")
    issues_detected_count: int = Field(..., description="Count of detected pronunciation issues")


class FeedbackGenerationRequest(BaseModel):
    """Input payload for generating personalized AI feedback."""
    stt_result: TranscriptionResponse = Field(..., description="Verified Speech-to-Text result from Phase 2")
    pronunciation_result: PronunciationAssessmentResponse = Field(..., description="Verified Pronunciation Assessment from Phase 3")
    accent_result: AccentAnalysisResponse = Field(..., description="Verified Accent Analysis result from Phase 4")
    user_id: Optional[str] = Field(None, description="Optional user identifier for session tracking")
    session_id: Optional[str] = Field(None, description="Optional session identifier")


class FeedbackResponse(BaseModel):
    """Structured personalized learning feedback output."""
    overall_summary: str = Field(..., description="Encouraging summary of the speaker's overall performance")
    pronunciation_feedback: str = Field(..., description="Analysis of pronunciation accuracy and phonetic clarity")
    accent_feedback: str = Field(..., description="Objective acoustic and prosodic observations")
    strengths: List[str] = Field(default_factory=list, description="Identified speech strengths")
    areas_to_improve: List[str] = Field(default_factory=list, description="Specific areas to focus on for improvement")
    practice_recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")
    suggested_exercises: List[PracticeExercise] = Field(default_factory=list, description="Concrete practice drills")
    scores_summary: ScoresSummary = Field(..., description="Preserved, unaltered numerical metrics")
    is_fallback: bool = Field(False, description="Whether this response was generated via deterministic fallback")
    provider: str = Field(..., description="Feedback provider (e.g. openai, deterministic_fallback)")
    model: str = Field(..., description="Model name or engine used")
