import pytest
from starlette.testclient import TestClient
from app.services.stt.stt_service import STTService
from app.services.stt.whisper_provider import FasterWhisperProvider
from app.core.config import settings
from app.core.errors import STTModelLoadError
from tests.mock_stt import MockSTTProvider, MockWhisperModel



@pytest.fixture(autouse=True)
def setup_mock_stt_provider(monkeypatch):
    """Ensure tests run predictably with mock/stubbed WhisperModel."""
    # Reset cached providers
    STTService._providers.clear()
    
    # Patch FasterWhisperProvider._get_model to return MockWhisperModel
    monkeypatch.setattr(FasterWhisperProvider, "_get_model", lambda self: MockWhisperModel(self._model_size, self._device, self._compute_type))


def test_stt_transcribe_valid_audio(client: TestClient, sample_valid_wav_bytes: bytes):
    """Test successful STT transcription with valid WAV audio."""
    files = {
        "file": ("recording.wav", sample_valid_wav_bytes, "audio/wav")
    }
    response = client.post("/api/v1/stt/transcribe", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert len(data["text"]) > 0
    assert data["language"] == "en"
    assert data["duration_seconds"] >= 0.9
    assert data["processing_time_seconds"] >= 0
    assert data["provider"] == "faster-whisper"
    assert data["model"] == settings.STT_MODEL
    assert isinstance(data["segments"], list)
    assert len(data["segments"]) > 0


def test_stt_transcribe_empty_file(client: TestClient):
    """Test STT rejects 0-byte audio upload through Phase 1 validation."""
    files = {
        "file": ("empty.wav", b"", "audio/wav")
    }
    response = client.post("/api/v1/stt/transcribe", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert "empty" in data["message"].lower()


def test_stt_transcribe_corrupted_audio(client: TestClient):
    """Test STT rejects corrupt audio through Phase 1 validation."""
    files = {
        "file": ("corrupted.wav", b"INVALID_GARBAGE_PAYLOAD_NOT_AUDIO", "audio/wav")
    }
    response = client.post("/api/v1/stt/transcribe", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert "corrupt" in data["message"].lower() or "not a recognized" in data["message"].lower()


def test_stt_transcribe_unsupported_audio(client: TestClient, sample_valid_wav_bytes: bytes):
    """Test STT rejects unsupported file extension through Phase 1 validation."""
    files = {
        "file": ("payload.exe", sample_valid_wav_bytes, "application/octet-stream")
    }
    response = client.post("/api/v1/stt/transcribe", files=files)
    assert response.status_code == 415
    data = response.json()
    assert data["error"] is True
    assert "not supported" in data["message"].lower()


def test_stt_transcribe_duration_too_short(client: TestClient, sample_too_short_wav_bytes: bytes):
    """Test STT rejects audio shorter than 0.5s through Phase 1 validation."""
    files = {
        "file": ("short.wav", sample_too_short_wav_bytes, "audio/wav")
    }
    response = client.post("/api/v1/stt/transcribe", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert "shorter than minimum" in data["message"].lower()


def test_stt_transcribe_duration_too_long(client: TestClient, sample_too_long_wav_bytes: bytes):
    """Test STT rejects audio longer than 120.0s through Phase 1 validation."""
    files = {
        "file": ("long.wav", sample_too_long_wav_bytes, "audio/wav")
    }
    response = client.post("/api/v1/stt/transcribe", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert "exceeds maximum allowed" in data["message"].lower()


def test_stt_transcribe_missing_file_upload(client: TestClient):
    """Test request without file parameter returns validation error."""
    response = client.post("/api/v1/stt/transcribe")
    assert response.status_code == 422
    data = response.json()
    assert data["error"] is True


def test_stt_transcribe_service_failure(client: TestClient, sample_valid_wav_bytes: bytes, monkeypatch):
    """Test safe handling when STT inference raises an exception."""
    class FailingWhisperModel:
        def transcribe(self, *args, **kwargs):
            raise RuntimeError("Underlying CTranslate2 execution failed")

    monkeypatch.setattr(FasterWhisperProvider, "_get_model", lambda self: FailingWhisperModel())

    files = {
        "file": ("recording.wav", sample_valid_wav_bytes, "audio/wav")
    }
    response = client.post("/api/v1/stt/transcribe", files=files)
    assert response.status_code == 500
    data = response.json()
    assert data["error"] is True
    assert "transcription failed" in data["message"].lower()


def test_stt_model_load_failure(client: TestClient, sample_valid_wav_bytes: bytes, monkeypatch):
    """Test safe handling when model loading fails."""
    def broken_get_model(self):
        raise STTModelLoadError(
            message=f"Failed to initialize STT model '{self._model_size}': simulated weight file missing",
            details={"model": self._model_size}
        )

    # Clear cache and trigger error in _get_model
    STTService._providers.clear()
    monkeypatch.setattr(FasterWhisperProvider, "_get_model", broken_get_model)

    files = {
        "file": ("recording.wav", sample_valid_wav_bytes, "audio/wav")
    }
    response = client.post("/api/v1/stt/transcribe", files=files)
    assert response.status_code == 500
    data = response.json()
    assert data["error"] is True
    assert "failed to initialize stt model" in data["message"].lower()




def test_stt_unsupported_provider_configuration(client: TestClient, sample_valid_wav_bytes: bytes):
    """Test configuring or requesting an invalid STT provider."""
    files = {
        "file": ("recording.wav", sample_valid_wav_bytes, "audio/wav")
    }
    data_form = {
        "provider": "non-existent-provider"
    }
    response = client.post("/api/v1/stt/transcribe", files=files, data=data_form)
    assert response.status_code == 500
    data = response.json()
    assert data["error"] is True
    assert "unsupported stt provider" in data["message"].lower()


def test_stt_response_schema_fields(client: TestClient, sample_valid_wav_bytes: bytes):
    """Verify all required response fields in schema."""
    files = {
        "file": ("speech.wav", sample_valid_wav_bytes, "audio/wav")
    }
    response = client.post("/api/v1/stt/transcribe", files=files)
    assert response.status_code == 200
    body = response.json()
    
    # Assert top-level keys
    for required_key in ["text", "language", "duration_seconds", "processing_time_seconds", "provider", "model", "segments", "metadata"]:
        assert required_key in body, f"Missing required key '{required_key}' in response"
    
    assert isinstance(body["text"], str)
    assert isinstance(body["duration_seconds"], float)
    assert isinstance(body["processing_time_seconds"], float)
    assert isinstance(body["segments"], list)
