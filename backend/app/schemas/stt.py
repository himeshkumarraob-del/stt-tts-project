from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class TranscriptionSegment(BaseModel):
    id: int = Field(..., description="Segment identifier")
    start: float = Field(..., description="Start timestamp in seconds")
    end: float = Field(..., description="End timestamp in seconds")
    text: str = Field(..., description="Transcribed text segment")
    avg_logprob: Optional[float] = Field(None, description="Average log probability")
    no_speech_prob: Optional[float] = Field(None, description="Probability that segment contains no speech")


class TranscriptionResponse(BaseModel):
    text: str = Field(..., description="Full transcribed text verbatim as spoken")
    language: str = Field(..., description="Detected or configured language code (e.g. 'en')")
    duration_seconds: float = Field(..., description="Duration of the processed audio in seconds")
    processing_time_seconds: float = Field(..., description="Total STT processing time in seconds")
    provider: str = Field(..., description="STT Provider used (e.g. 'faster-whisper')")
    model: str = Field(..., description="STT Model name or size (e.g. 'base.en')")
    segments: List[TranscriptionSegment] = Field(default_factory=list, description="Word/sentence timestamps")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional extraction diagnostics")
