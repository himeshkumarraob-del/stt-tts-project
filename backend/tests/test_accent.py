"""Tests for Phase 4 Indian-English Accent Analysis."""
import io
import wave
import json
import pytest
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.accent import (
    AccentLabel,
    ModelStatus,
    AccentAnalysisResponse,
    AcousticFeatures,
)
from app.services.accent.features import AcousticFeatureExtractor
from app.services.accent.classifier import (
    DevelopmentBaselineAccentClassifier,
    TrainedAccentClassifier,
)
from app.services.accent.accent_service import AccentService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def synthetic_wav_bytes():
    """Generate 2 seconds of synthetic 440 Hz + 880 Hz harmonic tone WAV data."""
    sr = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Multi-harmonic voiced signal with amplitude envelope
    signal = 0.5 * np.sin(2 * np.pi * 180 * t) + 0.3 * np.sin(2 * np.pi * 360 * t)
    envelope = np.sin(np.pi * t / duration)
    signal = (signal * envelope * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(signal.tobytes())
    buf.seek(0)
    return buf.read()


@pytest.fixture
def corrupted_wav_bytes():
    """Corrupted WAV header with non-audio payload."""
    return b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00\x7d\x00\x00\x02\x00\x10\x00data" + b"\x00" * 10


def test_acoustic_feature_extractor_signal(synthetic_wav_bytes):
    """Test feature extraction from audio bytes."""
    extractor = AcousticFeatureExtractor()
    import soundfile as sf
    data, sr = sf.read(io.BytesIO(synthetic_wav_bytes))
    features, metadata = extractor.extract_from_signal(data, sr)

    assert isinstance(features, AcousticFeatures)
    assert features.pitch_f0_mean_hz > 0
    assert len(features.mfcc_mean) == 13
    assert len(features.mfcc_std) == 13
    assert features.spectral_centroid_mean > 0
    assert 0.0 <= features.pause_duration_ratio <= 1.0
    assert metadata["duration_seconds"] == pytest.approx(2.0, rel=0.05)


def test_development_baseline_classifier():
    """Test development classifier produces NOT_CALIBRATED and does not fabricate predictions."""
    clf = DevelopmentBaselineAccentClassifier()
    assert clf.is_calibrated is False
    assert clf.model_name == "acoustic_prosody_baseline"

    mock_features = AcousticFeatures(
        pitch_f0_mean_hz=185.0,
        pitch_f0_std_hz=28.5,
        pitch_f0_range_hz=85.0,
        speech_rate_syllables_per_sec=3.5,
        articulation_rate=4.2,
        pause_duration_ratio=0.15,
        spectral_centroid_mean=1450.0,
        spectral_rolloff_mean=2800.0,
        spectral_flatness_mean=0.015,
        zero_crossing_rate_mean=0.045,
        energy_rms_mean=0.08,
        energy_rms_std=0.04,
        mfcc_mean=[0.0] * 13,
        mfcc_std=[1.0] * 13,
    )
    meta = {"duration_seconds": 2.0, "sample_rate": 16000}
    accent, conf, status, explanation, model_meta = clf.classify(mock_features, meta)

    assert accent == AccentLabel.UNKNOWN
    assert conf == 0.0
    assert status == ModelStatus.NOT_CALIBRATED
    assert len(explanation) > 0
    assert model_meta.training_dataset is None


def test_trained_classifier_mock(tmp_path):
    """Test TrainedAccentClassifier when calibrated model files exist."""
    model_dir = tmp_path / "test_model"
    model_dir.mkdir()

    meta_payload = {
        "model_name": "test_calibrated_classifier",
        "model_version": "1.0.0",
        "model_type": "linear_logistic",
        "training_dataset": "verified_labeled_accent_dataset_v1",
        "training_date": "2026-09-12T00:00:00Z",
        "is_calibrated": True,
        "labels": ["indian_english", "non_indian_english"],
    }
    with open(model_dir / "metadata.json", "w") as f:
        json.dump(meta_payload, f)

    # 38 features (12 scalar + 13 mfcc_mean + 13 mfcc_std)
    weights_payload = {
        "coef": [0.1] * 38,
        "intercept": 0.5,
        "mean": [0.0] * 38,
        "scale": [1.0] * 38,
    }
    with open(model_dir / "weights.json", "w") as f:
        json.dump(weights_payload, f)

    clf = TrainedAccentClassifier(str(model_dir))
    assert clf.is_calibrated is True
    assert clf.model_name == "test_calibrated_classifier"

    mock_features = AcousticFeatures(
        pitch_f0_mean_hz=185.0,
        pitch_f0_std_hz=28.5,
        pitch_f0_range_hz=85.0,
        speech_rate_syllables_per_sec=3.5,
        articulation_rate=4.2,
        pause_duration_ratio=0.15,
        spectral_centroid_mean=1450.0,
        spectral_rolloff_mean=2800.0,
        spectral_flatness_mean=0.015,
        zero_crossing_rate_mean=0.045,
        energy_rms_mean=0.08,
        energy_rms_std=0.04,
        mfcc_mean=[0.0] * 13,
        mfcc_std=[1.0] * 13,
    )
    accent, conf, status, explanation, model_meta = clf.classify(mock_features, {"duration_seconds": 2.0, "sample_rate": 16000})
    assert status == ModelStatus.TRAINED
    assert accent in [AccentLabel.INDIAN_ENGLISH, AccentLabel.NON_INDIAN_ENGLISH]
    assert 0.0 <= conf <= 1.0


def test_api_accent_analyze_success(client, synthetic_wav_bytes):
    """Test POST /api/v1/accent/analyze with valid synthetic audio."""
    response = client.post(
        "/api/v1/accent/analyze",
        files={"file": ("test_speech.wav", synthetic_wav_bytes, "audio/wav")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accent"] == "unknown"
    assert data["confidence"] == 0.0
    assert data["model_status"] == "not_calibrated"
    assert "features" in data
    assert len(data["features"]["mfcc_mean"]) == 13
    assert data["features"]["pitch_f0_mean_hz"] > 0
    assert "explanation" in data
    assert len(data["explanation"]) > 0
    assert data["metadata"]["model_name"] == "acoustic_prosody_baseline"


def test_api_accent_analyze_invalid_extension(client):
    """Test POST /api/v1/accent/analyze with unsupported file format."""
    response = client.post(
        "/api/v1/accent/analyze",
        files={"file": ("test.txt", b"Hello text file", "text/plain")},
    )
    assert response.status_code == 415
    data = response.json()
    assert data["error"] is True
    assert "not supported" in data["message"].lower()


def test_api_accent_analyze_empty_file(client):
    """Test POST /api/v1/accent/analyze with 0-byte file."""
    response = client.post(
        "/api/v1/accent/analyze",
        files={"file": ("empty.wav", b"", "audio/wav")},
    )
    assert response.status_code == 400


def test_api_accent_analyze_corrupted_file(client, corrupted_wav_bytes):
    """Test POST /api/v1/accent/analyze with corrupted audio."""
    response = client.post(
        "/api/v1/accent/analyze",
        files={"file": ("corrupt.wav", corrupted_wav_bytes, "audio/wav")},
    )
    assert response.status_code == 400


def test_pronunciation_accent_separation(client, synthetic_wav_bytes):
    """
    Verify that Pronunciation Assessment and Accent Analysis remain strictly decoupled.
    Pronunciation response must have overall_score and no accent pollution.
    Accent response must have features/model_status and no pronunciation score pollution.
    """
    from unittest.mock import patch
    from tests.mock_stt import MockWhisperModel

    with patch("app.services.pronunciation.assessor.AcousticPronunciationAssessor._get_model", return_value=MockWhisperModel(mock_words=["Hello", "world"])):
        # 1. Pronunciation endpoint
        pron_resp = client.post(
            "/api/v1/pronunciation/assess",
            data={"target_text": "Hello world"},
            files={"file": ("sample.wav", synthetic_wav_bytes, "audio/wav")},
        )
        assert pron_resp.status_code == 200
        pron_data = pron_resp.json()
        assert "overall_score" in pron_data
        assert "words" in pron_data
        assert "accent" not in pron_data  # Pronunciation must not evaluate accent

    # 2. Accent endpoint
    accent_resp = client.post(
        "/api/v1/accent/analyze",
        files={"file": ("sample.wav", synthetic_wav_bytes, "audio/wav")},
    )
    assert accent_resp.status_code == 200
    accent_data = accent_resp.json()
    assert "accent" in accent_data
    assert "features" in accent_data
    assert "overall_score" not in accent_data  # Accent analysis must not evaluate pronunciation correctness
