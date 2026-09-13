# API Reference

## Base URL
- Local: `http://localhost:8000`
- API Prefix: `/api/v1`

---

## 1. System Health

### `GET /health`
Direct root endpoint for health checks and container readiness probes.

**Response (HTTP 200)**
```json
{
  "status": "healthy",
  "app_name": "Voice Learning & Accent Analysis Backend",
  "environment": "development",
  "version": "0.1.0",
  "details": {
    "debug": true
  }
}
```

### `GET /api/v1/health`
Versioned health and system diagnostics endpoint.

---

## 2. Audio Validation & Ingestion

### `POST /api/v1/audio/validate`
Uploads an audio file for strict byte header inspection, magic byte verification, MIME/extension alignment, size constraints, and duration validation.

---

## 3. Speech-to-Text (STT)

### `POST /api/v1/stt/transcribe`
Transcribes an uploaded audio file using the configured STT engine (`faster-whisper`), enforcing Phase 1 validation prior to model inference.

---

## 4. Pronunciation Assessment (Phase 3)

### `POST /api/v1/pronunciation/assess`
Compares user-spoken audio recording against a target text prompt. Performs acoustic time-alignment, word-level scoring, phoneme representation, omission/substitution detection, and generates an overall pronunciation score.

> [!NOTE]
> **Methodology Notice**: Word scores are derived from acoustic posterior probabilities and DTW sequence alignment. Phoneme objects represent lexicon-projected constituent phonemes inheriting the word's acoustic score (`is_derived=true`), not independent sub-word forced alignment acoustic models.

**Request**
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `target_text`: (Required string, the sentence the user was prompted to speak)
  - `file`: (Required binary audio file)

**Response (HTTP 200 - Success)**
```json
{
  "target_text": "And so my fellow Americans, ask not what your country can do for you, ask what you can do for your country.",
  "transcript": "And so my fellow Americans, ask not what your country can do for you, ask what you can do for your country.",
  "overall_score": 95.2,
  "confidence": 0.952,
  "duration_seconds": 11.0,
  "processing_time_seconds": 3.635,
  "words": [
    {
      "target": "and",
      "spoken": "And",
      "score": 63.8,
      "status": "correct",
      "start": 0.0,
      "end": 0.5,
      "acoustic_confidence": 0.638,
      "phonemes": [
        {
          "phoneme": "AE",
          "score": 63.8,
          "status": "correct",
          "start": 0.0,
          "end": 0.5,
          "is_derived": true
        },
        {
          "phoneme": "N",
          "score": 63.8,
          "status": "correct",
          "start": 0.0,
          "end": 0.5,
          "is_derived": true
        },
        {
          "phoneme": "D",
          "score": 63.8,
          "status": "correct",
          "start": 0.0,
          "end": 0.5,
          "is_derived": true
        }
      ],
      "notes": null
    }
  ],
  "phonemes": [
    {
      "phoneme": "AE",
      "score": 63.8,
      "status": "correct",
      "start": 0.0,
      "end": 0.5,
      "is_derived": true
    }
  ],
  "issues": [],
  "metadata": {
    "model": "acoustic-whisper-aligner:base.en",
    "target_token_count": 22,
    "spoken_token_count": 22,
    "scoring_engine": "acoustic_alignment_dtw",
    "phoneme_methodology": "word_posterior_mapped_to_lexicon_phonemes",
    "filename": "sample_jfk.flac"
  }
}
```

**Error Responses**
- **HTTP 400 Bad Request**:
  - Missing or empty target text: `{"error": true, "message": "Target text must not be empty."}`
  - Target text exceeds maximum length (default 1000 chars).
  - Invalid / corrupt / duration out of bounds audio.
- **HTTP 415 Unsupported Media Type**: Invalid audio format.
- **HTTP 422 Unprocessable Content**: Missing required form field or upload.
- **HTTP 500 Internal Server Error**: Model alignment failure or inference error.

---

## 5. Accent Analysis (Phase 4)

### `POST /api/v1/accent/analyze`
Accepts an audio file upload, verifies audio integrity via Phase 1 validation, extracts a 38-dimensional acoustic and prosodic feature vector (MFCCs, pitch $F_0$ distribution, speech rate, articulation rate, pause ratio, spectral centroid, spectral rolloff, spectral flatness, zero crossing rate, RMS energy), and performs accent analysis with explicit calibration state reporting.

> [!IMPORTANT]
> **Strict Decoupling**: Accent analysis describes acoustic speech characteristics and does not compute a pronunciation correctness penalty. Because no human-labeled training dataset is loaded by default, the active classifier returns `model_status: "not_calibrated"` and `accent: "unknown"` with full acoustic feature metrics.

