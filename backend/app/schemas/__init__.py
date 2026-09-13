"""Pydantic schemas package."""
from app.schemas.health import HealthResponse
from app.schemas.audio import AudioValidationResponse, AudioMetadata
from app.schemas.stt import TranscriptionResponse, TranscriptionSegment
from app.schemas.pronunciation import (
    PronunciationAssessmentResponse,
    WordAssessment,
    PhonemeAssessment,
    PronunciationIssue,
    WordStatus,
)
from app.schemas.accent import (
    AccentLabel,
    ModelStatus,
    AcousticFeatures,
    AccentMetadata,
    AccentAnalysisResponse,
)
from app.schemas.feedback import (
    PracticeExercise,
    ScoresSummary,
    FeedbackGenerationRequest,
    FeedbackResponse,
)
from app.schemas.correction import (
    CorrectionConfirmRequest,
    CorrectionResponse,
    CorrectionListResponse,
)
from app.schemas.tts import (
    TTSSynthesizeRequest,
    TTSSynthesizeResponse,
)
from app.schemas.voice_learning import (
    PipelineTimings,
    VoiceLearningProcessResponse,
)

__all__ = [
    "HealthResponse",
    "AudioValidationResponse",
    "AudioMetadata",
    "TranscriptionResponse",
    "TranscriptionSegment",
    "PronunciationAssessmentResponse",
    "WordAssessment",
    "PhonemeAssessment",
    "PronunciationIssue",
    "WordStatus",
    "AccentLabel",
    "ModelStatus",
    "AcousticFeatures",
    "AccentMetadata",
    "AccentAnalysisResponse",
    "PracticeExercise",
    "ScoresSummary",
    "FeedbackGenerationRequest",
    "FeedbackResponse",
    "CorrectionConfirmRequest",
    "CorrectionResponse",
    "CorrectionListResponse",
    "TTSSynthesizeRequest",
    "TTSSynthesizeResponse",
    "PipelineTimings",
    "VoiceLearningProcessResponse",
]
