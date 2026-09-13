# Voice Learning & Indian-English Accent Analysis System

## 🌟 Project Overview
A specialized platform designed for voice learning, pronunciation assessment, and Indian-English accent analysis.

### System Workflow Roles
- **Antigravity**: Primary Backend & AI Pipeline Developer
- **Freebuff**: Code Review & Testing
- **Stitch**: Frontend Application
- **Obsidian**: Project Documentation & Knowledge Vault

---

## 🎯 Python Target Version
- **Python 3.12**

---

## 🏛️ Architecture & Component Design
```mermaid
graph TD
    Client[Stitch Frontend / Client API] -->|Target Text + Audio Stream| Gateway[FastAPI Backend Gateway]
    Gateway --> Health[Health & Diagnostics /health]
    Gateway --> Validator[Phase 1: Audio Validation & Ingestion]
    Validator --> STTService[Phase 2: STT Service Orchestrator]
    STTService --> WhisperProvider[faster-whisper CTranslate2 Provider]
    Validator --> PronService[Phase 3: Pronunciation Assessment Orchestrator]
    PronService --> DTWAligner[Sequence & Word Aligner (DTW / Needleman-Wunsch)]
    PronService --> PhonemeEngine[Phoneme Lexicon & Indian-English Equivalence G2P Engine]
    PronService --> AcousticAssessor[Acoustic Pronunciation Assessor (Acoustic Posterior Probabilities)]
    AcousticAssessor --> ScoreMatrix[Word Scores, Derived Phoneme Mappings & Issue Detection]
    ScoreMatrix --> PronOutput[Structured Pronunciation Assessment Result]
    Validator --> AccentService[Phase 4: Accent Analysis Service Orchestrator]
    AccentService --> FeatureExtractor[AcousticFeatureExtractor (38-dim MFCC, F0, Prosody, Spectral)]
    AccentService --> AccentClassifier[BaseAccentClassifier: DevelopmentBaseline / TrainedAccentClassifier]
    AccentClassifier --> AccentOutput[POST /api/v1/accent/analyze (Status: not_calibrated)]
    PronOutput --> FeedbackService[Phase 5: AI Feedback & Personalized Learning Orchestrator]
    STTService --> FeedbackService
    AccentOutput --> FeedbackService
    FeedbackService --> LLMProvider[OpenAIFeedbackProvider / DeterministicFallbackProvider]
    LLMProvider --> FeedbackOutput[Phase 5: Structured Feedback & Drills]
    FeedbackOutput --> TTSService[Phase 6: Text-to-Speech Service]
    TTSService --> TTSAudio[Synthesized Audio Output]
    FeedbackOutput --> DB[(Phase 6: SQLite / PostgreSQL Persistent Storage)]
    TTSAudio --> VoiceLoop[POST /api/v1/voice-learning/process]
```

---

## 📏 Audio Ingestion & Assessment Specifications
- **Magic Header & Sniffing Inspection**: Verification against magic numbers (`RIFF`, `ID3`, `OggS`, `fLaC`, `ftyp`).
- **Maximum File Size**: 25 MB (26,214,400 bytes).
- **Duration Bounds**: Minimum 0.5s, Maximum 120.0s.
- **Supported Containers/Formats**: WAV, MP3, M4A, OGG, FLAC, AAC, WEBM.
- **Speech-to-Text Engine**: `faster-whisper` running quantized CTranslate2 models (`base.en` default on `cpu` / `int8`).
- **Correction Memory Engine**: User-specific context-aware STT error correction and frequency tracking.
- **Pronunciation Assessment Engine**: Dynamic Time Warping (DTW) word sequence alignment + acoustic posterior probabilities.
- **Phoneme Representation**: Word-level acoustic scores mapped to constituent lexicon phonemes (`is_derived=True`).
- **Accent Analysis Engine**: 38-dimensional acoustic and prosodic feature extraction with explicit calibration state tracking (`not_calibrated`).
- **AI Feedback Engine**: Structured, prompt-injection defended personalized learning generator with resilient deterministic fallback.
- **Text-to-Speech Engine**: OpenAI TTS (`tts-1`) with deterministic dual-harmonic acoustic fallback.
- **Persistence Layer**: Relational SQLite / PostgreSQL database schemas for attempts, results, feedback, and corrections.
- **Strict Decoupling**: Pronunciation correctness $\neq$ accent analysis.

---

## 📅 Roadmap & Phases
- [x] **Phase 1: Backend Foundation & Audio Validation**
- [x] **Phase 2: Speech-to-Text (STT) Layer**
- [x] **Phase 3: Pronunciation Assessment Layer (Audited & Verified)**
- [x] **Phase 4: Indian-English Accent Feature Extraction & Classification**
- [x] **Phase 5: Pedagogical Feedback & Orchestration Layer**
- [x] **Phase 6: TTS & End-to-End Voice Learning Loop**
- [x] **Phase 7: Real Frontend ↔ Backend Integration (Stitch Dashboard)**