**Request**
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: (Required binary audio file `.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac`, `.webm`)

**Response (HTTP 200 - Success)**
```json
{
  "accent": "unknown",
  "confidence": 0.0,
  "model_status": "not_calibrated",
  "features": {
    "pitch_f0_mean_hz": 229.3,
    "pitch_f0_std_hz": 51.63,
    "pitch_f0_range_hz": 146.94,
    "speech_rate_syllables_per_sec": 3.09,
    "articulation_rate": 6.6,
    "pause_duration_ratio": 0.532,
    "spectral_centroid_mean": 1246.24,
    "spectral_rolloff_mean": 1087.18,
    "spectral_flatness_mean": 0.0035,
    "zero_crossing_rate_mean": 0.0194,
    "energy_rms_mean": 0.1187,
    "energy_rms_std": 0.1373,
    "mfcc_mean": [
      -47.8966, 26.3749, -7.2786, 1.246, -3.024, 2.8434,
      -4.6995, 0.0068, -0.3121, -1.7105, 0.911, -1.0283, 0.8071
    ],
    "mfcc_std": [
      8.9675, 4.4082, 3.4266, 3.2517, 1.9429, 1.7395,
      2.6851, 1.2682, 1.2396, 1.3335, 1.1176, 1.0194, 1.0165
    ]
  },
  "explanation": [
    "Mean fundamental frequency (F0): 229.3 Hz with standard deviation 51.6 Hz (range: 146.9 Hz).",
    "Utterance exhibits high pitch variability and dynamic pitch excursions.",
    "Estimated articulation rate: 6.6 syllables/sec (pause ratio: 53.2%).",
    "Significant pause segments observed across the speech sample.",
    "Mean spectral centroid: 1246.2 Hz (spectral roll-off: 1087.2 Hz).",
    "Note: Classifier is in development status ('not_calibrated'). Acoustic features are extracted accurately, but accent classification requires a verified labeled dataset."
  ],
  "metadata": {
    "model_name": "acoustic_prosody_baseline",
    "model_version": "0.1.0",
    "model_type": "heuristic_acoustic_analyzer",
    "training_dataset": null,
    "training_date": null,
    "duration_seconds": 11.0,
    "sample_rate": 44100
  }
}
```

**Error Responses**
- **HTTP 400 Bad Request**: Corrupt, unreadable, or out-of-bounds duration audio.
- **HTTP 413 Payload Too Large**: Audio exceeds maximum allowed file size (25 MB).
- **HTTP 415 Unsupported Media Type**: Unsupported audio extension/container.
- **HTTP 422 Unprocessable Content**: Missing audio file in multipart request.

---

## 6. AI Feedback & Personalized Learning (Phase 5)

### `POST /api/v1/feedback/generate`
Accepts structured outputs from Phase 2 (STT), Phase 3 (Pronunciation Assessment), and Phase 4 (Accent Analysis), and synthesizes personalized, encouraging pedagogical feedback with actionable recommendations and practice drills.

> [!NOTE]
> **Resilience & Privacy**: If no OpenAI API key is configured or if network calls fail, the service transparently generates high-quality deterministic fallback feedback (`is_fallback=true`). Numerical scores from previous phases are preserved without alteration.

**Request**
- **Content-Type**: `application/json`
- **Body (`FeedbackGenerationRequest`)**:
```json
{
  "stt_result": { ... },
  "pronunciation_result": { ... },
  "accent_result": { ... },
  "user_id": "optional_user_id",
  "session_id": "optional_session_id"
}
```

