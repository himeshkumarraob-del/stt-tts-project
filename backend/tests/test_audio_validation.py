import pytest
from starlette.testclient import TestClient
from app.core.config import settings


def test_validate_valid_wav_audio(client: TestClient, sample_valid_wav_bytes: bytes):
    """Test standard valid WAV audio upload."""
    files = {
        "file": ("recording.wav", sample_valid_wav_bytes, "audio/wav")
    }
    response = client.post("/api/v1/audio/validate", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["metadata"]["filename"] == "recording.wav"
    assert data["metadata"]["extension"] == "wav"
    assert data["metadata"]["duration_seconds"] is not None
    assert 0.9 <= data["metadata"]["duration_seconds"] <= 1.1
    assert data["metadata"]["sample_rate"] == 16000
    assert data["metadata"]["channels"] == 1
    assert data["diagnostics"]["format_check"] == "PASS"


def test_validate_unsupported_extension(client: TestClient, sample_valid_wav_bytes: bytes):
    """Test uploading file with unsupported extension."""
    files = {
        "file": ("sample.exe", sample_valid_wav_bytes, "application/octet-stream")
    }
    response = client.post("/api/v1/audio/validate", files=files)
    assert response.status_code == 415
    data = response.json()
    assert data["error"] is True
    assert "not supported" in data["message"].lower()


def test_validate_empty_file(client: TestClient):
    """Test uploading a 0-byte empty file."""
    files = {
        "file": ("empty.wav", b"", "audio/wav")
    }
    response = client.post("/api/v1/audio/validate", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert "empty" in data["message"].lower()


def test_validate_corrupt_file(client: TestClient):
    """Test uploading corrupted or unreadable audio bytes."""
    corrupt_bytes = b"NOT_A_REAL_AUDIO_CONTENT_XYZ_123456789"
    files = {
        "file": ("corrupt.wav", corrupt_bytes, "audio/wav")
    }
    response = client.post("/api/v1/audio/validate", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert "corrupt" in data["message"].lower() or "not a recognized" in data["message"].lower()


def test_validate_too_short_duration(client: TestClient, sample_too_short_wav_bytes: bytes):
    """Test audio shorter than 0.5s."""
    files = {
        "file": ("short.wav", sample_too_short_wav_bytes, "audio/wav")
    }
    response = client.post("/api/v1/audio/validate", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert "shorter than minimum" in data["message"].lower()


def test_validate_too_long_duration(client: TestClient, sample_too_long_wav_bytes: bytes):
    """Test audio longer than 120.0s."""
    files = {
        "file": ("long.wav", sample_too_long_wav_bytes, "audio/wav")
    }
    response = client.post("/api/v1/audio/validate", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert "exceeds maximum allowed" in data["message"].lower()


def test_validate_oversized_file(client: TestClient, monkeypatch):
    """Test uploading file exceeding MAX_AUDIO_SIZE_BYTES."""
    # Temporarily set small threshold (100 bytes) via monkeypatch to test without massive RAM usage
    monkeypatch.setattr(settings, "MAX_AUDIO_SIZE_BYTES", 100)
    fake_large_audio = b"RIFF" + b"\x00" * 200
    files = {
        "file": ("large.wav", fake_large_audio, "audio/wav")
    }
    response = client.post("/api/v1/audio/validate", files=files)
    assert response.status_code == 413
    data = response.json()
    assert data["error"] is True
    assert "exceeds maximum limit" in data["message"].lower()


def test_validate_missing_file_upload(client: TestClient):
    """Test request without any file payload."""
    response = client.post("/api/v1/audio/validate")
    assert response.status_code == 422
    data = response.json()
    assert data["error"] is True


def test_validate_mime_type_header_mismatch(client: TestClient, sample_valid_wav_bytes: bytes):
    """Test extension/header mismatch (e.g. WAV header in an MP3 named file)."""
    files = {
        "file": ("spoofed.mp3", sample_valid_wav_bytes, "audio/mpeg")
    }
    response = client.post("/api/v1/audio/validate", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert "does not match the actual inspected file header" in data["message"]


def test_validate_valid_supported_format(client: TestClient, sample_valid_wav_bytes: bytes):
    """Test valid audio with supported format returns full structured diagnostics."""
    files = {
        "file": ("supported_audio.wav", sample_valid_wav_bytes, "audio/wav")
    }
    response = client.post("/api/v1/audio/validate", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["metadata"]["format"] == "wav"
    assert data["diagnostics"]["header_sniff_format"] == "wav"
    assert data["diagnostics"]["size_check"] == "PASS"
    assert data["diagnostics"]["duration_check"] == "PASS"
