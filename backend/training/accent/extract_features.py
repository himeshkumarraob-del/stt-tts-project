"""Acoustic feature extraction script for training datasets."""
import os
import json
import logging
import argparse
from typing import List, Dict, Any, Tuple
import numpy as np

from app.services.accent.features import AcousticFeatureExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def extract_feature_vector(extractor: AcousticFeatureExtractor, audio_path: str) -> np.ndarray:
    """Extract a flattened numerical feature vector from an audio file."""
    features, _ = extractor.extract_from_file(audio_path)
    vec = [
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
    ] + features.mfcc_mean + features.mfcc_std
    return np.array(vec, dtype=np.float64)


def process_manifest(
    manifest_path: str,
    output_dir: str,
    split_name: str,
) -> Tuple[np.ndarray, np.ndarray]:
    """Process all audio files in a manifest and save numpy arrays."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        records: List[Dict[str, str]] = json.load(f)

    extractor = AcousticFeatureExtractor()
    X_list = []
    y_list = []
    valid_records = []

    for idx, r in enumerate(records, start=1):
        audio_path = r["audio_path"]
        label_str = r["accent_label"]
        label = 1 if label_str == "indian_english" else 0

        try:
            feat_vec = extract_feature_vector(extractor, audio_path)
            X_list.append(feat_vec)
            y_list.append(label)
            valid_records.append(r)
        except Exception as e:
            logger.warning(f"Failed to extract features from {audio_path}: {e}")

        if idx % 100 == 0 or idx == len(records):
            logger.info(f"Processed {idx}/{len(records)} files for {split_name} split.")

    X = np.array(X_list, dtype=np.float64)
    y = np.array(y_list, dtype=np.int64)

    os.makedirs(output_dir, exist_ok=True)
    np.save(os.path.join(output_dir, f"X_{split_name}.npy"), X)
    np.save(os.path.join(output_dir, f"y_{split_name}.npy"), y)
    with open(os.path.join(output_dir, f"{split_name}_records.json"), "w", encoding="utf-8") as f:
        json.dump(valid_records, f, indent=2)

    logger.info(f"Saved {split_name} features: X shape {X.shape}, y shape {y.shape} to {output_dir}")
    return X, y


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract acoustic features for manifest splits.")
    parser.add_argument("--splits-dir", type=str, default="data/splits", help="Directory with split manifests")
    parser.add_argument("--output-dir", type=str, default="data/features", help="Output directory for npy arrays")
    args = parser.parse_args()

    for split in ["train", "val", "test"]:
        manifest_file = os.path.join(args.splits_dir, f"{split}_manifest.json")
        if os.path.exists(manifest_file):
            process_manifest(manifest_file, args.output_dir, split)
