from typing import List, Union, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "Voice Learning & Accent Analysis Backend"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    API_V1_STR: str = "/api/v1"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Audio Validation & Constraints
    MAX_AUDIO_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    ALLOWED_AUDIO_EXTENSIONS: List[str] = [
        "wav", "mp3", "m4a", "ogg", "flac", "aac", "webm"
    ]
    MIN_AUDIO_DURATION_SEC: float = 0.5
    MAX_AUDIO_DURATION_SEC: float = 120.0

    # Speech-to-Text (STT) Settings
    STT_PROVIDER: str = "faster-whisper"
    STT_MODEL: str = "base.en"  # Lightweight model suitable for development laptops
    STT_DEVICE: str = "cpu"     # Safe default for development (cpu / cuda)
    STT_COMPUTE_TYPE: str = "int8"  # int8 / float32 / float16
    STT_LANGUAGE: Optional[str] = "en"  # Default to English (supports Indian-English verbatim)
    STT_BEAM_SIZE: int = 5

    # Pronunciation Assessment Settings
    PRONUNCIATION_MAX_TARGET_LEN: int = 1000  # Characters max for target text
    PRONUNCIATION_ACCEPT_INDIAN_ENGLISH_VARIANTS: bool = True

    # AI Feedback & LLM Settings (Phase 5)
    LLM_PROVIDER: str = "openai"  # openai / mock / custom
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: Optional[str] = None  # Custom OpenAI-compatible base URL if provided
    LLM_TIMEOUT_SECONDS: float = 15.0
    LLM_TEMPERATURE: float = 0.3

    # Text-to-Speech (TTS) Settings (Phase 6)
    TTS_PROVIDER: str = "openai"  # openai / fallback
    TTS_MODEL: str = "tts-1"
    TTS_VOICE: str = "alloy"
    TTS_AUDIO_FORMAT: str = "mp3"
    TTS_TIMEOUT_SECONDS: float = 15.0
    TTS_MAX_TEXT_LEN: int = 4096

    # Database Settings (Phase 6)
    DB_PATH: str = "voice_learning.db"

    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()
