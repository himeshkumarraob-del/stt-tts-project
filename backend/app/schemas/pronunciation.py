from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class WordStatus(str, Enum):
    CORRECT = "correct"
    ACCEPTABLE_VARIANT = "acceptable_variant"
    MISPRONOUNCED = "mispronounced"
    SUBSTITUTION = "substitution"
    OMISSION = "omission"
    INSERTION = "insertion"


class PhonemeAssessment(BaseModel):
    phoneme: str = Field(..., description="Target ARPAbet/IPA phoneme symbol")
    score: float = Field(
        ...,
        description="Word-level acoustic posterior mapped to constituent phonemes (0-100). "
                    "Note: This is an inherited word-level acoustic metric, not independent phoneme-boundary forced alignment."
    )
    status: str = Field(..., description="Phoneme status classification ('correct', 'acceptable_variant', 'substituted', 'omitted')")
    start: Optional[float] = Field(None, description="Word boundary start timestamp in seconds")
    end: Optional[float] = Field(None, description="Word boundary end timestamp in seconds")
    is_derived: bool = Field(
        True,
        description="True indicating this phoneme score is inherited from word-level acoustic posterior probability."
    )


class WordAssessment(BaseModel):
    target: Optional[str] = Field(None, description="Target word from the requested sentence")
    spoken: Optional[str] = Field(None, description="Actual spoken word recognized from audio")
    score: float = Field(..., description="Word-level pronunciation score (0-100) derived from acoustic confidence and alignment")
    status: WordStatus = Field(..., description="Alignment & pronunciation status classification")
    start: Optional[float] = Field(None, description="Word start time in seconds")
    end: Optional[float] = Field(None, description="Word end time in seconds")
    acoustic_confidence: float = Field(..., description="Acoustic posterior probability from speech model (0.0 - 1.0)")
    phonemes: List[PhonemeAssessment] = Field(default_factory=list, description="Phonemic representation with inherited word acoustic scores")
    notes: Optional[str] = Field(None, description="Pronunciation diagnostic notes (e.g., retroflex variation)")


class PronunciationIssue(BaseModel):
    index: int = Field(..., description="Index of target or spoken token")
    word: str = Field(..., description="Word containing pronunciation or alignment issue")
    issue_type: str = Field(..., description="Type of issue ('omission', 'mispronunciation', 'substitution', 'insertion')")
    description: str = Field(..., description="Human-readable description of the pronunciation difference")
    severity: str = Field("medium", description="Issue severity: 'low', 'medium', 'high'")


class PronunciationAssessmentResponse(BaseModel):
    target_text: str = Field(..., description="Target sentence requested for assessment")
    transcript: str = Field(..., description="Actual verbatim transcript recognized from audio")
    overall_score: float = Field(..., description="Composite engineering pronunciation score (0-100)")
    confidence: float = Field(..., description="Mean acoustic confidence across evaluated words (0.0 - 1.0)")
    duration_seconds: float = Field(..., description="Duration of the audio recording in seconds")
    processing_time_seconds: float = Field(..., description="Total processing time taken for assessment in seconds")
    words: List[WordAssessment] = Field(..., description="Word-by-word alignment and score breakdown")
    phonemes: List[PhonemeAssessment] = Field(default_factory=list, description="Constituent phonemes across utterance")
    issues: List[PronunciationIssue] = Field(default_factory=list, description="Identified pronunciation and alignment issues")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic, alignment, and methodology metadata")
