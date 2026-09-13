from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class AudioMetadata(BaseModel):
    filename: str = Field(..., description="Original name of the uploaded audio file")
    content_type: Optional[str] = Field(None, description="MIME type of the uploaded file")
    extension: str = Field(..., description="File extension")
    file_size_bytes: int = Field(..., description="Audio file size in bytes")
    duration_seconds: Optional[float] = Field(None, description="Audio length in seconds if decodable")
    sample_rate: Optional[int] = Field(None, description="Sample rate in Hz if detected")
    channels: Optional[int] = Field(None, description="Audio channels (1=mono, 2=stereo) if detected")
    format: Optional[str] = Field(None, description="Detected audio format / container")


class AudioValidationResponse(BaseModel):
    valid: bool = Field(..., description="True if the audio passed all validation checks")
    message: str = Field(..., description="Validation outcome message")
    metadata: AudioMetadata = Field(..., description="Extracted audio file metadata")
    diagnostics: Dict[str, Any] = Field(default_factory=dict, description="Additional validation checks passed")
