# Voice Learning & Indian-English Accent Analysis System — Backend

FastAPI-powered backend designed for speech processing, acoustic feature validation, speech-to-text, and pronunciation assessment workflows.

---

## 🛠️ Features
- **FastAPI Core**: Modular structure with automated Swagger (`/docs`) and ReDoc (`/redoc`) documentation.
- **Python 3.12 Target**: Modern typing, async handlers, and Pydantic v2 validation.
- **Configuration Management**: Centralized environment variable management via `pydantic-settings`.
- **System Health Checks**: `/health` and `/api/v1/health` diagnostic endpoints.
- **Audio Validation Infrastructure (Phase 1)**:
  - Magic byte sniffing & actual payload header inspection (`RIFF`, `ID3`, `OggS`, `fLaC`, `ftyp`, etc.).
  - File extension & MIME type alignment check.
  - File size limits (default: 25MB max).
  - Duration constraint checking (default: minimum 0.5s, maximum 120s).
  - Deep metadata extraction (sampling rate, channels, duration, format).
- **Speech-to-Text (STT) Layer (Phase 2)**:
  - Plug-and-play provider architecture (`BaseSTTProvider`, `FasterWhisperProvider`, `STTService`).
  - Pretrained `faster-whisper` CTranslate2 model integration (`base.en` default on `cpu` with `int8` quantization).
  - Preserves verbatim Indian-English and accented speech without grammar alteration.
  - Accurate latency tracking and segment-level timestamps.
- **Pronunciation Assessment Layer (Phase 3)**:
  - Sequence alignment via Dynamic Time Warping (DTW) and Needleman-Wunsch algorithm.
  - Word-level acoustic posterior scoring (0-100 scale).
  - Phoneme breakdown (ARPAbet/G2P lexicon) with acoustic time alignment.
  - Detection of omissions, substitutions, and insertions.
  - Configurable support for standard Indian-English phonetic variations.
- **Indian-English Accent Analysis Layer (Phase 4)**:
  - 38-dimensional acoustic, spectral, prosodic, and cepstral feature extraction (13 MFCCs mean/std, F0 pitch statistics, speech & articulation rates, pause ratio, spectral centroid, spectral rolloff, spectral flatness, zero-crossing rate, RMS energy).
  - Explicit calibration tracking: returns `model_status: "not_calibrated"` with honest acoustic descriptions until a validated labeled dataset is trained.
  - Strict decoupling: accent analysis describes acoustic characteristics and never penalizes pronunciation correctness scores.
  - Extensible training pipeline (`prepare_dataset.py`, `extract_features.py`, `train.py`, `evaluate.py`, `inference.py`) supporting speaker-independent splits to prevent acoustic identity leakage.
- **AI Feedback & Personalized Learning Layer (Phase 5)**:
  - Synthesizes STT, Pronunciation Assessment, and Accent Analysis into personalized, encouraging, actionable learning feedback.
  - Modular provider architecture (`BaseFeedbackProvider`, `OpenAIFeedbackProvider`, `DeterministicFallbackProvider`).
  - Score preservation: authoritative numerical scores from previous phases are preserved without alteration.
  - Prompt injection defense: user speech and transcript payloads are treated as untrusted data boundaries.
  - Accent calibration safety: prevents hallucinated regional accent labels when accent models are in uncalibrated development status.
  - High-resilience deterministic fallback: guarantees 100% endpoint reliability even when third-party LLM APIs are offline or unconfigured.
- **Text-to-Speech & End-to-End Voice Learning Loop (Phase 6)**:
  - Text-to-Speech (TTS) service with OpenAI (`tts-1`) and deterministic fallback generator.
  - Personalized context-aware STT correction memory (stores user-specific word replacements such as `"image"` $\to$ `"Himesh"` with context constraints).
  - Complete End-to-End Voice Learning Loop endpoint (`POST /api/v1/voice-learning/process`) connecting Audio Validation $\to$ STT $\to$ Correction Memory $\to$ Pronunciation Assessment $\to$ Accent Analysis $\to$ AI Feedback $\to$ TTS $\to$ Relational SQLite Database Storage.
  - Detailed component-by-component latency tracking.
