from fastapi import APIRouter, status
from app.schemas.health import HealthResponse
from app.core.config import settings

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns the current operational status, environment, and diagnostics of the backend API.",
    tags=["System"]
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        version="0.1.0",
        details={
            "debug": settings.DEBUG,
            "max_audio_size_mb": round(settings.MAX_AUDIO_SIZE_BYTES / (1024 * 1024), 2),
            "allowed_formats": settings.ALLOWED_AUDIO_EXTENSIONS,
        }
    )
