import os
import time
from app.services.stt.whisper_provider import FasterWhisperProvider
from app.schemas.stt import TranscriptionResponse


def run_real_stt_verification():
    print("==================================================================")
    print("RUNNING REAL FASTER-WHISPER MODEL INFERENCE (NO MOCKS)")
    print("==================================================================")
    
    # 1. Initialize real FasterWhisperProvider with default configuration
    provider = FasterWhisperProvider(model_size="base.en", device="cpu", compute_type="int8")
    print(f"Loading Model: '{provider.model_name}' on device='{provider._device}', compute_type='{provider._compute_type}'...")
    
    load_start = time.perf_counter()
    model = provider._get_model()
    load_time = round(time.perf_counter() - load_start, 4)
    print(f"Model loaded successfully in {load_time}s.")
    
    # 2. Read real standard English speech audio sample (JFK historic public address sample from faster-whisper tests)
    audio_path = os.path.join(os.path.dirname(__file__), "sample_jfk.flac")
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    
    print(f"Loaded test audio: {len(audio_bytes)} bytes, format: FLAC")
    
    # 3. Perform real inference
    infer_start = time.perf_counter()
    result: TranscriptionResponse = provider.transcribe(
        audio_bytes=audio_bytes,
        audio_duration_seconds=11.0,
        language="en",
        filename="sample_jfk.flac"
    )
    infer_time = round(time.perf_counter() - infer_start, 4)
    
    print("\n--- REAL INFERENCE RESULTS ---")
    print(f"Provider: {result.provider}")
    print(f"Model: {result.model}")
    print(f"Language: {result.language}")
    print(f"Audio Duration: {result.duration_seconds}s")
    print(f"Processing Time: {result.processing_time_seconds}s (Total script time: {infer_time}s)")
    print(f"Transcribed Text: '{result.text}'")
    print(f"Segments Count: {len(result.segments)}")
    for seg in result.segments:
        print(f"  [{seg.start}s -> {seg.end}s] (logprob={seg.avg_logprob}): {seg.text}")
    print(f"Metadata: {result.metadata}")
    print("==================================================================")
    
    assert len(result.text.strip()) > 0, "Transcribed text should not be empty!"
    return result


if __name__ == "__main__":
    run_real_stt_verification()
