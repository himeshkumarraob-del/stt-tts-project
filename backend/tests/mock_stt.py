from typing import List, Optional
from collections import namedtuple
from app.services.stt.base import BaseSTTProvider
from app.schemas.stt import TranscriptionResponse, TranscriptionSegment

MockWord = namedtuple("MockWord", ["word", "start", "end", "probability"])
MockSegment = namedtuple("MockSegment", ["id", "start", "end", "text", "avg_logprob", "no_speech_prob", "words"])
MockTranscriptionInfo = namedtuple("MockTranscriptionInfo", ["language", "all_language_probs"])


class MockWhisperModel:
    """Mock model to test FasterWhisperProvider & AcousticPronunciationAssessor without requiring network or heavy compute."""

    def __init__(self, model_size="base.en", device="cpu", compute_type="int8", mock_words: Optional[List[str]] = None, mock_probs: Optional[List[float]] = None):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.mock_words = mock_words or ["Hello", "world", "this", "is", "a", "test"]
        self.mock_probs = mock_probs or [0.98, 0.95, 0.92, 0.96, 0.99, 0.94]

    def transcribe(self, audio_stream, beam_size=5, language="en", vad_filter=True, vad_parameters=None, word_timestamps=False):
        words = []
        cur_t = 0.0
        for w, prob in zip(self.mock_words, self.mock_probs):
            words.append(MockWord(word=w, start=cur_t, end=cur_t + 0.3, probability=prob))
            cur_t += 0.35

        full_text = " ".join(self.mock_words)

        segments = [
            MockSegment(
                id=0,
                start=0.0,
                end=cur_t,
                text=full_text,
                avg_logprob=-0.15,
                no_speech_prob=0.01,
                words=words,
            )
        ]
        info = MockTranscriptionInfo(
            language=language or "en",
            all_language_probs={"en": 0.99, "hi": 0.01}
        )
        return segments, info


class MockSTTProvider(BaseSTTProvider):
    """Mock STT Provider for unit testing."""

    def __init__(self, provider_name: str = "mock-stt", model_name: str = "mock-model"):
        self._provider_name = provider_name
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def transcribe(
        self,
        audio_bytes: bytes,
        audio_duration_seconds: float,
        language: Optional[str] = "en",
        filename: Optional[str] = None,
    ) -> TranscriptionResponse:
        return TranscriptionResponse(
            text="Hello world, this is a test audio recording.",
            language=language or "en",
            duration_seconds=audio_duration_seconds,
            processing_time_seconds=0.042,
            provider=self.provider_name,
            model=self.model_name,
            segments=[
                TranscriptionSegment(
                    id=0,
                    start=0.0,
                    end=round(audio_duration_seconds, 2),
                    text="Hello world, this is a test audio recording.",
                    avg_logprob=-0.12,
                    no_speech_prob=0.01,
                )
            ],
            metadata={"mock": True, "filename": filename}
        )
