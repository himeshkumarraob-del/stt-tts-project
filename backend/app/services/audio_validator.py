import io
import wave
import mutagen
from typing import Tuple, Optional, Dict, Any
from app.core.config import settings
from app.core.errors import (
    AudioValidationError,
    AudioFormatNotSupportedError,
    AudioFileSizeExceededError,
    AudioCorruptError,
    AudioMimeTypeMismatchError,
)
from app.schemas.audio import AudioMetadata, AudioValidationResponse
from app.core.logging import logger


class AudioValidatorService:
    """Service responsible for deep inspection of uploaded audio bytes, headers, format integrity, and metadata."""

    # Magic byte signatures for audio containers/formats
    MAGIC_SIGNATURES = {
        b"RIFF": "wav",
        b"ID3": "mp3",
        b"\xff\xfb": "mp3",
        b"\xff\xf3": "mp3",
        b"\xff\xf2": "mp3",
        b"OggS": "ogg",
        b"fLaC": "flac",
        b"\x1a\x45\xdf\xa3": "webm",
    }

    # Expected MIME prefixes / substrings per format
    FORMAT_MIME_MAP = {
        "wav": ["audio/wav", "audio/x-wav", "audio/wave"],
        "mp3": ["audio/mpeg", "audio/mp3"],
        "ogg": ["audio/ogg", "application/ogg"],
        "flac": ["audio/flac", "audio/x-flac"],
        "m4a": ["audio/mp4", "audio/x-m4a", "audio/m4a", "video/mp4"],
        "webm": ["audio/webm", "video/webm"],
    }

    @classmethod
    def detect_format_from_bytes(cls, content: bytes) -> Optional[str]:
        """Sniff magic numbers at the start of audio bytes."""
        if len(content) < 4:
            return None
        
        for sig, fmt in cls.MAGIC_SIGNATURES.items():
            if content.startswith(sig):
                return fmt

        # Check for M4A / MP4 ISO box (ftyp)
        if len(content) >= 12 and content[4:8] == b"ftyp":
            return "m4a"

        return None

    @classmethod
    def validate_audio(
        cls,
        file_bytes: bytes,
        filename: str,
        content_type: Optional[str] = None
    ) -> AudioValidationResponse:
        """Deep inspect and validate audio bytes against size, magic header, MIME alignment, corruption, and duration limits."""
        logger.info(f"Validating audio file: '{filename}', size: {len(file_bytes)} bytes, content_type: '{content_type}'")

        if not filename or not filename.strip():
            raise AudioValidationError("Audio filename cannot be empty.")

        file_size = len(file_bytes)
        if file_size == 0:
            raise AudioValidationError("Audio file is completely empty (0 bytes).")

        # 1. Size Constraints Check
        if file_size > settings.MAX_AUDIO_SIZE_BYTES:
            raise AudioFileSizeExceededError(
                f"File size {file_size} bytes exceeds maximum limit of {settings.MAX_AUDIO_SIZE_BYTES} bytes."
            )

        # 2. Extension Check
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if not ext or ext not in settings.ALLOWED_AUDIO_EXTENSIONS:
            raise AudioFormatNotSupportedError(
                f"File extension '.{ext}' is not supported. Allowed formats: {settings.ALLOWED_AUDIO_EXTENSIONS}"
            )

        # 3. Magic Bytes / Header Inspection (Sniffing actual payload header)
        sniffed_format = cls.detect_format_from_bytes(file_bytes)

        # 4. MIME Type / Header / Extension Mismatch Inspection
        # If the file header is recognized and contradicts the filename extension (e.g., MP3 header in .wav file)
        if sniffed_format and ext:
            if sniffed_format == "mp3" and ext in ["wav", "flac", "ogg"]:
                raise AudioMimeTypeMismatchError(
                    f"File extension '.{ext}' does not match the actual inspected file header ('{sniffed_format}')."
                )
            elif sniffed_format == "wav" and ext in ["mp3", "flac", "ogg", "m4a"]:
                raise AudioMimeTypeMismatchError(
                    f"File extension '.{ext}' does not match the actual inspected file header ('{sniffed_format}')."
                )
            elif sniffed_format == "flac" and ext in ["wav", "mp3", "ogg"]:
                raise AudioMimeTypeMismatchError(
                    f"File extension '.{ext}' does not match the actual inspected file header ('{sniffed_format}')."
                )

        # Also check MIME type mismatch if explicitly provided and not generic octet-stream
        if content_type and content_type != "application/octet-stream" and sniffed_format:
            expected_mimes = cls.FORMAT_MIME_MAP.get(sniffed_format, [])
            if expected_mimes and not any(content_type.lower().startswith(m) for m in expected_mimes):
                # E.g., Content-Type declared as audio/mp3 but header is WAV RIFF
                logger.warning(f"MIME type '{content_type}' does not match detected format '{sniffed_format}'")

        # 5. Parse detailed audio metadata & verify decoding
        duration_sec = None
        sample_rate = None
        channels = None
        detected_fmt = sniffed_format or ext

        parsed_successfully = False

        # Attempt WAV parsing via stdlib wave module
        if ext == "wav" or sniffed_format == "wav":
            try:
                with wave.open(io.BytesIO(file_bytes), "rb") as wf:
                    frames = wf.getnframes()
                    sample_rate = wf.getframerate()
                    channels = wf.getnchannels()
                    if sample_rate > 0:
                        duration_sec = round(frames / float(sample_rate), 3)
                    detected_fmt = "wav"
                    parsed_successfully = True
            except Exception as e:
                logger.warning(f"Wave module parsing failed on {filename}: {e}")

        # Attempt Mutagen parsing for MP3, OGG, FLAC, M4A, etc.
        if not parsed_successfully:
            try:
                audio_file = mutagen.File(io.BytesIO(file_bytes))
                if audio_file is not None and audio_file.info is not None:
                    duration_sec = round(audio_file.info.length, 3) if hasattr(audio_file.info, "length") else None
                    sample_rate = getattr(audio_file.info, "sample_rate", None)
                    channels = getattr(audio_file.info, "channels", None)
                    detected_fmt = sniffed_format or ext
                    parsed_successfully = True
            except Exception as e:
                logger.warning(f"Mutagen parsing failed on {filename}: {e}")

        # If audio payload could not be decoded by any audio parser, reject early with a 400 error
        if not parsed_successfully:
            raise AudioCorruptError(
                f"Uploaded file '{filename}' is corrupt, unreadable, or contains invalid audio frames."
            )

        # 6. Duration Constraints Check (Min 0.5s, Max 120s)
        if duration_sec is None:
            raise AudioCorruptError(
                f"Could not determine valid duration for audio file '{filename}'."
            )

        if duration_sec < settings.MIN_AUDIO_DURATION_SEC:
            raise AudioValidationError(
                f"Audio duration ({duration_sec}s) is shorter than minimum required ({settings.MIN_AUDIO_DURATION_SEC}s)."
            )
        if duration_sec > settings.MAX_AUDIO_DURATION_SEC:
            raise AudioValidationError(
                f"Audio duration ({duration_sec}s) exceeds maximum allowed ({settings.MAX_AUDIO_DURATION_SEC}s)."
            )

        metadata = AudioMetadata(
            filename=filename,
            content_type=content_type,
            extension=ext,
            file_size_bytes=file_size,
            duration_seconds=duration_sec,
            sample_rate=sample_rate,
            channels=channels,
            format=detected_fmt,
        )

        return AudioValidationResponse(
            valid=True,
            message="Audio successfully passed all validation checks.",
            metadata=metadata,
            diagnostics={
                "size_check": "PASS",
                "format_check": "PASS",
                "header_sniff_format": sniffed_format,
                "duration_check": "PASS" if duration_sec is not None else "SKIPPED_UNPARSED_DURATION",
            }
        )
