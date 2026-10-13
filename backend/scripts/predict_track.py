"""Collect Spotify audio features and predict a track's KMeans cluster."""

from __future__ import annotations

import argparse
import math
import pickle
from pathlib import Path
from typing import Any

import numpy as np


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_MODEL_PATH = _ROOT / "models" / "best_kmeans_model.pkl"
_BINARY_FEATURES = {"explicit", "mode"}


def load_model_artifact(model_path: Path) -> dict[str, Any]:
    """Load and validate the model, scaler, and feature names saved by training."""
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Model artifact not found: {model_path}. "
            "Train it first with model_training.py train-kmeans."
        )

    with model_path.open("rb") as model_file:
        artifact = pickle.load(model_file)

    if not isinstance(artifact, dict):
        raise ValueError("Model artifact must contain a dictionary.")

    missing = {"model", "scaler", "features"} - artifact.keys()
    if missing:
        raise ValueError(
            "Model artifact is missing required entries: "
            + ", ".join(sorted(missing))
        )

    features = artifact["features"]
    if (
        not isinstance(features, list)
        or not features
        or not all(isinstance(name, str) for name in features)
        or len(set(features)) != len(features)
    ):
        raise ValueError("Model artifact contains an invalid feature list.")

    model = artifact["model"]
    scaler = artifact["scaler"]
    expected_count = getattr(model, "n_features_in_", None)
    scaler_feature_count = getattr(scaler, "n_features_in_", None)
    if expected_count != len(features) or scaler_feature_count != len(features):
        raise ValueError(
            "Model, scaler, and feature list do not agree on the number of features."
        )
    if not callable(getattr(model, "predict", None)) or not callable(
        getattr(scaler, "transform", None)
    ):
        raise ValueError("Model artifact does not support prediction.")

    return artifact


def predict_track(
    values: dict[str, float], artifact: dict[str, Any]
) -> tuple[int, float]:
    """Return the predicted cluster label and its scaled distance to the centroid."""
    features = artifact["features"]
    missing = [name for name in features if name not in values]
    if missing:
        raise ValueError("Missing feature values: " + ", ".join(missing))

    row = np.asarray([[values[name] for name in features]], dtype=np.float64)
    if not np.isfinite(row).all():
        raise ValueError("Feature values must be finite numbers.")

    model = artifact["model"]
    scaled_row = artifact["scaler"].transform(row).astype(
        model.cluster_centers_.dtype, copy=False
    )
    cluster = int(model.predict(scaled_row)[0])

    if not callable(getattr(model, "transform", None)):
        raise ValueError("The saved model cannot calculate distance to its clusters.")
    distances = model.transform(scaled_row)[0]
    return cluster, float(distances[cluster])


def collect_input(features: list[str]) -> dict[str, float]:
    """Prompt until each required feature has a valid numeric value."""
    values: dict[str, float] = {}
    print("Enter the Spotify audio-feature values for one track.")
    print("Use 0 or 1 for 'explicit' and 'mode'. Press Ctrl+C to cancel.\n")

    for feature in features:
        while True:
            raw_value = input(f"{feature}: ").strip()
            try:
                value = float(raw_value)
            except ValueError:
                print("  Please enter a number.")
                continue

            if not math.isfinite(value):
                print("  Please enter a finite number.")
                continue
            if feature in _BINARY_FEATURES and value not in (0, 1):
                print("  Please enter 0 or 1.")
                continue

            values[feature] = value
            break

    return values


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Predict a Spotify track's cluster from its audio features."
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=_DEFAULT_MODEL_PATH,
        help="Path to the trained model artifact.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    artifact = load_model_artifact(args.model)
    values = collect_input(artifact["features"])
    cluster, distance = predict_track(values, artifact)

    print("\n=== Model Result ===")
    print(f"Assigned cluster: {cluster}")
    print(f"Distance to cluster center (scaled feature space): {distance:.4f}")
    print("The cluster number is a model label; it does not represent a ranking.")


if __name__ == "__main__":
    main()
