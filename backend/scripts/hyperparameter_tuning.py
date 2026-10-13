"""
hyperparameter_tuning.py
------------------------
KMeans hyperparameter search for the Spotify tracks dataset.

Usage
-----
    python backend/scripts/hyperparameter_tuning.py           # uses defaults
    python backend/scripts/hyperparameter_tuning.py --data path/to/data.csv
    python backend/scripts/hyperparameter_tuning.py --data path/to/data.csv \\
        --output-params backend/models/best_kmeans_params.json \\
        --output-plot   search_results.png

The script saves the best parameters as JSON and (optionally) a silhouette
vs. k plot.  Run *this* script before model_training.py.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DATA_PATH   = _ROOT / "data" / "spotify-tracks-dataset.csv"
_DEFAULT_PARAMS_PATH = _ROOT / "models" / "best_kmeans_params.json"

AUDIO_FEATURES = [
    "popularity", "duration_ms", "explicit", "danceability", "energy",
    "key", "loudness", "mode", "speechiness", "acousticness",
    "instrumentalness", "liveness", "valence", "tempo", "time_signature",
]

PARAM_GRID = {
    "n_clusters": list(range(2, 13)),
    "init":       ["k-means++", "random"],
    "n_init":     [10, 20],
    "max_iter":   [300],
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_features(data_path: Path) -> np.ndarray:
    """Load audio features from *data_path* and return a float32 array."""
    log.info("Loading data from: %s", data_path)
    df = pd.read_csv(data_path, usecols=AUDIO_FEATURES).dropna()
    if len(df) < 10:
        raise ValueError(
            f"Need at least 10 complete rows; found {len(df)} in {data_path}."
        )
    log.info("Loaded %d tracks with %d features.", len(df), len(AUDIO_FEATURES))
    return df.to_numpy(dtype=np.float32)


# ---------------------------------------------------------------------------
# Hyperparameter search
# ---------------------------------------------------------------------------
def run_hyperparameter_search(
    X: np.ndarray,
    param_grid: dict | None = None,
    fit_size: int = 15_000,
    valid_size: int = 2_500,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Grid-search KMeans hyperparameters using a held-out validation split.

    Parameters
    ----------
    X          : Feature matrix (already loaded, not yet scaled).
    param_grid : Dict with keys ``n_clusters``, ``init``, ``n_init``,
                 ``max_iter``.  Defaults to ``PARAM_GRID``.
    fit_size   : Max samples used for fitting each candidate.
    valid_size : Max samples used for validation silhouette scoring.
    random_state : Seed for reproducibility.

    Returns
    -------
    pd.DataFrame sorted by validation silhouette (best first).
    """
    if param_grid is None:
        param_grid = PARAM_GRID

    # Split into selection-train and validation
    X_sel_train, X_val = train_test_split(
        X, test_size=0.2, random_state=random_state, shuffle=True
    )
    rng = np.random.default_rng(random_state)

    n_fit   = min(fit_size,   len(X_sel_train))
    n_valid = min(valid_size, len(X_val))
    if n_fit < 2 or n_valid < 2:
        raise ValueError("Not enough rows for fitting and validation samples.")

    X_fit_raw   = X_sel_train[rng.choice(len(X_sel_train), n_fit,   replace=False)]
    X_valid_raw = X_val       [rng.choice(len(X_val),       n_valid, replace=False)]

    scaler  = StandardScaler()
    X_fit   = scaler.fit_transform(X_fit_raw).astype(np.float32, copy=False)
    X_valid = scaler.transform(X_valid_raw).astype(np.float32, copy=False)

    keys   = ["n_clusters", "init", "n_init", "max_iter"]
    combos = list(product(*[param_grid[k] for k in keys]))
    log.info("Searching %d combinations …", len(combos))

    results: list[dict] = []
    for combo in combos:
        params = dict(zip(keys, combo))
        model  = KMeans(**params, random_state=random_state)
        model.fit(X_fit)
        labels = model.predict(X_valid)
        n_unique = np.unique(labels).size
        if 1 < n_unique < len(labels):
            score = silhouette_score(X_valid, labels)
            results.append({**params, "silhouette": score, "inertia": model.inertia_})

    if not results:
        raise RuntimeError(
            "No candidate produced valid validation labels for silhouette scoring."
        )

    df_results = (
        pd.DataFrame(results)
        .sort_values("silhouette", ascending=False)
        .reset_index(drop=True)
    )
    log.info(
        "Best → k=%d  init=%s  n_init=%d  silhouette=%.4f",
        df_results.iloc[0]["n_clusters"],
        df_results.iloc[0]["init"],
        df_results.iloc[0]["n_init"],
        df_results.iloc[0]["silhouette"],
    )
    return df_results


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------
def save_best_params(results: pd.DataFrame, output_path: Path) -> dict:
    """Extract the top row from *results* and write it to *output_path* as JSON."""
    best = results.iloc[0]
    best_params = {
        "n_clusters":   int(best["n_clusters"]),
        "init":         str(best["init"]),
        "n_init":       int(best["n_init"]),
        "max_iter":     int(best["max_iter"]),
        "random_state": 42,
    }
    output_path.write_text(json.dumps(best_params, indent=2), encoding="utf-8")
    log.info("Saved best parameters to: %s", output_path)
    return best_params


def plot_search_results(results: pd.DataFrame, output_path: Path | None = None) -> None:
    """Plot validation silhouette vs k (best init per k)."""
    best_by_k = (
        results.groupby("n_clusters", as_index=False)["silhouette"].max()
    )
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(best_by_k["n_clusters"], best_by_k["silhouette"], marker="o",
            color="#2ecc71", linewidth=2, markersize=7)
    ax.set_xlabel("Number of clusters (k)")
    ax.set_ylabel("Validation silhouette score")
    ax.set_title("KMeans hyperparameter search — Spotify tracks")
    ax.set_xticks(best_by_k["n_clusters"])
    ax.grid(alpha=0.3)
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=120)
        log.info("Saved plot to: %s", output_path)
    else:
        plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="KMeans hyperparameter search for the Spotify dataset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--data", type=Path, default=_DEFAULT_DATA_PATH,
        help="Path to the raw Spotify CSV file.",
    )
    p.add_argument(
        "--output-params", type=Path, default=_DEFAULT_PARAMS_PATH,
        help="Where to write the best parameters JSON.",
    )
    p.add_argument(
        "--output-plot", type=Path, default=None,
        help="Optional path to save the silhouette vs k plot (e.g. search.png). "
             "If omitted the plot is shown interactively.",
    )
    p.add_argument(
        "--fit-size", type=int, default=15_000,
        help="Max samples for fitting each candidate.",
    )
    p.add_argument(
        "--valid-size", type=int, default=2_500,
        help="Max samples for validation silhouette scoring.",
    )
    p.add_argument(
        "--top-n", type=int, default=10,
        help="Number of top candidates to print.",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    X       = load_features(args.data)
    results = run_hyperparameter_search(
        X,
        fit_size=args.fit_size,
        valid_size=args.valid_size,
    )
    print("\nTop candidates:")
    print(results.head(args.top_n).to_string(index=False))

    best_params = save_best_params(results, args.output_params)
    print("\nBest parameters saved:")
    for k, v in best_params.items():
        print(f"  {k}: {v}")

    plot_search_results(results, args.output_plot)


if __name__ == "__main__":
    main()
