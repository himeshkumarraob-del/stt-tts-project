"""Pydantic schemas for Personalized STT Correction Memory."""
from typing import Optional, List
from pydantic import BaseModel, Field


class CorrectionConfirmRequest(BaseModel):
    """Request payload for confirming a user-specific STT correction."""
    user_id: str = Field(..., description="Unique user identifier for personalized memory")
    incorrect_text: str = Field(..., description="Incorrect word/phrase recognized by STT (e.g. 'image')")
    correct_text: str = Field(..., description="Actual intended word/phrase (e.g. 'Himesh')")
    context: Optional[str] = Field(None, description="Optional surrounding context trigger (e.g. 'my name is')")


class CorrectionResponse(BaseModel):
    """Details of a confirmed persistent user correction."""
    id: str = Field(..., description="Unique correction record ID")
    user_id: str = Field(..., description="User ID owning the correction")
    incorrect_text: str = Field(..., description="Incorrect text recognized by STT")
    correct_text: str = Field(..., description="Intended replacement text")
    context_phrase: Optional[str] = Field(None, description="Context phrase trigger if restricted")
    occurrence_count: int = Field(1, description="Number of times this correction was confirmed/applied")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence weighting of the correction")
    created_at: str = Field(..., description="Timestamp of initial creation")
    updated_at: str = Field(..., description="Timestamp of last update")


class CorrectionListResponse(BaseModel):
    """List of all confirmed corrections for a specific user."""
    user_id: str = Field(..., description="User identifier")
    total_count: int = Field(..., description="Total active corrections for user")
    corrections: List[CorrectionResponse] = Field(default_factory=list, description="List of corrections")
