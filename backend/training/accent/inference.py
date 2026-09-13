"""Standalone CLI inference utility for accent analysis."""
import os
import sys
import json
import logging
import argparse

from app.services.accent.features import AcousticFeatureExtractor
from app.services.accent.classifier import DevelopmentBaselineAccentClassifier, TrainedAccentClassifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_inference(audio_path: str, model_dir: str = None) -> dict:
    """Run accent analysis inference on an audio file."""
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    extractor = AcousticFeatureExtractor()
    features, meta = extractor.extract_from_file(audio_path)

    if model_dir and os.path.exists(model_dir):
        logger.info(f"Loading trained classifier from {model_dir}")
        classifier = TrainedAccentClassifier(model_dir)
    else:
        logger.info("Using development baseline classifier (uncalibrated)")
        classifier = DevelopmentBaselineAccentClassifier()

    accent, conf, status, explanations, model_meta = classifier.classify(features, meta)

    result = {
        "audio_path": audio_path,
        "accent": accent.value,
        "confidence": conf,
        "model_status": status.value,
        "features": features.model_dump(),
        "explanation": explanations,
        "metadata": model_meta.model_dump(),
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run accent inference on an audio file.")
    parser.add_argument("--audio", type=str, required=True, help="Path to audio file")
    parser.add_argument("--model-dir", type=str, default=None, help="Optional path to trained model directory")
    args = parser.parse_args()

    res = run_inference(args.audio, args.model_dir)
    print(json.dumps(res, indent=2))
