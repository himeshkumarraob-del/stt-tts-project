import os
import time
from app.services.pronunciation.assessor import AcousticPronunciationAssessor
from app.schemas.pronunciation import PronunciationAssessmentResponse


def run_real_pronunciation_verification():
    print("==================================================================")
    print("RUNNING REAL PRONUNCIATION ASSESSMENT INFERENCE (NO MOCKS)")
    print("==================================================================")
    
    # Target phrase matching sample speech audio
    target_sentence = "And so my fellow Americans, ask not what your country can do for you, ask what you can do for your country."
    
    audio_path = os.path.join(os.path.dirname(__file__), "sample_jfk.flac")
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    
    assessor = AcousticPronunciationAssessor(model_size="base.en")
    print(f"Loaded Assessor: '{assessor.model_name}'")
    
    start_t = time.perf_counter()
    result: PronunciationAssessmentResponse = assessor.assess(
        target_text=target_sentence,
        audio_bytes=audio_bytes,
        audio_duration_seconds=11.0,
        filename="sample_jfk.flac"
    )
    total_time = round(time.perf_counter() - start_t, 4)
    
    print("\n--- REAL PRONUNCIATION ASSESSMENT RESULTS ---")
    print(f"Target Text: \"{result.target_text}\"")
    print(f"Recognized Transcript: \"{result.transcript}\"")
    print(f"Overall Pronunciation Score: {result.overall_score} / 100")
    print(f"Assessment Confidence: {result.confidence}")
    print(f"Audio Duration: {result.duration_seconds}s | Processing Time: {result.processing_time_seconds}s (Total: {total_time}s)")
    print(f"Total Words Assessed: {len(result.words)}")
    print(f"Total Phonemes Analyzed: {len(result.phonemes)}")
    print(f"Pronunciation Issues Detected: {len(result.issues)}")
    
    print("\nWord-Level Alignment & Scoring Breakdown:")
    for w in result.words:
        print(f"  - Target: {w.target:<12} | Spoken: {str(w.spoken):<12} | Score: {w.score:>5.1f} | Status: {w.status.value:<15} | Conf: {w.acoustic_confidence:.2f}")
    
    print("==================================================================")
    assert result.overall_score >= 80.0, "Score for clear matching speech should be high"
    assert len(result.words) > 0
    return result


if __name__ == "__main__":
    run_real_pronunciation_verification()
