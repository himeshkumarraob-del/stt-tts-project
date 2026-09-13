import pytest
from starlette.testclient import TestClient
from app.services.pronunciation.pronunciation_service import PronunciationService
from app.services.pronunciation.assessor import AcousticPronunciationAssessor
from app.schemas.pronunciation import WordStatus
from tests.mock_stt import MockWhisperModel


@pytest.fixture(autouse=True)
def setup_mock_pronunciation_assessor(monkeypatch):
    """Ensure pronunciation tests run with predictable mock model."""
    PronunciationService._assessor = None
    monkeypatch.setattr(
        AcousticPronunciationAssessor,
        "_get_model",
        lambda self: MockWhisperModel(
            mock_words=["Hello", "world", "this", "is", "a", "test"],
            mock_probs=[0.98, 0.95, 0.92, 0.96, 0.99, 0.94]
        )
    )


def test_assess_perfect_pronunciation(client: TestClient, sample_valid_wav_bytes: bytes):
    """Test assess endpoint with matching target text and speech."""
    files = {
        "file": ("test.wav", sample_valid_wav_bytes, "audio/wav")
    }
    data = {
        "target_text": "Hello world this is a test"
    }
    response = client.post("/api/v1/pronunciation/assess", files=files, data=data)
    assert response.status_code == 200
    body = response.json()

    assert body["target_text"] == "Hello world this is a test"
    assert "hello world this is a test" in body["transcript"].lower()
    assert 90.0 <= body["overall_score"] <= 100.0
    assert 0.0 <= body["confidence"] <= 1.0
    assert len(body["words"]) == 6
    for w in body["words"]:
        assert w["status"] == WordStatus.CORRECT
        assert w["score"] >= 90.0
        # Verify derived phoneme scores
        for p in w["phonemes"]:
            assert p["is_derived"] is True
            assert p["score"] == w["score"]


def test_acoustic_evidence_directly_modulates_score(client: TestClient, sample_valid_wav_bytes: bytes, monkeypatch):
    """
    Test specifically proving that changing acoustic posterior probabilities directly
    modulates the word-level and overall pronunciation scores (not text alone).
    """
    # High acoustic confidence (0.95 avg)
    monkeypatch.setattr(
        AcousticPronunciationAssessor,
        "_get_model",
        lambda self: MockWhisperModel(
            mock_words=["Hello", "world"],
            mock_probs=[0.95, 0.95]
        )
    )
    files = {"file": ("test.wav", sample_valid_wav_bytes, "audio/wav")}
    data = {"target_text": "Hello world"}
    resp_high = client.post("/api/v1/pronunciation/assess", files=files, data=data)
    score_high = resp_high.json()["overall_score"]

    # Low acoustic confidence (0.50 avg) for identical spoken transcript text
    monkeypatch.setattr(
        AcousticPronunciationAssessor,
        "_get_model",
        lambda self: MockWhisperModel(
            mock_words=["Hello", "world"],
            mock_probs=[0.50, 0.50]
        )
    )
    resp_low = client.post("/api/v1/pronunciation/assess", files=files, data=data)
    score_low = resp_low.json()["overall_score"]

    # Even though transcript text matches the target in both cases,
    # the pronunciation score must directly decrease with degraded acoustic probability!
    assert score_high == 95.0
    assert score_low == 50.0
    assert score_high > score_low


def test_assess_word_substitution(client: TestClient, sample_valid_wav_bytes: bytes, monkeypatch):
    """Test assess endpoint detects word substitutions."""
    monkeypatch.setattr(
        AcousticPronunciationAssessor,
        "_get_model",
        lambda self: MockWhisperModel(
            mock_words=["Good", "morning", "this", "is", "a", "test"],
            mock_probs=[0.95, 0.95, 0.92, 0.96, 0.99, 0.94]
        )
    )
    files = {
        "file": ("test.wav", sample_valid_wav_bytes, "audio/wav")
    }
    data = {
        "target_text": "Hello world this is a test"
    }
    response = client.post("/api/v1/pronunciation/assess", files=files, data=data)
    assert response.status_code == 200
    body = response.json()

    assert body["overall_score"] < 90.0
    substitutions = [w for w in body["words"] if w["status"] == WordStatus.SUBSTITUTION]
    assert len(substitutions) >= 1
    assert len(body["issues"]) >= 1


