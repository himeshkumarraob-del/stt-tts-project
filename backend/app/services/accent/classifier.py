"""Accent classifier implementations with explicit calibration status."""
import os
import json
import logging
from typing import Dict, Any, List, Tuple, Optional
import numpy as np

from app.schemas.accent import (
    AccentLabel,
    ModelStatus,
    AcousticFeatures,
    AccentMetadata,
)
from app.services.accent.base import BaseAccentClassifier

logger = logging.getLogger(__name__)


class DevelopmentBaselineAccentClassifier(BaseAccentClassifier):
    """
    Development fallback classifier.
    
    CRITICAL POLICY:
    Because no legitimate human-labeled Indian-English accent dataset has been trained yet,
    this classifier explicitly reports `model_status = ModelStatus.NOT_CALIBRATED` and does NOT
    fabricate confident or regional classifications. It analyzes acoustic feature distributions
    and provides descriptive observations.
    """

    def __init__(self, model_name: str = "acoustic_prosody_baseline", model_version: str = "0.1.0"):
        self._model_name = model_name
        self._model_version = model_version
        self._model_type = "heuristic_acoustic_analyzer"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def model_type(self) -> str:
        return self._model_type

    @property
    def is_calibrated(self) -> bool:
        return False

    def classify(
        self,
        features: AcousticFeatures,
        audio_metadata: Dict[str, Any],
    ) -> Tuple[AccentLabel, float, ModelStatus, List[str], AccentMetadata]:
        """Perform descriptive acoustic analysis without claiming calibrated classification."""
        explanations: List[str] = []

        # 1. Pitch / Intonation observations
        if features.pitch_f0_mean_hz > 0:
            explanations.append(
                f"Mean fundamental frequency (F0): {features.pitch_f0_mean_hz:.1f} Hz "
                f"with standard deviation {features.pitch_f0_std_hz:.1f} Hz (range: {features.pitch_f0_range_hz:.1f} Hz)."
            )
            if features.pitch_f0_std_hz > 35.0:
                explanations.append("Utterance exhibits high pitch variability and dynamic pitch excursions.")
            elif features.pitch_f0_std_hz < 15.0:
                explanations.append("Utterance exhibits relatively flat/narrow intonation contours.")
        else:
            explanations.append("Insufficient voiced frames detected to reliably estimate fundamental frequency (F0).")

        # 2. Timing and Prosody observations
        explanations.append(
            f"Estimated articulation rate: {features.articulation_rate:.1f} syllables/sec "
            f"(pause ratio: {features.pause_duration_ratio * 100:.1f}%)."
        )
        if features.pause_duration_ratio > 0.30:
            explanations.append("Significant pause segments observed across the speech sample.")

        # 3. Spectral distribution observations
        explanations.append(
            f"Mean spectral centroid: {features.spectral_centroid_mean:.1f} Hz "
            f"(spectral roll-off: {features.spectral_rolloff_mean:.1f} Hz)."
        )

        # 4. Explicit uncalibrated model note
        explanations.append(
            "Note: Classifier is in development status ('not_calibrated'). "
            "Acoustic features are extracted accurately, but accent classification requires a verified labeled dataset."
        )

        metadata = AccentMetadata(
            model_name=self.model_name,
            model_version=self.model_version,
            model_type=self.model_type,
            training_dataset=None,
            training_date=None,
            duration_seconds=audio_metadata.get("duration_seconds", 0.0),
            sample_rate=audio_metadata.get("sample_rate", 16000),
        )

        # Return UNKNOWN with 0.0 confidence and NOT_CALIBRATED status
        return (
            AccentLabel.UNKNOWN,
            0.0,
            ModelStatus.NOT_CALIBRATED,
            explanations,
            metadata,
        )


class TrainedAccentClassifier(BaseAccentClassifier):
    """
    Trained classifier loaded from legitimate model weights & calibration metadata.
    """

    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self._load_model()

    def _load_model(self):
        meta_path = os.path.join(self.model_dir, "metadata.json")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"Model metadata not found at {meta_path}")

        with open(meta_path, "r", encoding="utf-8") as f:
            self._meta = json.load(f)

        self._model_name = self._meta.get("model_name", "custom_accent_classifier")
        self._model_version = self._meta.get("model_version", "1.0.0")
        self._model_type = self._meta.get("model_type", "linear_svc")
        self._training_dataset = self._meta.get("training_dataset")
        self._training_date = self._meta.get("training_date")
        self._is_calibrated = bool(self._meta.get("is_calibrated", False))
        self._labels = self._meta.get("labels", ["indian_english", "non_indian_english"])
        
        # Load weights/scaler if present
        weights_path = os.path.join(self.model_dir, "weights.json")
        if os.path.exists(weights_path):
            with open(weights_path, "r", encoding="utf-8") as f:
                self._weights = json.load(f)
        else:
            self._weights = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def model_type(self) -> str:
        return self._model_type

    @property
    def is_calibrated(self) -> bool:
        return self._is_calibrated

    def classify(
        self,
        features: AcousticFeatures,
        audio_metadata: Dict[str, Any],
    ) -> Tuple[AccentLabel, float, ModelStatus, List[str], AccentMetadata]:
        """Classify using loaded weights."""
        if not self.is_calibrated or not self._weights:
            dev_clf = DevelopmentBaselineAccentClassifier(self.model_name, self.model_version)
            return dev_clf.classify(features, audio_metadata)

        # Feature vector assembly
        feat_vec = np.array(
            [
                features.pitch_f0_mean_hz,
                features.pitch_f0_std_hz,
                features.pitch_f0_range_hz,
                features.speech_rate_syllables_per_sec,
                features.articulation_rate,
                features.pause_duration_ratio,
                features.spectral_centroid_mean,
                features.spectral_rolloff_mean,
                features.spectral_flatness_mean,
                features.zero_crossing_rate_mean,
                features.energy_rms_mean,
                features.energy_rms_std,
            ] + features.mfcc_mean + features.mfcc_std,
            dtype=np.float64,
        )

        mean = np.array(self._weights.get("mean", np.zeros_like(feat_vec)))
        scale = np.array(self._weights.get("scale", np.ones_like(feat_vec)))
        scale[scale == 0] = 1.0
        norm_feat = (feat_vec - mean) / scale

        w = np.array(self._weights.get("coef", np.zeros_like(feat_vec)))
        b = float(self._weights.get("intercept", 0.0))

        logit = float(np.dot(w, norm_feat) + b)
        prob = 1.0 / (1.0 + np.exp(-logit))

        if prob >= 0.5:
            pred_label = AccentLabel.INDIAN_ENGLISH
            conf = float(prob)
        else:
            pred_label = AccentLabel.NON_INDIAN_ENGLISH
            conf = float(1.0 - prob)

        explanations = [
            f"Predicted {pred_label.value} with calibrated probability {conf:.2f}.",
            f"F0 Mean: {features.pitch_f0_mean_hz:.1f} Hz, Articulation Rate: {features.articulation_rate:.1f} syl/s.",
            f"Model verified against dataset: {self._training_dataset}.",
        ]

        metadata = AccentMetadata(
            model_name=self.model_name,
            model_version=self.model_version,
            model_type=self.model_type,
            training_dataset=self._training_dataset,
            training_date=self._training_date,
            duration_seconds=audio_metadata.get("duration_seconds", 0.0),
            sample_rate=audio_metadata.get("sample_rate", 16000),
        )

        return pred_label, round(conf, 4), ModelStatus.TRAINED, explanations, metadata
