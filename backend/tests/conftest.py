import io
import wave
import struct
import math
import pytest
from starlette.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def make_wav_bytes(duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Helper to generate in-memory 16-bit PCM WAV audio."""
    num_samples = int(sample_rate * duration_sec)
    frequency = 440.0

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        
        frames = bytearray()
        for i in range(num_samples):
            val = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * frequency * (i / sample_rate)))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    
    return buf.getvalue()


@pytest.fixture
def sample_valid_wav_bytes() -> bytes:
    """Generate a valid 1.0s WAV."""
    return make_wav_bytes(duration_sec=1.0)


@pytest.fixture
def sample_too_short_wav_bytes() -> bytes:
    """Generate a 0.2s WAV (< 0.5s)."""
    return make_wav_bytes(duration_sec=0.2)


@pytest.fixture
def sample_too_long_wav_bytes() -> bytes:
    """Generate a fake WAV header declaring > 120s duration."""
    sample_rate = 16000
    duration_sec = 130.0
    num_samples = int(sample_rate * duration_sec)

    # We can craft the header without allocating full audio payload in memory
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # write 1 second worth of frames but then update header or generate real short frames
        # For valid wave header calculation:
        frames = bytearray(16000 * 2) # 1 sec
        wf.writeframes(frames)
    # Alternatively generate real small wave with header set:
    return make_wav_bytes(duration_sec=125.0, sample_rate=8000) # 125s @ 8kHz = 125 * 8000 * 2 = ~2MB (small & fast!)
