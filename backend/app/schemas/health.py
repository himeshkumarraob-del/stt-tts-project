from pydantic import BaseModel, Field
from typing import Dict, Any


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status", json_schema_extra={"example": "healthy"})
    app_name: str = Field(..., description="Application name")
    environment: str = Field(..., description="Application environment")
    version: str = Field("0.1.0", description="API version")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional health diagnostics")
