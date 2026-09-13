# Phase 4 — Indian-English Accent Analysis

## 🎯 Phase Goal
Analyze user speech for Indian-English accent characteristics using genuine acoustic and prosodic features while enforcing a strict separation between **accent** and **pronunciation correctness**.

---

## ⚖️ Pronunciation Correctness vs. Accent Analysis

A fundamental design principle of this platform is that **Pronunciation Correctness $\neq$ Accent**:

| Dimension | Pronunciation Assessment (Phase 3) | Accent Analysis (Phase 4) |
| :--- | :--- | :--- |
| **Objective** | Measures intelligibility, phonemic accuracy, omissions, and insertions against target text | Describes phonetic, acoustic, and prosodic speech characteristics |
| **Scoring** | Quantitative score ($0 - 100$) reflecting intelligibility | Categorical label (`indian_english`, `non_indian_english`, `unknown`) + acoustic features |
| **Pedagogy** | Flags actual mispronunciations affecting comprehension | Identifies regional/prosodic patterns without treating Indian English as "incorrect English" |
| **API Response** | Isolated in `/api/v1/pronunciation/assess` (`overall_score`) | Isolated in `/api/v1/accent/analyze` (`model_status`, `features`, `explanation`) |

> [!IMPORTANT]
> An Indian-English speaker is never penalized with a lower pronunciation score simply because their accent exhibits characteristic Indian-English prosody or phonology.

---

## 🔬 Acoustic & Prosodic Feature Extraction

The feature extractor (`AcousticFeatureExtractor` in `app/services/accent/features.py`) extracts a 38-dimensional acoustic representation using pure `numpy` and `soundfile` signal processing:

### 1. Selected Features & Linguistic Rationale
1. **MFCC (13 Coefficients — Mean and Std Dev)**:
   - *Rationale*: Captures the overall spectral envelope and vocal tract formant structure. Indian English exhibits characteristic formant transitions for retroflex consonants (/ʈ/, /ɖ/), dental stops (/t̪/, /d̪/), and monophthongization of standard English diphthongs (/eɪ/ $\to$ [eː], /oʊ/ $\to$ [oː]).
2. **Pitch / Fundamental Frequency ($F_0$) Statistics ($F_0$ Mean, Std Dev, Range)**:
   - *Rationale*: Prosodic intonation contour is one of the strongest perceptual and acoustic markers of Indian English varieties, characterized by syllable-level pitch excursions and distinctive intonational boundaries.
3. **Speech Rate & Articulation Rate (Syllable Nuclei Estimation)**:
   - *Rationale*: Indian English is predominantly syllable-timed (characterized by a lower normalized Pairwise Variability Index, nPVI), yielding different vowel duration ratios and rhythm compared to stress-timed British or American English.
4. **Pause Duration Ratio**:
   - *Rationale*: Captures phrase-level chunking and pause distribution across utterances.
5. **Spectral Centroid & Spectral Rolloff (85%)**:
   - *Rationale*: Quantifies spectral brightness and energy distribution, reflecting differences in stop consonant aspiration (Indian English typically features unaspirated voiceless stops $[p, t, k]$ vs. aspirated English $[p^h, t^h, k^h]$).
6. **Spectral Flatness**:
   - *Rationale*: Measures tonal versus noise-like spectral characteristics to distinguish vowel harmonics from frication.
7. **Zero Crossing Rate (ZCR)**:
   - *Rationale*: Identifies consonant frication and high-frequency energy distribution (e.g., /v/-/w/ or /s/-/ʃ/ distinctions).
8. **RMS Energy (Mean, Std Dev)**:
   - *Rationale*: Quantifies dynamic range and syllabic energy contours.

### 2. Pretrained Representation Evaluation
- **Wav2Vec2 / XLS-R / HuBERT**: Pretrained self-supervised speech representations offer high-capacity frame-level embeddings for downstream phonetic classifiers. When training on labeled accent corpora, these representations can serve as upstream feature extractors. For the lightweight CPU runtime, the 38-dim acoustic/prosodic feature vector provides deterministic, interpretable, and low-latency extraction.

