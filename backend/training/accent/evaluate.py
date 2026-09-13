"""Evaluation and calibration metrics for accent classifiers."""
import os
import json
import logging
import argparse
from typing import Dict, Any, List
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def compute_classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, probs: np.ndarray) -> Dict[str, Any]:
    """Compute confusion matrix, precision, recall, F1, and calibration error."""
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))

    accuracy = float((tp + tn) / max(1, len(y_true)))
    precision = float(tp / max(1, tp + fp))
    recall = float(tp / max(1, tp + fn))
    f1 = float(2 * precision * recall / max(1e-9, precision + recall))

    # Brier Score (mean squared difference between predicted probabilities and binary outcomes)
    brier_score = float(np.mean((probs - y_true) ** 2))

    # Expected Calibration Error (ECE) with 10 bins
    num_bins = 10
    bin_boundaries = np.linspace(0, 1, num_bins + 1)
    ece = 0.0
    for i in range(num_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        in_bin = (probs >= bin_lower) & (probs < bin_upper if i < num_bins - 1 else probs <= bin_upper)
        prop_in_bin = np.mean(in_bin)
        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(y_true[in_bin])
            avg_confidence_in_bin = np.mean(probs[in_bin])
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "confusion_matrix": {
            "true_positive": tp,
            "false_positive": fp,
            "true_negative": tn,
            "false_negative": fn,
        },
        "brier_score": round(brier_score, 4),
        "expected_calibration_error_ece": round(float(ece), 4),
        "total_test_samples": len(y_true),
    }


def evaluate_model(model_dir: str, features_dir: str, output_report: str) -> Dict[str, Any]:
    """Load model and test features, perform inference, and generate metrics report."""
    weights_path = os.path.join(model_dir, "weights.json")
    meta_path = os.path.join(model_dir, "metadata.json")

    if not os.path.exists(weights_path) or not os.path.exists(meta_path):
        raise FileNotFoundError(f"Model files not found in {model_dir}")

    with open(weights_path, "r", encoding="utf-8") as f:
        weights_data = json.load(f)

    with open(meta_path, "r", encoding="utf-8") as f:
        meta_data = json.load(f)

    X_test_path = os.path.join(features_dir, "X_test.npy")
    y_test_path = os.path.join(features_dir, "y_test.npy")

    if not os.path.exists(X_test_path) or not os.path.exists(y_test_path):
        raise FileNotFoundError(f"Test features not found in {features_dir}")

    X_test = np.load(X_test_path)
    y_test = np.load(y_test_path)

    mean = np.array(weights_data["mean"])
    std = np.array(weights_data["scale"])
    w = np.array(weights_data["coef"])
    b = float(weights_data["intercept"])

    X_test_norm = (X_test - mean) / std
    logits = np.dot(X_test_norm, w) + b
    probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -25.0, 25.0)))
    y_pred = (probs >= 0.5).astype(int)

    metrics = compute_classification_metrics(y_test, y_pred, probs)
    metrics["model_name"] = meta_data.get("model_name")
    metrics["model_version"] = meta_data.get("model_version")
    metrics["training_dataset"] = meta_data.get("training_dataset")

    os.makedirs(os.path.dirname(output_report) or ".", exist_ok=True)
    with open(output_report, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    logger.info(f"Evaluation report generated:\n{json.dumps(metrics, indent=2)}")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate trained accent classifier.")
    parser.add_argument("--model-dir", type=str, default="models/accent_v1", help="Model directory")
    parser.add_argument("--features-dir", type=str, default="data/features", help="Directory with X_test.npy")
    parser.add_argument("--output-report", type=str, default="evaluation_report.json", help="Output path for metrics report")
    args = parser.parse_args()

    evaluate_model(args.model_dir, args.features_dir, args.output_report)
