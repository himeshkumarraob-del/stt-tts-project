"""Comprehensive test suite for Phase 6 (TTS, Personalized STT Memory & Voice Learning Loop)."""
import io
import wave
import json
import uuid
import pytest
import numpy as np
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.tts import TTSSynthesizeRequest, TTSSynthesizeResponse
from app.schemas.correction import CorrectionConfirmRequest, CorrectionResponse
from app.schemas.voice_learning import VoiceLearningProcessResponse
from app.services.tts import TTSService, OpenAITTSProvider, DeterministicFallbackTTSProvider
from app.services.correction import CorrectionService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_speech_wav_bytes():
    """Generate 2 seconds of 16kHz audio for test pipeline."""
    sr = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    signal = 0.5 * np.sin(2 * np.pi * 220 * t) + 0.3 * np.sin(2 * np.pi * 440 * t)
    envelope = np.sin(np.pi * t / duration)
    pcm = (signal * envelope * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    buf.seek(0)
    return buf.read()


# ==========================================
# 1. TEXT-TO-SPEECH (TTS) TESTS
# ==========================================

@pytest.mark.asyncio
async def test_fallback_tts_provider():
    """Test deterministic fallback TTS generates valid playable audio."""
    provider = DeterministicFallbackTTSProvider()
    req = TTSSynthesizeRequest(text="Hello world, this is a test.", voice="alloy")
    audio_bytes, meta = await provider.synthesize_speech(req)

    assert len(audio_bytes) > 0
    assert meta.is_fallback is True
    assert meta.provider == "deterministic_fallback"
    assert meta.format == "wav"
    assert meta.character_count == len(req.text)
    assert meta.audio_base64 is not None


@pytest.mark.asyncio
async def test_openai_tts_provider_mock():
    """Test OpenAITTSProvider correctly calls OpenAI API."""
    mock_audio = b"\xff\xfb\x90\x44" + b"\x00" * 500  # MP3 frame
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.content = mock_audio

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        provider = OpenAITTSProvider(api_key="sk-testkey12345")
        req = TTSSynthesizeRequest(text="Practice makes perfect.", voice="nova", audio_format="mp3")
        audio_bytes, meta = await provider.synthesize_speech(req)

        assert audio_bytes == mock_audio
        assert meta.is_fallback is False
        assert meta.provider == "openai"
        assert meta.voice == "nova"


@pytest.mark.asyncio
async def test_tts_service_empty_text_rejection():
    """Test TTSService rejects empty strings."""
    with pytest.raises(ValueError, match="cannot be empty"):
        await TTSService.synthesize("")


def test_api_tts_synthesize_endpoint(client):
    """Test POST /api/v1/tts/synthesize JSON response."""
    payload = {"text": "Welcome to your English learning session.", "voice": "alloy"}
    response = client.post("/api/v1/tts/synthesize", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "audio_base64" in data
    assert data["character_count"] == len(payload["text"])


def test_api_tts_synthesize_raw_audio_stream(client):
    """Test POST /api/v1/tts/synthesize?raw_audio=true stream response."""
    payload = {"text": "Direct audio stream.", "voice": "alloy", "audio_format": "wav"}
    response = client.post("/api/v1/tts/synthesize?raw_audio=true", json=payload)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/")
    assert len(response.content) > 0


# ==========================================
# 2. PERSONALIZED CORRECTION MEMORY TESTS
# ==========================================

def test_correction_service_confirm_and_update():
    """Test confirming, counting, and retrieving user-specific corrections."""
    user_id = f"test_user_himesh_{uuid.uuid4()}"
    req1 = CorrectionConfirmRequest(
        user_id=user_id,
        incorrect_text="image",
        correct_text="Himesh",
        context="my name is",
    )
    res1 = CorrectionService.confirm_correction(req1)
    assert res1.user_id == user_id
    assert res1.incorrect_text == "image"
    assert res1.correct_text == "Himesh"
    assert res1.occurrence_count == 1

    # Confirm same correction again -> should increment occurrence count
    res2 = CorrectionService.confirm_correction(req1)
    assert res2.occurrence_count == 2
    assert res2.id == res1.id


def test_correction_service_context_aware_replacement():
    """
    Test that 'image' -> 'Himesh' occurs ONLY when context ('my name is') matches,
    and regular words like 'This is an image' are NOT replaced!
    """
    user_id = f"test_user_context_{uuid.uuid4()}"
    CorrectionService.confirm_correction(
        CorrectionConfirmRequest(
            user_id=user_id,
            incorrect_text="image",
            correct_text="Himesh",
            context="my name is",
        )
    )

    # 1. Matching context: "My name is image" -> "My name is Himesh"
    transcript_matching = "Hello, my name is image and I am learning English."
    corrected, applied = CorrectionService.apply_corrections(user_id, transcript_matching)
    assert "my name is Himesh" in corrected or "My name is Himesh" in corrected
    assert len(applied) == 1

    # 2. Non-matching context: "This is an image" -> MUST REMAIN "This is an image"
    transcript_general = "This is an image of the mountains."
    corrected_gen, applied_gen = CorrectionService.apply_corrections(user_id, transcript_general)
    assert corrected_gen == "This is an image of the mountains."
    assert len(applied_gen) == 0  # Not replaced!


def test_correction_service_user_isolation():
    """Test corrections for User A do NOT affect User B."""
    user_a = f"user_alpha_{uuid.uuid4()}"
    user_b = f"user_beta_{uuid.uuid4()}"

    CorrectionService.confirm_correction(
        CorrectionConfirmRequest(
            user_id=user_a,
            incorrect_text="image",
            correct_text="Himesh",
            context="my name is",
        )
    )

    # User B says "my name is image" -> Should NOT replace because correction belongs only to User A!
    transcript = "my name is image"
    corrected_b, applied_b = CorrectionService.apply_corrections(user_b, transcript)
    assert corrected_b == "my name is image"
    assert len(applied_b) == 0


def test_api_corrections_endpoints(client):
    """Test POST /api/v1/corrections/confirm and GET /api/v1/corrections/{user_id}."""
    user_id = f"test_api_user_{uuid.uuid4()}"
    payload = {
        "user_id": user_id,
        "incorrect_text": "van",
        "correct_text": "one",
        "context": "number",
    }
    post_res = client.post("/api/v1/corrections/confirm", json=payload)
    assert post_res.status_code == 200
    data = post_res.json()
    assert data["incorrect_text"] == "van"
    assert data["correct_text"] == "one"

    # Get corrections list
    get_res = client.get(f"/api/v1/corrections/{user_id}")
    assert get_res.status_code == 200
    list_data = get_res.json()
    assert list_data["total_count"] >= 1
    assert any(c["incorrect_text"] == "van" for c in list_data["corrections"])


# ==========================================
# 3. END-TO-END VOICE LEARNING LOOP TESTS
# ==========================================

def test_api_voice_learning_loop_success(client, valid_speech_wav_bytes):
    """Test POST /api/v1/voice-learning/process orchestrating all 6 phases end-to-end."""
    user_id = "e2e_test_user_777"
    target_text = "Ask not what your country can do for you."

    # Setup a correction for this user
    CorrectionService.confirm_correction(
        CorrectionConfirmRequest(
            user_id=user_id,
            incorrect_text="country",
            correct_text="nation",
            context="your",
        )
    )

    data_payload = {
        "target_text": target_text,
        "user_id": user_id,
        "synthesize_tts": True,
    }
    files = {
        "file": ("e2e_recording.wav", valid_speech_wav_bytes, "audio/wav")
    }

    response = client.post(
        "/api/v1/voice-learning/process",
        data=data_payload,
        files=files,
    )

    assert response.status_code == 200
    res = response.json()

    # Validate output contract
    assert "attempt_id" in res
    assert res["user_id"] == user_id
    assert "original_transcript" in res
    assert "corrected_transcript" in res
    assert "pronunciation_result" in res
    assert "accent_result" in res
    assert "feedback_result" in res
    assert "timings" in res

    # Timings breakdown
    timings = res["timings"]
    assert timings["audio_validation_seconds"] >= 0.0
    assert timings["stt_seconds"] >= 0.0
    assert timings["pronunciation_seconds"] >= 0.0
    assert timings["accent_seconds"] >= 0.0
    assert timings["feedback_seconds"] >= 0.0
    assert timings["total_pipeline_seconds"] > 0.0

    # Intermediate verified score preservation
    assert res["pronunciation_result"]["overall_score"] >= 0.0
    assert res["feedback_result"]["scores_summary"]["overall_pronunciation_score"] == res["pronunciation_result"]["overall_score"]
    assert res["accent_result"]["model_status"] == "not_calibrated"
