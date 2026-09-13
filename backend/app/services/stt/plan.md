# Phase 2: Speech-to-Text (STT) Layer Implementation Plan

## Goal
Implement a modular, production-ready Speech-to-Text (STT) layer powered by `faster-whisper` (with configurable provider abstraction, e.g., local Whisper vs cloud speech APIs in the future), fully integrated with Phase 1 audio validation, supporting English including Indian-English accents with zero grammar modification.

## 1. Requirements & Constraints
- Modular STT architecture under `backend/app/services/stt/`:
  - `base.py`: Abstract base class `BaseSTTProvider` ensuring pluggable providers.
  - `whisper_provider.py`: Concrete provider using `faster-whisper` (default model `base.en` or `tiny.en`, `cpu`, `int8` compute for laptop compatibility).
  - `stt_service.py`: Orchestrator service that validates audio using Phase 1 `AudioValidatorService`, invokes the configured provider, measures processing time, and normalizes output.
- Target Python 3.12 compatibility.
- Endpoint: `POST /api/v1/stt/transcribe`.
- Response Schema:
  ```json
  {
    "text": "...",
    "language": "en",
    "duration_seconds": 1.23,
    "processing_time_seconds": 0.45,
    "provider": "faster-whisper",
    "model": "base.en",
    "segments": [...]
  }
  ```
- Error Handling: Custom STT exceptions (`STTServiceError`, `STTModelLoadError`, `STTTranscriptionError`, `STTConfigurationError`) with clean HTTP status codes.
- Language Handling: Preserve actual user speech verbatim; no grammar correction.
- Automated Tests: 10+ test scenarios with mocked and live test fixtures.
- Synchronization with README, .env.example, and Obsidian documentation.
