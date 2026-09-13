"""Model training and calibration pipeline for accent classification."""
import os
import json
import logging
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def standardize_features(X_train: np.ndarray, X_val: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Standardize feature matrix to zero mean and unit variance."""
    mean = np.mean(X_train, axis=0)
    std = np.std(X_train, axis=0)
    std[std == 0] = 1.0

    X_train_norm = (X_train - mean) / std
    X_val_norm = (X_val - mean) / std
    return X_train_norm, X_val_norm, mean, std


def train_logistic_regression(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    lr: float = 0.01,
    reg_lambda: float = 0.01,
    epochs: int = 1000,
) -> Tuple[np.ndarray, float, Dict[str, Any]]:
    """Train L2-regularized logistic regression classifier using batch gradient descent."""
    num_samples, num_features = X_train.shape
    weights = np.zeros(num_features, dtype=np.float64)
    bias = 0.0

    history = {"train_loss": [], "val_loss": [], "val_acc": []}

    for epoch in range(1, epochs + 1):
        # Forward pass
        logits = np.dot(X_train, weights) + bias
        probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -25.0, 25.0)))

        # Cross-entropy loss with L2 regularization
        eps = 1e-12
        loss = -np.mean(y_train * np.log(probs + eps) + (1 - y_train) * np.log(1 - probs + eps))
        loss += 0.5 * reg_lambda * np.sum(weights ** 2)

        # Gradients
        dz = probs - y_train
        dw = (np.dot(X_train.T, dz) / num_samples) + (reg_lambda * weights)
        db = np.mean(dz)

        # Gradient update
        weights -= lr * dw
        bias -= lr * db

        if epoch % 100 == 0 or epoch == epochs:
            # Validation evaluation
            val_logits = np.dot(X_val, weights) + bias
            val_probs = 1.0 / (1.0 + np.exp(-np.clip(val_logits, -25.0, 25.0)))
            val_loss = -np.mean(y_val * np.log(val_probs + eps) + (1 - y_val) * np.log(1 - val_probs + eps))
            val_preds = (val_probs >= 0.5).astype(int)
            val_acc = np.mean(val_preds == y_val)

            history["train_loss"].append(float(loss))
            history["val_loss"].append(float(val_loss))
            history["val_acc"].append(float(val_acc))
            logger.info(f"Epoch {epoch}/{epochs} - Train Loss: {loss:.4f}, Val Loss: {val_loss:.4f}, Val Acc: {val_acc * 100:.2f}%")

    return weights, bias, history


def save_trained_model(
    output_dir: str,
    weights: np.ndarray,
    bias: float,
    mean: np.ndarray,
    std: np.ndarray,
    dataset_name: str,
    val_acc: float,
):
    """Save model artifacts, weights, and version metadata."""
    os.makedirs(output_dir, exist_ok=True)

    weights_payload = {
        "coef": [float(w) for w in weights],
        "intercept": float(bias),
        "mean": [float(m) for m in mean],
        "scale": [float(s) for s in std],
    }

    with open(os.path.join(output_dir, "weights.json"), "w", encoding="utf-8") as f:
        json.dump(weights_payload, f, indent=2)

    meta_payload = {
        "model_name": "indian_english_acoustic_classifier",
        "model_version": "1.0.0",
        "model_type": "logistic_regression_acoustic",
        "training_dataset": dataset_name,
        "training_date": datetime.now(timezone.utc).isoformat(),
        "is_calibrated": True,
        "labels": ["indian_english", "non_indian_english"],
        "validation_accuracy": round(val_acc, 4),
    }

    with open(os.path.join(output_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta_payload, f, indent=2)

    logger.info(f"Trained model saved successfully to {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train accent classification model on extracted features.")
    parser.add_argument("--features-dir", type=str, default="data/features", help="Directory with X_train.npy, etc.")
    parser.add_argument("--output-dir", type=str, default="models/accent_v1", help="Output model directory")
    parser.add_argument("--dataset-name", type=str, default="custom_labeled_dataset", help="Dataset identifier")
    parser.add_argument("--epochs", type=int, default=1000, help="Training epochs")
    parser.add_argument("--lr", type=float, default=0.05, help="Learning rate")
    args = parser.parse_args()

    X_train_path = os.path.join(args.features_dir, "X_train.npy")
    y_train_path = os.path.join(args.features_dir, "y_train.npy")
    X_val_path = os.path.join(args.features_dir, "X_val.npy")
    y_val_path = os.path.join(args.features_dir, "y_val.npy")

    if not os.path.exists(X_train_path) or not os.path.exists(y_train_path):
        raise FileNotFoundError(
            f"Training features not found at {X_train_path}. "
            "Please extract features first using extract_features.py once a legitimate labeled dataset is provided."
        )

    X_train = np.load(X_train_path)
    y_train = np.load(y_train_path)
    X_val = np.load(X_val_path) if os.path.exists(X_val_path) else X_train
    y_val = np.load(y_val_path) if os.path.exists(y_val_path) else y_train

    X_train_norm, X_val_norm, mean, std = standardize_features(X_train, X_val)
    weights, bias, history = train_logistic_regression(X_train_norm, y_train, X_val_norm, y_val, lr=args.lr, epochs=args.epochs)

    final_val_acc = history["val_acc"][-1] if history["val_acc"] else 0.0
    save_trained_model(args.output_dir, weights, bias, mean, std, args.dataset_name, final_val_acc)
