# Phase 6 — TTS & End-to-End Voice Learning Loop

## 🎯 Phase Goal
Orchestrate all verified subsystem layers:
1. **Audio Validation & Ingestion** (Phase 1)
2. **Speech-to-Text (STT)** (Phase 2)
3. **Personalized STT Correction Memory** (Phase 6)
4. **Pronunciation Assessment** (Phase 3)
5. **Accent Analysis** (Phase 4)
6. **AI Feedback & Practice Drills** (Phase 5)
7. **Text-to-Speech (TTS)** (Phase 6)
8. **Relational Data Persistence** (Phase 6)

into a single unified, ultra-reliable, context-aware voice learning loop.

---

## 🏛️ End-to-End Pipeline Architecture

```mermaid
graph TD
    UserAudio[User Audio Upload + Target Sentence] --> V1[Phase 1: AudioValidatorService]
    V1 --> STT[Phase 2: faster-whisper STT Service]
    STT --> RawTranscript[Original STT Transcript]
    RawTranscript --> Memory[Phase 6: Personalized Correction Memory Service]
    Memory --> CorrectedTranscript[Corrected Transcript (e.g. 'image' -> 'Himesh')]
    V1 --> Pron[Phase 3: Pronunciation Assessment Orchestrator]
    V1 --> Accent[Phase 4: Accent Feature Extractor & Classifier]
    STT --> FB[Phase 5: AI Feedback & Personalized Drills Engine]
    Pron --> FB
    Accent --> FB
    FB --> FeedbackPayload[Structured Learning Feedback]
    FeedbackPayload --> TTS[Phase 6: OpenAI / Fallback Text-to-Speech Service]
    TTS --> FinalAudio[Synthesized Speech Audio]
    FinalAudio --> SQLiteDB[(Phase 6: SQLite / PostgreSQL Storage)]
    SQLiteDB --> FinalResponse[POST /api/v1/voice-learning/process Response]
```

---

## 🧠 Personalized STT Correction Memory

### Design & Behavior
The correction service (`CorrectionService` in `app/services/correction/correction_service.py`) enables user-specific acoustic corrections to overcome recurring STT misrecognitions (such as uncommon names, domain-specific terminology, or non-standard proper nouns):

- **User Isolation**: Corrections configured for User A never alter transcripts for User B.
- **Context-Aware Replacement**:
  - Example: User confirms `"image"` $\to$ `"Himesh"` with context `"my name is"`.
  - Input: `"Hello, my name is image"` $\to$ transformed to `"Hello, my name is Himesh"`.
  - Input: `"This is an image of the sky"` $\to$ **NOT replaced** (general vocabulary usage is preserved).
- **Frequency & Confidence Tracking**: Tracks `occurrence_count` and updates replacement confidence weightings.
- **Transcript Separation**: Never overwrites the raw STT output; `original_transcript` and `corrected_transcript` are stored and returned side-by-side.

---

## 🔊 Text-to-Speech (TTS) Layer

- **Provider**: Modular `BaseTTSProvider` with `OpenAITTSProvider` (`tts-1` / `tts-1-hd` targeting voices `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`).
- **Resilient Fallback**: `DeterministicFallbackTTSProvider` generates standard dual-harmonic audio bytes if the external API is offline or unconfigured, preventing pipeline failures.
- **Dual Response Format**: Supports JSON metadata with Base64 audio payload or direct binary streaming via `?raw_audio=true`.

---

## 🗄️ Database Schema & Storage

The application leverages a relational SQLite schema (`backend/app/db/database.py`):
1. `users`: User identity records.
2. `practice_sessions`: User practice session tracking.
3. `speech_attempts`: Records `attempt_id`, `target_text`, `original_transcript`, `corrected_transcript`, `duration_seconds`.
4. `corrections`: `user_id`, `incorrect_text`, `correct_text`, `context_phrase`, `occurrence_count`, `confidence`.
5. `pronunciation_results`: Word scores, constituent phoneme mappings, detected issues.
6. `accent_results`: Accent label, confidence, calibration state (`not_calibrated`), 38-dim acoustic features.
7. `feedback_records`: Summary, strengths, areas to improve, practice drills, fallback status.

---

## 🔌 API Endpoints

### 1. `POST /api/v1/tts/synthesize`
Synthesizes speech audio from text input.

### 2. `POST /api/v1/corrections/confirm`
Explicitly confirms or updates a personalized user STT correction.

### 3. `GET /api/v1/corrections/{user_id}`
Retrieves all stored corrections for the specified user.

### 4. `POST /api/v1/voice-learning/process`
Executes the full multi-phase voice learning loop.

**Sample Request**:
- `target_text`: `"And so my fellow Americans, ask not what your country can do for you."`
- `file`: `sample.flac`
- `user_id`: `"user_himesh_demo"`
- `synthesize_tts`: `true`

**Sample Response**:
```json
{
  "attempt_id": "fcf3b3d3-10b1-416d-997f-894bfa82c6a6",
  "user_id": "user_himesh_demo",
  "original_transcript": "And so my fellow Americans, ask not what your country can do for you, ask what you can do for your country.",
  "corrected_transcript": "And so my fellow Americans, ask not what your country can do for you, ask what you can do for your country.",
  "applied_corrections": [],
  "pronunciation_result": {
    "overall_score": 95.4,
    "confidence": 0.954,
    "words": []
  },
  "accent_result": {
    "accent": "unknown",
    "confidence": 0.0,
    "model_status": "not_calibrated",
    "features": {}
  },
  "feedback_result": {
    "overall_summary": "Excellent delivery! Your overall pronunciation score is 95.4/100.",
    "strengths": ["Correctly and clearly enunciated 14 out of 14 target words."],
    "scores_summary": {
      "overall_pronunciation_score": 95.4,
      "accent_model_status": "not_calibrated"
    }
  },
  "tts_result": {
    "audio_base64": "...",
    "format": "wav",
    "voice": "alloy",
    "provider": "deterministic_fallback",
    "model": "synthetic_audio_v1",
    "character_count": 162,
    "is_fallback": true
  },
  "timings": {
    "audio_validation_seconds": 0.0479,
    "stt_seconds": 3.5091,
    "correction_seconds": 0.0014,
    "pronunciation_seconds": 2.6732,
    "accent_seconds": 0.9028,
    "feedback_seconds": 0.0005,
    "tts_seconds": 0.0066,
    "total_pipeline_seconds": 7.1438
  }
}
```

---

## 🧪 Verification & Audit Results
- **Automated Tests**: **58 / 58 passed (100%)**
- **Context-Aware Memory**: Verified that `"my name is image"` transforms to `"my name is Himesh"`, while `"this is an image"` is preserved without alteration.
- **Full System Latency**: Real speech sample (11.0s) fully validated, transcribed, assessed, analyzed, feedback-generated, TTS-synthesized, and stored in ~7.1 seconds total.