**Response (HTTP 200 - Success)**
```json
{
  "overall_summary": "Excellent delivery! Your overall pronunciation score is 90.3/100. Your spoken words demonstrated high acoustic clarity and intelligibility throughout the passage.",
  "pronunciation_feedback": "Your pronunciation aligned closely with the target prompt with zero critical word-level errors.",
  "accent_feedback": "Acoustic analysis shows an articulation rate of 6.6 syllables/sec with a mean fundamental pitch of 229.3 Hz. Note: Accent classification is in development status ('not_calibrated') and regional labels are not assigned.",
  "strengths": [
    "Correctly and clearly enunciated 14 out of 14 target words.",
    "High acoustic confidence and distinct voice clarity.",
    "Natural, well-controlled overall speaking rate."
  ],
  "areas_to_improve": [
    "Reduce extended pause intervals between phrases to improve natural speech flow."
  ],
  "practice_recommendations": [
    "Read aloud at a steady, deliberate tempo while recording yourself.",
    "Break multi-syllable challenging words into individual syllables before speaking full sentences."
  ],
  "suggested_exercises": [
    {
      "title": "Rhythm and Phrasing Practice",
      "exercise_type": "pacing",
      "target_words": [],
      "instructions": "Speak the target sentence using metronome pacing, pausing only at natural comma or clause boundaries.",
      "sample_sentence": "And so my fellow Americans, ask not what your country can do for you."
    }
  ],
  "scores_summary": {
    "overall_pronunciation_score": 90.3,
    "pronunciation_confidence": 0.903,
    "accent_label": "unknown",
    "accent_model_status": "not_calibrated",
    "accent_confidence": 0.0,
    "words_total": 14,
    "words_correct": 14,
    "issues_detected_count": 0
  },
  "is_fallback": true,
  "provider": "deterministic_fallback",
  "model": "rule_based_v1"
}
```

**Error Responses**
- **HTTP 422 Unprocessable Content**: Request payload does not adhere to `FeedbackGenerationRequest` schema.

---

## 7. Text-to-Speech (TTS) (Phase 6)

### `POST /api/v1/tts/synthesize`
Synthesizes speech audio from text input with selectable voice and format.

**Request**
- **Content-Type**: `application/json`
- **Body**:
```json
{
  "text": "Welcome to your voice learning practice session.",
  "voice": "alloy",
  "audio_format": "mp3"
}
```

**Response (HTTP 200 - Success)**
```json
{
  "audio_base64": "...",
  "format": "mp3",
  "voice": "alloy",
  "provider": "openai",
  "model": "tts-1",
  "character_count": 48,
  "is_fallback": false
}
```

---

## 8. Personalized STT Correction Memory (Phase 6)

### `POST /api/v1/corrections/confirm`
Stores or updates a user-specific STT correction (e.g. `'image'` $\to$ `'Himesh'` when context is `'my name is'`).

**Request**
```json
{
  "user_id": "user_123",
  "incorrect_text": "image",
  "correct_text": "Himesh",
  "context": "my name is"
}
```

**Response (HTTP 200 - Success)**
```json
{
  "id": "c1f7a0...",
  "user_id": "user_123",
  "incorrect_text": "image",
  "correct_text": "Himesh",
  "context_phrase": "my name is",
  "occurrence_count": 1,
  "confidence": 0.85,
  "created_at": "2026-09-12T04:20:00Z",
  "updated_at": "2026-09-12T04:20:00Z"
}
```

### `GET /api/v1/corrections/{user_id}`
Retrieves all stored corrections for a user.

---

## 9. End-to-End Voice Learning Loop (Phase 6)

### `POST /api/v1/voice-learning/process`
Orchestrates the entire multi-phase voice learning pipeline: Audio Validation $\to$ STT $\to$ Correction Memory $\to$ Pronunciation $\to$ Accent $\to$ AI Feedback $\to$ TTS Synthesis $\to$ Database Persistence.

**Request (`multipart/form-data`)**:
- `target_text`: Target sentence string
- `file`: Audio recording file
- `user_id`: Optional user ID
- `synthesize_tts`: Optional boolean (default `true`)

**Response (HTTP 200 - Success)**
```json
{
  "attempt_id": "fcf3b3d3-10b1-416d-997f-894bfa82c6a6",
  "user_id": "user_123",
  "original_transcript": "Hello, my name is image.",
  "corrected_transcript": "Hello, my name is Himesh.",
  "applied_corrections": [
    {
      "correction_id": "c1f7a0...",
      "original": "image",
      "replaced_with": "Himesh",
      "context_matched": true
    }
  ],
  "pronunciation_result": {
    "overall_score": 92.5,
    "confidence": 0.925
  },
  "accent_result": {
    "accent": "unknown",
    "model_status": "not_calibrated"
  },
  "feedback_result": {
    "overall_summary": "Great pronunciation clarity!",
    "scores_summary": {
      "overall_pronunciation_score": 92.5
    }
  },
  "tts_result": {
    "audio_base64": "...",
    "format": "wav"
  },
  "timings": {
    "audio_validation_seconds": 0.045,
    "stt_seconds": 1.25,
    "correction_seconds": 0.001,
    "pronunciation_seconds": 2.10,
    "accent_seconds": 0.85,
    "feedback_seconds": 0.001,
    "tts_seconds": 0.005,
    "total_pipeline_seconds": 4.25
  }
}
```
