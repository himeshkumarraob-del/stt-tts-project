import io
import time
from typing import Optional, List
from app.services.stt.base import BaseSTTProvider
from app.schemas.stt import TranscriptionResponse, TranscriptionSegment
from app.core.config import settings
from app.core.errors import STTModelLoadError, STTTranscriptionError
from app.core.logging import logger


class FasterWhisperProvider(BaseSTTProvider):
    """Faster-Whisper STT Provider implementation running quantized CTranslate2 models."""

    def __init__(
        self,
        model_size: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ):
        self._model_size = model_size or settings.STT_MODEL
        self._device = device or settings.STT_DEVICE
        self._compute_type = compute_type or settings.STT_COMPUTE_TYPE
        self._model = None

    @property
    def provider_name(self) -> str:
        return "faster-whisper"

    @property
    def model_name(self) -> str:
        return self._model_size

    def _get_model(self):
        """Lazy load the WhisperModel instance with safe error handling."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel

                logger.info(
                    f"Loading faster-whisper model '{self._model_size}' "
                    f"on device='{self._device}', compute_type='{self._compute_type}'..."
                )
                self._model = WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                logger.info(f"Faster-whisper model '{self._model_size}' loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load faster-whisper model '{self._model_size}': {str(e)}", exc_info=True)
                raise STTModelLoadError(
                    message=f"Failed to initialize STT model '{self._model_size}': {str(e)}",
                    details={"model": self._model_size, "device": self._device}
                )
        return self._model

    def transcribe(
        self,
        audio_bytes: bytes,
        audio_duration_seconds: float,
        language: Optional[str] = "en",
        filename: Optional[str] = None,
    ) -> TranscriptionResponse:
        """Transcribe audio bytes using faster-whisper without altering accent or grammar."""
        model = self._get_model()
        start_time = time.perf_counter()

        try:
            audio_stream = io.BytesIO(audio_bytes)
            
            # Note: We do not pass initial_prompt that enforces grammar alterations.
            # language='en' ensures English decoding (including Indian-English phonetic variations).
            segments_gen, info = model.transcribe(
                audio_stream,
                beam_size=settings.STT_BEAM_SIZE,
                language=language or settings.STT_LANGUAGE,
                vad_filter=True,  # Filter out background noise silences
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            segments: List[TranscriptionSegment] = []
            full_text_pieces: List[str] = []

            for seg in segments_gen:
                text_clean = seg.text.strip()
                if text_clean:
                    full_text_pieces.append(text_clean)
                segments.append(
                    TranscriptionSegment(
                        id=seg.id,
                        start=round(seg.start, 3),
                        end=round(seg.end, 3),
                        text=text_clean,
                        avg_logprob=round(seg.avg_logprob, 4) if getattr(seg, "avg_logprob", None) is not None else None,
                        no_speech_prob=round(seg.no_speech_prob, 4) if getattr(seg, "no_speech_prob", None) is not None else None,
                    )
                )

            processing_time = round(time.perf_counter() - start_time, 4)
            full_text = " ".join(full_text_pieces).strip()

            detected_or_used_lang = info.language if hasattr(info, "language") and info.language else (language or "en")

            return TranscriptionResponse(
                text=full_text,
                language=detected_or_used_lang,
                duration_seconds=round(audio_duration_seconds, 3),
                processing_time_seconds=processing_time,
                provider=self.provider_name,
                model=self.model_name,
                segments=segments,
                metadata={
                    "all_language_probabilities": (
                        {lang: round(prob, 4) for lang, prob in list(info.all_language_probs.items())[:5]}
                        if getattr(info, "all_language_probs", None) else {}
                    ),
                    "filename": filename,
                }
            )
        except STTModelLoadError:
            raise
        except Exception as e:
            logger.error(f"STT transcription execution error: {str(e)}", exc_info=True)
            raise STTTranscriptionError(
                message=f"Speech-to-Text transcription failed: {str(e)}",
                details={"provider": self.provider_name, "model": self.model_name}
            )

