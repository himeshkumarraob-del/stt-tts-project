"""Real end-to-end Phase 6 verification script (TTS, Personalized STT Memory & Complete Voice Learning Loop)."""
import os
import json
import time
import logging
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.correction import CorrectionConfirmRequest
from app.services.correction import CorrectionService
from app.services.tts import TTSService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    client = TestClient(app)
    sample_flac_path = os.path.join(os.path.dirname(__file__), "sample_jfk.flac")
    if not os.path.exists(sample_flac_path):
        raise FileNotFoundError(f"Sample audio not found: {sample_flac_path}")

    with open(sample_flac_path, "rb") as f:
        audio_bytes = f.read()

    print("=" * 70)
    print("PHASE 6: REAL VERIFICATION AUDIT")
    print("=" * 70)

    # -------------------------------------------------------------
    # PART A: REAL TTS SYNTHESIS VERIFICATION
    # -------------------------------------------------------------
    print("\n--- [A] Testing Real TTS Synthesis ---")
    tts_text = "Welcome to the Voice Learning platform. Let us practice your pronunciation."
    tts_req = {"text": tts_text, "voice": "alloy", "audio_format": "mp3"}
    
    t0 = time.perf_counter()
    tts_resp = client.post("/api/v1/tts/synthesize", json=tts_req)
    t_tts = round(time.perf_counter() - t0, 4)

    print(f"TTS HTTP Status: {tts_resp.status_code}")
    assert tts_resp.status_code == 200
    tts_data = tts_resp.json()
    print(f"TTS Model: {tts_data['model']}")
    print(f"TTS Provider: {tts_data['provider']}")
    print(f"Is Fallback: {tts_data['is_fallback']}")
    print(f"Audio Base64 Payload Present: {tts_data['audio_base64'] is not None} (Length: {len(tts_data['audio_base64'])})")
    print(f"TTS Synthesis Latency: {t_tts}s")

    # -------------------------------------------------------------
    # PART B: PERSONALIZED STT CORRECTION MEMORY VERIFICATION
    # -------------------------------------------------------------
    print("\n--- [B] Testing Personalized STT Correction Memory ---")
    test_user_id = "user_himesh_demo"

    # Step 1: Confirm correction "image" -> "Himesh" with context "my name is"
    confirm_req = {
        "user_id": test_user_id,
        "incorrect_text": "image",
        "correct_text": "Himesh",
        "context": "my name is",
    }
    conf_resp = client.post("/api/v1/corrections/confirm", json=confirm_req)
    assert conf_resp.status_code == 200
    print(f"Confirmed Correction: 'image' -> 'Himesh' (Context: 'my name is') for user '{test_user_id}'")

    # Step 2: Matching Context Case
    test_transcript_1 = "Hello everyone, my name is image and I am pleased to meet you."
    corrected_1, applied_1 = CorrectionService.apply_corrections(test_user_id, test_transcript_1)
    print(f"\n1. Matching Context Input:  '{test_transcript_1}'")
    print(f"   Corrected Output:        '{corrected_1}'")
    print(f"   Applied: {applied_1}")
    assert "my name is Himesh" in corrected_1 or "My name is Himesh" in corrected_1
    assert len(applied_1) == 1

    # Step 3: Non-Matching Context Case (General image usage must be preserved!)
    test_transcript_2 = "This is a beautiful image of the sunset."
    corrected_2, applied_2 = CorrectionService.apply_corrections(test_user_id, test_transcript_2)
    print(f"\n2. Non-Matching Context Input: '{test_transcript_2}'")
    print(f"   Output (Must NOT replace):  '{corrected_2}'")
    print(f"   Applied: {applied_2}")
    assert corrected_2 == "This is a beautiful image of the sunset."
    assert len(applied_2) == 0

    print(">>> Context-Aware Personalized Correction Memory PASSED all checks!")

    # -------------------------------------------------------------
    # PART C: COMPLETE END-TO-END VOICE LEARNING LOOP
    # -------------------------------------------------------------
    print("\n--- [C] Testing Complete End-to-End Voice Learning Pipeline ---")
    target_prompt = "And so my fellow Americans, ask not what your country can do for you, ask what you can do for your country."
    
    e2e_data = {
        "target_text": target_prompt,
        "user_id": test_user_id,
        "synthesize_tts": "true",
    }
    e2e_files = {
        "file": ("sample_jfk.flac", audio_bytes, "audio/flac")
    }

    t0_loop = time.perf_counter()
    loop_resp = client.post("/api/v1/voice-learning/process", data=e2e_data, files=e2e_files)
    t_loop_total = round(time.perf_counter() - t0_loop, 4)

    print(f"\nLoop HTTP Status: {loop_resp.status_code}")
    assert loop_resp.status_code == 200
    loop_result = loop_resp.json()

    print("\n=== PIPELINE EXECUTION SUMMARY ===")
    print(f"- Attempt ID: {loop_result['attempt_id']}")
    print(f"- User ID: {loop_result['user_id']}")
    print(f"- Target Text: {target_prompt}")
    print(f"- Original STT Transcript: {loop_result['original_transcript']}")
    print(f"- Corrected Transcript:    {loop_result['corrected_transcript']}")
    print(f"- Pronunciation Score:     {loop_result['pronunciation_result']['overall_score']}/100")
    print(f"- Accent Status:           {loop_result['accent_result']['model_status']} (Accent: {loop_result['accent_result']['accent']})")
    print(f"- Feedback Summary:        {loop_result['feedback_result']['overall_summary']}")
    print(f"- Preserved Score:         {loop_result['feedback_result']['scores_summary']['overall_pronunciation_score']}/100")
    print(f"- TTS Generated:           {loop_result['tts_result'] is not None}")

    print("\n=== LATENCY BREAKDOWN ===")
    timings = loop_result["timings"]
    print(f"1. Audio Validation:     {timings['audio_validation_seconds']}s")
    print(f"2. Speech-to-Text (STT): {timings['stt_seconds']}s")
    print(f"3. Correction Memory:    {timings['correction_seconds']}s")
    print(f"4. Pronunciation Assmt:  {timings['pronunciation_seconds']}s")
    print(f"5. Accent Analysis:      {timings['accent_seconds']}s")
    print(f"6. AI Feedback Gen:      {timings['feedback_seconds']}s")
    print(f"7. TTS Synthesis:        {timings['tts_seconds']}s")
    print(f"----------------------------------------")
    print(f"Total Pipeline Latency:  {timings['total_pipeline_seconds']}s (Client Roundtrip: {t_loop_total}s)")

    print("\n" + "=" * 70)
    print(">>> ALL PHASE 6 REAL VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