---

## 🏛️ Model Architecture & Calibration Policy

```mermaid
graph TD
    Audio[Uploaded Audio File] --> Validator[AudioValidatorService Phase 1]
    Validator --> Extractor[AcousticFeatureExtractor (MFCC, F0, Prosody, Spectral)]
    Extractor --> Features[38-dim AcousticFeatures]
    Features --> Classifier{Model Status Check}
    Classifier -->|No Calibrated Dataset| Baseline[DevelopmentBaselineAccentClassifier]
    Classifier -->|Calibrated Dataset Loaded| Trained[TrainedAccentClassifier]
    Baseline --> Output1[status: not_calibrated, confidence: 0.0, accent: unknown]
    Trained --> Output2[status: trained, calibrated probability, predicted label]
```

### Calibration Policy & Development Baseline
- **No Fabricated Predictions**: Because a legitimate human-labeled Indian-English accent dataset is not bundled by default, the active classifier (`DevelopmentBaselineAccentClassifier`) explicitly sets:
  ```json
  "model_status": "not_calibrated",
  "confidence": 0.0,
  "accent": "unknown"
  ```
- **Extensible Label System**: Initially supports `indian_english`, `non_indian_english`, and `unknown`. Regional sub-accents (e.g., Tamil, Telugu, Hindi, Marathi) are intentionally omitted until validated training data is supplied.

---

## 📦 Dataset Requirements & Training Pipeline

The system includes complete infrastructure in `backend/training/accent/`:

### Dataset Structure
```text
dataset/
├── audio/
│   ├── spk001_utt01.wav
│   └── ...
└── metadata.csv
```

**Required `metadata.csv` Fields**:
- `audio_path`: Relative or absolute path to audio recording.
- `accent_label`: Label (`indian_english` or `non_indian_english`).
- `speaker_id`: Unique speaker identifier (mandatory for speaker-independent splitting).
- `region`: Optional region/state.
- `gender_optional`: Optional demographic tag.
- `age_group_optional`: Optional demographic tag.

### Training Modules
1. **`prepare_dataset.py`**:
   - Validates audio file existence and metadata fields.
   - Performs **speaker-independent** train/val/test splitting (groups by `speaker_id` to strictly prevent acoustic identity leakage).
2. **`extract_features.py`**:
   - Extracts 38-dim feature matrices (`X_train.npy`, `y_train.npy`, etc.).
3. **`train.py`**:
   - Standardizes features and trains a regularized classifier.
   - Exports `weights.json` and version metadata `metadata.json`.
4. **`evaluate.py`**:
   - Evaluates test split: Accuracy, Precision, Recall, Macro/Weighted F1, Confusion Matrix, and Expected Calibration Error (ECE) / Brier Score.
5. **`inference.py`**:
   - Standalone CLI for running inference on audio files.

---

## 🔌 API Endpoint

### `POST /api/v1/accent/analyze`

**Request**:
- `file`: Multipart audio file (`.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac`, `.webm`).

**Response Schema (`AccentAnalysisResponse`)**:
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
    "mfcc_mean": [-47.8966, 26.3749, -7.2786, 1.246, -3.024, 2.8434, -4.6995, 0.0068, -0.3121, -1.7105, 0.911, -1.0283, 0.8071],
    "mfcc_std": [8.9675, 4.4082, 3.4266, 3.2517, 1.9429, 1.7395, 2.6851, 1.2682, 1.2396, 1.3335, 1.1176, 1.0194, 1.0165]
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

---

## 🛡️ Limitations & Ethical Considerations
- **No Accent Bias in Scoring**: Accent variation must never be used to penalize language learners or treat non-standard varieties as defective.
- **Data Provenance**: Training will only occur once a verified dataset with diverse Indian regions, age groups, and balanced demographics is validated.
- **Privacy**: Does not collect or mandate sensitive demographic metadata.
