"""Dataset preparation and speaker-independent split validation for accent training."""
import os
import csv
import json
import logging
import argparse
from typing import Dict, List, Set, Any
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"audio_path", "accent_label", "speaker_id"}
OPTIONAL_COLUMNS = {"region", "gender_optional", "age_group_optional"}
SUPPORTED_ACCENTS = {"indian_english", "non_indian_english"}


def validate_metadata(csv_path: str, audio_root: str) -> List[Dict[str, str]]:
    """Validate CSV header, file presence, and label validity."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Metadata CSV not found: {csv_path}")

    records = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not REQUIRED_COLUMNS.issubset(set(reader.fieldnames or [])):
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            raise ValueError(f"Metadata CSV is missing required columns: {missing}")

        for row_idx, row in enumerate(reader, start=1):
            audio_path = row["audio_path"]
            # Resolve relative to audio_root if relative
            full_audio_path = audio_path if os.path.isabs(audio_path) else os.path.join(audio_root, audio_path)
            if not os.path.exists(full_audio_path):
                logger.warning(f"Row {row_idx}: Audio file not found at '{full_audio_path}', skipping.")
                continue

            label = row["accent_label"].strip().lower()
            if label not in SUPPORTED_ACCENTS:
                logger.warning(f"Row {row_idx}: Unsupported accent label '{label}', skipping.")
                continue

            speaker_id = row["speaker_id"].strip()
            if not speaker_id:
                logger.warning(f"Row {row_idx}: Empty speaker_id, skipping to prevent leakage.")
                continue

            records.append({
                "audio_path": full_audio_path,
                "accent_label": label,
                "speaker_id": speaker_id,
                "region": row.get("region", "unknown"),
            })

    logger.info(f"Successfully validated {len(records)} audio samples across {len(set(r['speaker_id'] for r in records))} distinct speakers.")
    return records


def speaker_independent_split(
    records: List[Dict[str, str]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> Dict[str, List[Dict[str, str]]]:
    """
    Perform speaker-independent dataset splitting.
    Guarantees that no speaker appears in more than one split to prevent acoustic identity leakage.
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-4, "Split ratios must sum to 1.0"
    
    np.random.seed(seed)
    # Group records by speaker
    speaker_map: Dict[str, List[Dict[str, str]]] = {}
    speaker_labels: Dict[str, str] = {}
    for r in records:
        spk = r["speaker_id"]
        speaker_map.setdefault(spk, []).append(r)
        speaker_labels[spk] = r["accent_label"]

    speakers = list(speaker_map.keys())
    np.random.shuffle(speakers)

    # Stratify speakers by dominant accent label
    indian_spks = [s for s in speakers if speaker_labels[s] == "indian_english"]
    non_indian_spks = [s for s in speakers if speaker_labels[s] == "non_indian_english"]

    def split_list(lst: List[str]):
        n = len(lst)
        n_train = int(round(n * train_ratio))
        n_val = int(round(n * val_ratio))
        return lst[:n_train], lst[n_train : n_train + n_val], lst[n_train + n_val :]

    ind_train, ind_val, ind_test = split_list(indian_spks)
    non_train, non_val, non_test = split_list(non_indian_spks)

    train_spks = set(ind_train + non_train)
    val_spks = set(ind_val + non_val)
    test_spks = set(ind_test + non_test)

    # Double check zero speaker leakage
    assert len(train_spks.intersection(val_spks)) == 0, "Speaker leakage detected between Train and Val!"
    assert len(train_spks.intersection(test_spks)) == 0, "Speaker leakage detected between Train and Test!"
    assert len(val_spks.intersection(test_spks)) == 0, "Speaker leakage detected between Val and Test!"

    train_records = [r for s in train_spks for r in speaker_map[s]]
    val_records = [r for s in val_spks for r in speaker_map[s]]
    test_records = [r for s in test_spks for r in speaker_map[s]]

    logger.info(
        f"Split results: "
        f"Train={len(train_records)} samples ({len(train_spks)} spks), "
        f"Val={len(val_records)} samples ({len(val_spks)} spks), "
        f"Test={len(test_records)} samples ({len(test_spks)} spks)"
    )

    return {
        "train": train_records,
        "val": val_records,
        "test": test_records,
    }


def save_splits(splits: Dict[str, List[Dict[str, str]]], output_dir: str):
    """Save split manifests to JSON/CSV files."""
    os.makedirs(output_dir, exist_ok=True)
    for split_name, data in splits.items():
        out_path = os.path.join(output_dir, f"{split_name}_manifest.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {split_name} split manifest ({len(data)} items) to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare and validate speaker-independent dataset splits.")
    parser.add_argument("--csv", type=str, required=True, help="Path to metadata.csv")
    parser.add_argument("--audio-root", type=str, default=".", help="Root directory for relative audio paths")
    parser.add_argument("--output-dir", type=str, default="data/splits", help="Output directory for manifests")
    args = parser.parse_args()

    records = validate_metadata(args.csv, args.audio_root)
    splits = speaker_independent_split(records)
    save_splits(splits, args.output_dir)