- **Error Handling & Logging**: Unified exception hierarchy and formatted stream logging.
- **Automated Testing Suite**: Full integration test coverage via `pytest` (58 tests passing).

---

## 📁 Directory Structure
```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── accent.py
│   │       │   ├── audio.py
│   │       │   ├── corrections.py
│   │       │   ├── feedback.py
│   │       │   ├── health.py
│   │       │   ├── pronunciation.py
│   │       │   ├── tts.py
│   │       │   └── voice_learning.py
│   │       └── router.py
│   ├── core/
│   │   ├── config.py
│   │   ├── errors.py
│   │   └── logging.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── database.py
│   ├── models/
│   ├── schemas/
│   │   ├── accent.py
│   │   ├── audio.py
│   │   ├── correction.py
│   │   ├── feedback.py
│   │   ├── health.py
│   │   ├── pronunciation.py
│   │   ├── stt.py
│   │   ├── tts.py
│   │   └── voice_learning.py
│   ├── services/
│   │   ├── accent/
│   │   │   ├── __init__.py
│   │   │   ├── accent_service.py
│   │   │   ├── base.py
│   │   │   ├── classifier.py
│   │   │   └── features.py
│   │   ├── audio_validator.py
│   │   ├── correction/
│   │   │   ├── __init__.py
│   │   │   └── correction_service.py
│   │   ├── feedback/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── fallback_provider.py
│   │   │   ├── feedback_service.py
│   │   │   ├── openai_provider.py
│   │   │   └── prompts.py
│   │   ├── pronunciation/
│   │   │   ├── __init__.py
│   │   │   ├── aligner.py
│   │   │   ├── assessor.py
│   │   │   ├── base.py
│   │   │   ├── phonetics.py
│   │   │   └── pronunciation_service.py
│   │   └── stt/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── faster_whisper.py
│   │       └── stt_service.py
│   │   └── tts/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── fallback_tts.py
│   │       ├── openai_tts.py
│   │       └── tts_service.py
│   └── main.py
├── training/
│   └── accent/
│       ├── prepare_dataset.py
│       ├── extract_features.py
│       ├── train.py
│       ├── evaluate.py
│       └── inference.py
├── tests/
│   ├── conftest.py
│   ├── mock_stt.py
│   ├── test_accent.py
│   ├── test_audio_validation.py
│   ├── test_feedback.py
│   ├── test_health.py
│   ├── test_pronunciation.py
│   ├── test_stt.py
│   ├── test_voice_learning.py
│   ├── verify_real_accent.py
│   ├── verify_real_api.py
│   ├── verify_real_feedback.py
│   ├── verify_real_phase6.py
│   ├── verify_real_pronunciation.py
│   └── verify_real_stt.py
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🚀 Setup & Run Instructions

### 1. Prerequisites
- Python 3.12
- pip

### 2. Environment Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 4. Run Development Server
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive API documentation will be available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 5. Run Stitch Frontend Dashboard (Phase 7 Integration)
```bash
# In a separate terminal, serve the Stitch dashboard:
python -m http.server 3000 --directory "C:\Users\Himesh kumar rao\Desktop\stitch_voice_learning_ai_dashboard"
```
Access the dashboard at:
- Practice Screen (Dark): [http://127.0.0.1:3000/practice_live_recording/code.html](http://127.0.0.1:3000/practice_live_recording/code.html)
- Practice Screen (Light): [http://127.0.0.1:3000/practice_live_recording_light/code.html](http://127.0.0.1:3000/practice_live_recording_light/code.html)
- Learned Corrections (Dark): [http://127.0.0.1:3000/learned_corrections_history/code.html](http://127.0.0.1:3000/learned_corrections_history/code.html)

---

## 🧪 Running Tests
```bash
# Automated unit/regression test suite (58 tests)
pytest -v

# Real model, feature extraction, and feedback verifications
python tests/verify_real_stt.py
python tests/verify_real_pronunciation.py
python tests/verify_real_accent.py
python tests/verify_real_feedback.py
python tests/verify_real_phase6.py
python tests/verify_real_api.py
```
