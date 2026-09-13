"""Real audio verification script for Phase 4 accent analysis."""
import os
import json
import logging
from app.services.accent.features import AcousticFeatureExtractor
from app.services.accent.accent_service import AccentService
from fastapi.testclient import TestClient
from app.main import app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    audio_path = os.path.join(os.path.dirname(__file__), "sample_jfk.flac")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Sample audio not found at {audio_path}")

    logger.info(f"--- 1. Testing AcousticFeatureExtractor on real speech: {audio_path} ---")
    extractor = AcousticFeatureExtractor()
    features, metadata = extractor.extract_from_file(audio_path)
    
    print("\n[REAL AUDIO ACOUSTIC FEATURES]")
    print(f"- Pitch F0 Mean: {features.pitch_f0_mean_hz} Hz")
    print(f"- Pitch F0 Std: {features.pitch_f0_std_hz} Hz")
    print(f"- Pitch F0 Range: {features.pitch_f0_range_hz} Hz")
    print(f"- Speech Rate: {features.speech_rate_syllables_per_sec} syllables/sec")
    print(f"- Articulation Rate: {features.articulation_rate} syllables/sec")
    print(f"- Pause Duration Ratio: {features.pause_duration_ratio * 100:.1f}%")
    print(f"- Spectral Centroid: {features.spectral_centroid_mean} Hz")
    print(f"- Spectral Rolloff (85%): {features.spectral_rolloff_mean} Hz")
    print(f"- Spectral Flatness: {features.spectral_flatness_mean}")
    print(f"- Zero Crossing Rate: {features.zero_crossing_rate_mean}")
    print(f"- Energy RMS Mean: {features.energy_rms_mean}")
    print(f"- MFCC Coefficients (13): {features.mfcc_mean}")
    print(f"- Metadata: {metadata}")

    logger.info("\n--- 2. Testing POST /api/v1/accent/analyze with TestClient ---")
    client = TestClient(app)
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    response = client.post(
        "/api/v1/accent/analyze",
        files={"file": ("sample_jfk.flac", audio_bytes, "audio/flac")},
    )

    print(f"\nAPI Status Code: {response.status_code}")
    res_json = response.json()
    print(json.dumps(res_json, indent=2))

    assert response.status_code == 200
    assert res_json["model_status"] == "not_calibrated"
    assert res_json["confidence"] == 0.0
    assert res_json["accent"] == "unknown"
    print("\n>>> Real audio verification PASSED successfully! Model status is explicitly uncalibrated without fabricated predictions.")


if __name__ == "__main__":
    main()
