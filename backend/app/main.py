from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.errors import AppBaseException
from app.api.v1.router import api_router
from app.schemas.health import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} in '{settings.APP_ENV}' mode...")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="FastAPI Backend for Voice Learning & Indian-English Accent Analysis System",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    @app.exception_handler(AppBaseException)
    async def app_base_exception_handler(request: Request, exc: AppBaseException):
        logger.warning(f"Handled application exception on {request.url.path}: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": True,
                "message": "Request validation failed",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled server error on {request.url.path}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "message": "An unexpected internal server error occurred.",
            },
        )

    # Root health shortcut (/health)
    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["System"],
        summary="Root Health Check",
        description="Direct root health endpoint."
    )
    async def root_health():
        return HealthResponse(
            status="healthy",
            app_name=settings.APP_NAME,
            environment=settings.APP_ENV,
            version="0.1.0",
            details={"debug": settings.DEBUG}
        )

    # Include API Routers under /api/v1
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app


app = create_application()
