# Resonant Voice Learning AI & Indian-English Accent Analysis Platform

An intelligent, multi-layer speech analysis, pronunciation assessment, and accent adaptation system built with **FastAPI**, **Faster-Whisper (CTranslate2)**, **Dynamic Time Warping (DTW)**, **ARPAbet Phonetic G2P**, and an interactive real-time **Web Audio Dashboard**.

---

## 🚀 Key Highlights & Capabilities

- **🎙️ Real-time Acoustic & Audio Ingestion**: Deep header inspection, format validation (WAV, FLAC, WebM, MP3, OGG), magic byte sniffing, and dynamic audio feature extraction.
- **⚡ Speech-to-Text (STT) Engine**: CTranslate2 quantized Faster-Whisper neural STT running locally with sub-second inference and verbatim speech capture.
- **🎯 Pronunciation Scoring & Phoneme Alignment**: Sequence alignment using DTW and Needleman-Wunsch algorithms against standard ARPAbet phonetic transcriptions. Precise omission, substitution, and insertion detection.
- **🇮🇳 Indian-English Accent Feature Analysis**: 38-dimensional acoustic, spectral, prosodic, and cepstral feature vector extraction (MFCCs, F0 pitch metrics, speech rate, pause ratios, spectral centroid/rolloff/flatness, RMS energy) with non-punitive accent characterization.
- **🧠 Personalized Context-Aware STT Memory**: Learns user-specific corrections (e.g., custom names or dialectal acoustic patterns) constrained by conversational context to prevent global over-correction.
- **🤖 Actionable AI Coaching**: Modular feedback synthesis provider delivering encouraging, structured, and phoneme-targeted pronunciation guidance with deterministic zero-downtime fallback.
- **🔊 Neural Text-to-Speech (TTS)**: Reference target pronunciation synthesis with audio playback in browser.
- **✨ Interactive Glassmorphic Frontend**: Dark & Light mode real-time audio recording interface with dynamic waveform visualization, latency tracking, and learning history.

---

## 📁 Repository Structure

```
├── backend/                  # FastAPI Acoustic & Phonetic Processing Engine
│   ├── app/
│   │   ├── api/v1/endpoints/ # REST Endpoints (Audio, STT, Pronunciation, Accent, Feedback, TTS, Voice-Learning)
│   │   ├── core/             # Configuration & Settings
│   │   ├── db/               # SQLite Models & Database Session
│   │   ├── models/           # SQLAlchemy ORM Entities
│   │   ├── schemas/          # Pydantic Schemas & DTOs
│   │   ├── services/         # Modular Pipeline Services
│   │   │   ├── audio_validator.py
│   │   │   ├── stt/          # Faster-Whisper Provider & STT Service
│   │   │   ├── pronunciation/# DTW Alignment & Phonetic Assessor
│   │   │   ├── accent/       # 38-dim Acoustic Feature Extractor
│   │   │   ├── feedback/     # AI Feedback Provider & Fallback Engine
│   │   │   ├── tts/          # TTS Audio Generation Provider
│   │   │   └── correction/   # Context-Aware STT Correction Memory
│   │   └── main.py           # Application Entry Point & CORS Setup
│   ├── tests/                # Comprehensive Pytest Integration Suite (58 passing tests)
│   ├── training/accent/      # Accent Dataset Extraction, Training & Evaluation Pipeline
│   └── requirements.txt      # Python Dependencies
│
├── frontend/                 # Web Audio Client Dashboard
│   ├── practice_live_recording/     # Main Voice Practice & Microphone Interface (Dark Mode)
│   ├── practice_live_recording_light/# Main Voice Practice (Light Mode)
│   ├── pipeline_analysis_progress/   # Real-time Multi-Stage Acoustic Pipeline Visualizer
│   ├── analysis_results_feedback/    # Detailed Phonetic Scores & AI Coaching Results
│   ├── learned_corrections_history/  # Personalized Memory & History Management
│   └── shared/                       # Web Audio Recorder, API Client, State Machine
│
├── Voice Learning AI/        # Architectural Specifications & Phase Documentation (Phases 1 - 7)
└── PHASE_7_REAL_USER_BROWSER_QA_REPORT.md # 28-point Browser & Audio Verification Report
```

---

## 🛠️ Quick Start Guide

### 1. Backend Setup

```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux / macOS:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Start Backend Server:
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive API documentation will be available at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 2. Frontend Setup

The frontend runs as static HTML5/Tailwind/ES6 modules. You can serve it with any static web server:

```bash
cd frontend
# Using Python:
python -m http.server 3000

# Or using Node:
npx serve -p 3000 .
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Running Automated Tests

```bash
cd backend
pytest -v
```

---

## 📄 License

MIT License. Designed for robust, production-grade speech learning applications.
