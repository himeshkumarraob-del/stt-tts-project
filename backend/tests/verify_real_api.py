import os
from starlette.testclient import TestClient
from app.main import app
from app.services.stt.stt_service import STTService


def test_real_end_to_end_stt_api_endpoint():
    print("\n==================================================================")
    print("TESTING REAL POST /api/v1/stt/transcribe ENDPOINT (NO MOCKS)")
    print("==================================================================")
    
    # Ensure fresh instance with real faster-whisper model
    STTService._providers.clear()
    
    audio_path = os.path.join(os.path.dirname(__file__), "sample_jfk.flac")
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    
    with TestClient(app) as client:
        files = {
            "file": ("sample_jfk.flac", audio_bytes, "audio/flac")
        }
        data_form = {
            "language": "en"
        }
        
        response = client.post("/api/v1/stt/transcribe", files=files, data=data_form)
        
        print(f"HTTP Status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        body = response.json()
        print("\nAPI Response Body:")
        for k, v in body.items():
            if k == "segments":
                print(f"  segments: [Count={len(v)}]")
                for seg in v:
                    print(f"    - [{seg['start']}s -> {seg['end']}s]: \"{seg['text']}\"")
            else:
                print(f"  {k}: {v}")
            
        assert "text" in body
        assert len(body["text"]) > 0
        assert "fellow americans" in body["text"].lower()
        assert body["language"] == "en"
        assert body["duration_seconds"] > 10.0
        assert body["processing_time_seconds"] > 0
        assert body["provider"] == "faster-whisper"
        assert body["model"] == "base.en"
        assert isinstance(body["segments"], list)
        assert len(body["segments"]) > 0
        
        print("\n[SUCCESS] Real STT End-to-End API endpoint test PASSED successfully!")

        print("==================================================================")


if __name__ == "__main__":
    test_real_end_to_end_stt_api_endpoint()