def test_assess_omitted_word(client: TestClient, sample_valid_wav_bytes: bytes, monkeypatch):
    """Test assess endpoint detects omitted words."""
    monkeypatch.setattr(
        AcousticPronunciationAssessor,
        "_get_model",
        lambda self: MockWhisperModel(
            mock_words=["Hello", "world", "test"],
            mock_probs=[0.95, 0.95, 0.94]
        )
    )
    files = {
        "file": ("test.wav", sample_valid_wav_bytes, "audio/wav")
    }
    data = {
        "target_text": "Hello world this is a test"
    }
    response = client.post("/api/v1/pronunciation/assess", files=files, data=data)
    assert response.status_code == 200
    body = response.json()

    omissions = [w for w in body["words"] if w["status"] == WordStatus.OMISSION]
    assert len(omissions) >= 1
    for o in omissions:
        assert o["score"] == 0.0


def test_assess_inserted_word(client: TestClient, sample_valid_wav_bytes: bytes, monkeypatch):
    """Test assess endpoint detects inserted extra words."""
    monkeypatch.setattr(
        AcousticPronunciationAssessor,
        "_get_model",
        lambda self: MockWhisperModel(
            mock_words=["Hello", "world", "extra", "this", "is", "a", "test"],
            mock_probs=[0.95, 0.95, 0.85, 0.92, 0.96, 0.99, 0.94]
        )
    )
    files = {
        "file": ("test.wav", sample_valid_wav_bytes, "audio/wav")
    }
    data = {
        "target_text": "Hello world this is a test"
    }
    response = client.post("/api/v1/pronunciation/assess", files=files, data=data)
    assert response.status_code == 200
    body = response.json()

    insertions = [w for w in body["words"] if w["status"] == WordStatus.INSERTION]
    assert len(insertions) >= 1


def test_assess_empty_target_text(client: TestClient, sample_valid_wav_bytes: bytes):
    """Test assess endpoint rejects empty target text."""
    files = {
        "file": ("test.wav", sample_valid_wav_bytes, "audio/wav")
    }
    data = {
        "target_text": "   "
    }
    response = client.post("/api/v1/pronunciation/assess", files=files, data=data)
    assert response.status_code == 400
    body = response.json()
    assert body["error"] is True
    assert "target text must not be empty" in body["message"].lower()


def test_assess_missing_file(client: TestClient):
    """Test assess endpoint with missing file upload."""
    data = {
        "target_text": "Hello world"
    }
    response = client.post("/api/v1/pronunciation/assess", data=data)
    assert response.status_code == 422
    body = response.json()
    assert body["error"] is True


def test_assess_invalid_audio_extension(client: TestClient, sample_valid_wav_bytes: bytes):
    """Test assess endpoint with invalid audio file format."""
    files = {
        "file": ("test.exe", sample_valid_wav_bytes, "application/octet-stream")
    }
    data = {
        "target_text": "Hello world"
    }
    response = client.post("/api/v1/pronunciation/assess", files=files, data=data)
    assert response.status_code == 415
    body = response.json()
    assert body["error"] is True


def test_assess_corrupt_audio(client: TestClient):
    """Test assess endpoint with corrupt audio bytes."""
    files = {
        "file": ("corrupt.wav", b"NOT_VALID_AUDIO_BYTES_12345", "audio/wav")
    }
    data = {
        "target_text": "Hello world"
    }
    response = client.post("/api/v1/pronunciation/assess", files=files, data=data)
    assert response.status_code == 400
    body = response.json()
    assert body["error"] is True


def test_assess_model_failure(client: TestClient, sample_valid_wav_bytes: bytes, monkeypatch):
    """Test assess endpoint gracefully handles model exception."""
    class FailingModel:
        def transcribe(self, *args, **kwargs):
            raise RuntimeError("Model CUDA out of memory / compute error")

    monkeypatch.setattr(AcousticPronunciationAssessor, "_get_model", lambda self: FailingModel())

    files = {
        "file": ("test.wav", sample_valid_wav_bytes, "audio/wav")
    }
    data = {
        "target_text": "Hello world"
    }
    response = client.post("/api/v1/pronunciation/assess", files=files, data=data)
    assert response.status_code == 500
    body = response.json()
    assert body["error"] is True
    assert "pronunciation assessment failed" in body["message"].lower()


def test_assess_schema_and_range_validation(client: TestClient, sample_valid_wav_bytes: bytes):
    """Test schema validity, score ranges (0-100), and confidence ranges (0.0-1.0)."""
    files = {
        "file": ("test.wav", sample_valid_wav_bytes, "audio/wav")
    }
    data = {
        "target_text": "Hello world this is a test"
    }
    response = client.post("/api/v1/pronunciation/assess", files=files, data=data)
    assert response.status_code == 200
    body = response.json()

    assert 0.0 <= body["overall_score"] <= 100.0
    assert 0.0 <= body["confidence"] <= 1.0
    assert body["duration_seconds"] > 0
    assert body["processing_time_seconds"] > 0
    assert isinstance(body["words"], list)
    assert isinstance(body["phonemes"], list)
    assert isinstance(body["issues"], list)
    assert isinstance(body["metadata"], dict)
