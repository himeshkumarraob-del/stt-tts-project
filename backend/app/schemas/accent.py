"""Accent analysis schemas."""
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class AccentLabel(str, Enum):
    """Supported accent classifications."""
    INDIAN_ENGLISH = "indian_english"
    NON_INDIAN_ENGLISH = "non_indian_english"
    UNKNOWN = "unknown"


class ModelStatus(str, Enum):
    """Status and calibration state of the classification model."""
    TRAINED = "trained"
    NOT_CALIBRATED = "not_calibrated"
    UNKNOWN = "unknown"


class AcousticFeatures(BaseModel):
    """Extracted acoustic and prosodic features."""
    pitch_f0_mean_hz: float = Field(..., description="Mean fundamental frequency (F0) in Hertz")
    pitch_f0_std_hz: float = Field(..., description="Standard deviation of F0 in Hertz (pitch variability)")
    pitch_f0_range_hz: float = Field(..., description="Range between 95th and 5th percentile F0")
    speech_rate_syllables_per_sec: float = Field(..., description="Estimated syllable rate per second")
    articulation_rate: float = Field(..., description="Estimated syllables per second of active phonation")
    pause_duration_ratio: float = Field(..., description="Ratio of silent/pause frames to total frames")
    spectral_centroid_mean: float = Field(..., description="Mean spectral brightness/centroid")
    spectral_rolloff_mean: float = Field(..., description="Mean spectral roll-off point (85% energy)")
    spectral_flatness_mean: float = Field(..., description="Mean spectral flatness/noisiness")
    zero_crossing_rate_mean: float = Field(..., description="Mean zero crossing rate (consonant frication indicator)")
    energy_rms_mean: float = Field(..., description="Mean root mean square energy")
    energy_rms_std: float = Field(..., description="Standard deviation of RMS energy (dynamic range)")
    mfcc_mean: List[float] = Field(..., description="Mean of 13 MFCC coefficients")
    mfcc_std: List[float] = Field(..., description="Standard deviation of 13 MFCC coefficients")


class AccentMetadata(BaseModel):
    """Model information, versioning, and processing details."""
    model_name: str = Field(..., description="Name of the accent classifier model")
    model_version: str = Field(..., description="Semantic version of the model")
    model_type: str = Field(..., description="Architecture type (e.g. acoustic_prosody_baseline, xlsr_classifier)")
    training_dataset: Optional[str] = Field(None, description="Dataset used if trained, otherwise None")
    training_date: Optional[str] = Field(None, description="Training date if applicable")
    duration_seconds: float = Field(..., description="Processed audio duration in seconds")
    sample_rate: int = Field(..., description="Audio sample rate in Hertz")


class AccentAnalysisResponse(BaseModel):
    """Response schema for accent analysis endpoint."""
    accent: AccentLabel = Field(..., description="Classified accent label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score [0.0 - 1.0]")
    model_status: ModelStatus = Field(..., description="Model calibration status")
    features: AcousticFeatures = Field(..., description="Extracted acoustic and prosodic features")
    explanation: List[str] = Field(default_factory=list, description="Descriptive observations of acoustic characteristics")
    metadata: AccentMetadata = Field(..., description="Model metadata and processing parameters")
