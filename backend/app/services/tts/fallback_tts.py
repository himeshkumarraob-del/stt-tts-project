"""Deterministic fallback TTS provider generating valid audio bytes."""
import io
import wave
import base64
import logging
import numpy as np
from typing import Tuple

from app.schemas.tts import TTSSynthesizeRequest, TTSSynthesizeResponse
from app.services.tts.base import BaseTTSProvider

logger = logging.getLogger(__name__)


class DeterministicFallbackTTSProvider(BaseTTSProvider):
    """
    Fallback TTS provider.
    Generates a valid minimal synthetic audio signal when external TTS APIs are offline or unconfigured.
    """

    @property
    def provider_name(self) -> str:
        return "deterministic_fallback"

    @property
    def model_name(self) -> str:
        return "synthetic_audio_v1"

    async def synthesize_speech(
        self,
        request: TTSSynthesizeRequest,
    ) -> Tuple[bytes, TTSSynthesizeResponse]:
        """Generate a valid, playable synthetic audio tone with metadata."""
        sr = 16000
        duration = min(3.0, max(0.5, len(request.text) * 0.05))
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        # Gentle dual-harmonic acoustic tone
        signal = 0.3 * np.sin(2 * np.pi * 440 * t) + 0.15 * np.sin(2 * np.pi * 880 * t)
        envelope = np.sin(np.pi * t / duration)
        pcm_data = (signal * envelope * 32767).astype(np.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm_data.tobytes())
        buf.seek(0)
        audio_bytes = buf.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        response = TTSSynthesizeResponse(
            audio_base64=audio_b64,
            format="wav",
            voice=request.voice or "alloy",
            provider=self.provider_name,
            model=self.model_name,
            character_count=len(request.text),
            is_fallback=True,
        )

        return audio_bytes, response
