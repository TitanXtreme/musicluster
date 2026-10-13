"""
model_training.py
-----------------
Two tools in one module:

1.  ClusteringPipeline  — trains PCA + multiple clustering algorithms on any
    feature matrix accepted as a dict of sklearn model instances.

2.  train_kmeans         — loads parameters saved by hyperparameter_tuning.py,
    trains a final KMeans model on the full training split, evaluates it on a
    held-out test set, and persists the artefact as a pickle.

Usage
-----
    # Full clustering pipeline
    python backend/scripts/model_training.py cluster \\
        --data backend/data/spotify-tracks-dataset.csv

    # Train the best KMeans found during hyperparameter search
    python backend/scripts/model_training.py train-kmeans \\
        --data   backend/data/spotify-tracks-dataset.csv \\
        --params backend/models/best_kmeans_params.json \\
        --output backend/models/best_kmeans_model.pkl
"""

from __future__ import annotations

import argparse
import json
import logging
import pickle
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, silhouette_samples
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from scipy.cluster.hierarchy import dendrogram, linkage

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
# Constants
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent

AUDIO_FEATURES = [
    "popularity", "duration_ms", "explicit", "danceability", "energy",
    "key", "loudness", "mode", "speechiness", "acousticness",
    "instrumentalness", "liveness", "valence", "tempo", "time_signature",
]


# ═══════════════════════════════════════════════════════════════════════════
#  ClusteringPipeline
# ═══════════════════════════════════════════════════════════════════════════
class ClusteringPipeline:
    """
    Unified training & evaluation pipeline for unsupervised clustering models.

    Pass a dict of sklearn model instances.  Any ``PCA`` instance in the dict
    is used as the dimensionality-reduction step applied before clustering;
    all other models are treated as clustering algorithms.

    Parameters
    ----------
    models : dict[str, sklearn estimator]
        Example::

            {
                "PCA":          PCA(n_components=0.90, random_state=42),
                "KMeans":       KMeans(n_clusters=5, random_state=42),
                "Hierarchical": AgglomerativeClustering(n_clusters=5),
                "DBSCAN":       DBSCAN(eps=1.5, min_samples=50),
            }

    sample_size : int
        Maximum number of points used for expensive metrics (silhouette).
    random_state : int
        Seed for reproducible subsampling.
    """

    def __init__(
        self,
        models: dict,
        sample_size: int = 10_000,
        random_state: int = 42,
    ) -> None:
        self.random_state = random_state
        self.sample_size  = sample_size
        self.scaler       = StandardScaler()

        # Separate PCA from clustering models
        self.pca: PCA = None  # type: ignore[assignment]
        self.clustering_models: dict = {}
        for name, model in models.items():
            if isinstance(model, PCA):
                self.pca = model
            else:
                self.clustering_models[name] = model

        if self.pca is None:
            self.pca = PCA(n_components=0.90, random_state=random_state)

        # Outputs populated by fit()
        self.X_original_:    np.ndarray = None  # type: ignore[assignment]
        self.X_scaled_:      np.ndarray = None  # type: ignore[assignment]
        self.X_pca_:         np.ndarray = None  # type: ignore[assignment]
        self.feature_names_: list[str]  = []
        self.labels_:        dict[str, np.ndarray] = {}
        self.metrics_:       pd.DataFrame | None   = None
        self.profiles_:      dict[str, pd.DataFrame] = {}

    # ── fit ─────────────────────────────────────────────────────────────────
    def fit(self, X: np.ndarray, feature_names: list[str] | None = None) -> "ClusteringPipeline":
        """Scale → PCA → fit all clustering models."""
        self.X_original_    = X.copy()
        self.feature_names_ = feature_names or [f"f{i}" for i in range(X.shape[1])]

        self.X_scaled_ = self.scaler.fit_transform(X)
        self.X_pca_    = self.pca.fit_transform(self.X_scaled_)

        log.info(
            "[PCA]  %dD → %dD  |  variance retained: %.3f%%",
            X.shape[1],
            self.X_pca_.shape[1],
            self.pca.explained_variance_ratio_.sum() * 100,
        )

        for name, model in self.clustering_models.items():
            log.info("[Fit]  %s …", name)
            model.fit(self.X_pca_)
            self.labels_[name] = (
                model.labels_ if hasattr(model, "labels_")
                else model.predict(self.X_pca_)
            )
            n_cl    = len(set(self.labels_[name]) - {-1})
            n_noise = int((self.labels_[name] == -1).sum())
            log.info("       → %d clusters  |  %d noise points", n_cl, n_noise)

        return self

    # ── evaluate ────────────────────────────────────────────────────────────
    def evaluate(self) -> pd.DataFrame:
        """Compute silhouette score, inertia, cluster count and noise count."""
        np.random.seed(self.random_state)
        rows: list[dict] = []

        for name, labels in self.labels_.items():
            model   = self.clustering_models[name]
            mask    = labels != -1
            n_cl    = len(set(labels[mask]))
            n_noise = int((~mask).sum())

            sil: float | None = None
            if n_cl > 1 and mask.sum() > n_cl:
                Xv, lv = self.X_pca_[mask], labels[mask]
                if len(Xv) > self.sample_size:
                    idx = np.random.choice(len(Xv), self.sample_size, replace=False)
                    Xv, lv = Xv[idx], lv[idx]
                sil = silhouette_score(Xv, lv)

            inertia = getattr(model, "inertia_", None)
            rows.append({
                "Model":              name,
                "Clusters":           n_cl,
                "Noise Points":       n_noise,
                "Silhouette Score ↑": round(sil, 4) if sil is not None else "—",
                "Inertia ↓":          f"{inertia:,.0f}" if inertia else "—",
            })

        self.metrics_ = pd.DataFrame(rows).set_index("Model")
        return self.metrics_

    # ── profile ─────────────────────────────────────────────────────────────
    def profile(self) -> dict[str, pd.DataFrame]:
        """Return per-cluster mean of z-scored features for each model."""
        for name, labels in self.labels_.items():
            tmp = pd.DataFrame(self.X_scaled_, columns=self.feature_names_)
            tmp["_cluster"] = labels
            valid = tmp[tmp["_cluster"] != -1]
            self.profiles_[name] = (
                valid.groupby("_cluster")[self.feature_names_].mean()
            )
        return self.profiles_

    # ── plots ────────────────────────────────────────────────────────────────
    def plot_silhouette(self, model_name: str) -> None:
        """Silhouette coefficient plot for a single model."""
        labels = self.labels_[model_name]
        mask   = labels != -1
        Xv, lv = self.X_pca_[mask], labels[mask]
        np.random.seed(self.random_state)
        if len(Xv) > self.sample_size:
            idx = np.random.choice(len(Xv), self.sample_size, replace=False)
            Xv, lv = Xv[idx], lv[idx]

        sil_vals = silhouette_samples(Xv, lv)
        avg_sil  = sil_vals.mean()
        colors   = sns.color_palette("tab10", len(set(lv)))

        fig, ax = plt.subplots(figsize=(10, 6))
        y_lower = 10
        for i, c in enumerate(sorted(set(lv))):
            cv   = np.sort(sil_vals[lv == c])
            y_up = y_lower + len(cv)
            ax.fill_betweenx(np.arange(y_lower, y_up), 0, cv,
                             color=colors[i], alpha=0.85, label=f"Cluster {c}")
            y_lower = y_up + 10

        ax.axvline(avg_sil, linestyle="--", color="red", linewidth=1.5,
                   label=f"Avg = {avg_sil:.4f}")
        ax.set_xlabel("Silhouette Coefficient")
        ax.set_title(f"Silhouette Plot — {model_name}", fontsize=13, fontweight="bold")
        ax.legend(fontsize=8, loc="upper right")
        plt.tight_layout()
        plt.show()

    def plot_pca_scatter(self) -> None:
        """2D PCA scatter coloured by cluster assignment for every model."""
        n    = len(self.clustering_models)
        fig, axes = plt.subplots(1, n, figsize=(7 * n, 6))
        if n == 1:
            axes = [axes]

        np.random.seed(self.random_state)
        idx = np.random.choice(len(self.X_pca_),
                               min(20_000, len(self.X_pca_)), replace=False)

        for ax, (name, labels) in zip(axes, self.labels_.items()):
            sc = ax.scatter(self.X_pca_[idx, 0], self.X_pca_[idx, 1],
                            c=labels[idx], cmap="tab10", s=3, alpha=0.4)
            plt.colorbar(sc, ax=ax, label="Cluster")
            ax.set_title(f"{name}  (PC1 vs PC2)", fontweight="bold")
            ax.set_xlabel("PC 1")
            ax.set_ylabel("PC 2")

        plt.suptitle("Cluster Assignments in PCA Space", fontsize=14, fontweight="bold")
        plt.tight_layout()
        plt.show()

    def plot_profiles(self) -> None:
        """Heatmap of z-scored mean feature values per cluster per model."""
        if not self.profiles_:
            self.profile()
        n    = len(self.profiles_)
        fig, axes = plt.subplots(1, n, figsize=(8 * n, 5))
        if n == 1:
            axes = [axes]

        for ax, (name, prof) in zip(axes, self.profiles_.items()):
            normed = (prof - prof.mean()) / (prof.std() + 1e-9)
            sns.heatmap(normed.T, ax=ax, cmap="RdYlGn", center=0,
                        linewidths=0.4, annot=(len(prof) <= 8), fmt=".2f")
            ax.set_title(f"{name}", fontweight="bold")
            ax.set_xlabel("Cluster")

        plt.suptitle("Cluster Profiles — z-scored Mean Feature Values",
                     fontsize=13, fontweight="bold")
        plt.tight_layout()
        plt.show()

    def plot_dendrogram(self, n_sample: int = 1_000) -> None:
        """Ward-linkage dendrogram on a random subsample."""
        np.random.seed(self.random_state)
        idx  = np.random.choice(len(self.X_pca_), min(n_sample, len(self.X_pca_)),
                                replace=False)
        Z    = linkage(self.X_pca_[idx], method="ward")
        fig, ax = plt.subplots(figsize=(16, 6))
        dendrogram(Z, ax=ax, truncate_mode="level", p=6,
                   color_threshold=0.65 * max(Z[:, 2]),
                   above_threshold_color="lightgrey")
        ax.axhline(0.65 * max(Z[:, 2]), linestyle="--", color="#e74c3c",
                   linewidth=1.5, label="Cut threshold")
        ax.set_title(f"Hierarchical Clustering — Dendrogram  ({n_sample}-sample, Ward)",
                     fontsize=13, fontweight="bold")
        ax.set_xlabel("Sample index")
        ax.set_ylabel("Ward distance")
        ax.legend()
        plt.tight_layout()
        plt.show()

    def plot_dbscan_kdist(self, min_samples: int = 50, n_sample: int = 10_000) -> None:
        """k-distance graph to guide DBSCAN eps selection."""
        np.random.seed(self.random_state)
        idx  = np.random.choice(len(self.X_pca_), min(n_sample, len(self.X_pca_)),
                                replace=False)
        Xs   = self.X_pca_[idx]
        dist = NearestNeighbors(n_neighbors=min_samples).fit(Xs).kneighbors(Xs)[0]
        k_d  = np.sort(dist[:, -1])[::-1]

        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(k_d, color="#9b59b6", linewidth=1.5, label="k-distance")
        if "DBSCAN" in self.clustering_models:
            eps = self.clustering_models["DBSCAN"].eps
            ax.axhline(eps, linestyle="--", color="#e74c3c", linewidth=1.5,
                       label=f"eps = {eps} (current)")
        ax.set_xlabel("Points sorted by descending k-distance")
        ax.set_ylabel(f"{min_samples}-NN distance")
        ax.set_title(f"DBSCAN k-Distance Graph  (k={min_samples}, {n_sample}-sample)\n"
                     "Choose eps at the elbow", fontsize=12, fontweight="bold")
        ax.legend()
        plt.tight_layout()
        plt.show()


# ═══════════════════════════════════════════════════════════════════════════
#  KMeans training from saved parameters
# ═══════════════════════════════════════════════════════════════════════════
def train_kmeans(
    data_path:   Path,
    params_path: Path,
    output_path: Path,
    features:    list[str] | None = None,
    test_size:   float = 0.20,
    eval_sample: int   = 2_500,
    random_state: int  = 42,
) -> None:
    """
    Load best parameters, train KMeans on the full training split, evaluate on
    a held-out test set, and save the model artefact as a pickle.

    Parameters
    ----------
    data_path    : Path to the raw Spotify CSV.
    params_path  : Path to the JSON file written by hyperparameter_tuning.py.
    output_path  : Destination for the pickled ``{model, scaler, features}`` dict.
    features     : Feature columns to use.  Defaults to ``AUDIO_FEATURES``.
    test_size    : Fraction held out for evaluation.
    eval_sample  : Max samples used for test-set silhouette scoring.
    random_state : Seed.
    """
    features = features or AUDIO_FEATURES

    if not params_path.exists():
        raise FileNotFoundError(
            f"{params_path} not found. Run hyperparameter_tuning.py first."
        )

    with params_path.open(encoding="utf-8") as fh:
        best_params = json.load(fh)
    log.info("Loaded parameters: %s", best_params)

    log.info("Loading data from: %s", data_path)
    df = pd.read_csv(data_path, usecols=features).dropna()
    X  = df.to_numpy(dtype=np.float32)
    if len(X) < 10:
        raise ValueError(f"Need at least 10 rows; found {len(X)}.")

    X_train, X_test = train_test_split(
        X, test_size=test_size, random_state=random_state, shuffle=True
    )
    if best_params["n_clusters"] > len(X_train):
        raise ValueError("n_clusters exceeds training-set size.")

    scaler         = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train).astype(np.float32, copy=False)
    X_test_scaled  = scaler.transform(X_test).astype(np.float32, copy=False)

    log.info("Fitting KMeans (k=%d) on %d training tracks …",
             best_params["n_clusters"], len(X_train))
    model       = KMeans(**best_params)
    model.fit(X_train_scaled)
    test_labels = model.predict(X_test_scaled)

    # Silhouette on subsample
    rng  = np.random.default_rng(random_state)
    n_ev = min(eval_sample, len(X_test_scaled))
    idx  = rng.choice(len(X_test_scaled), size=n_ev, replace=False)
    sv, lv = X_test_scaled[idx], test_labels[idx]
    if 1 < np.unique(lv).size < len(lv):
        sil = silhouette_score(sv, lv)
        log.info("Test silhouette (%d samples): %.4f", n_ev, sil)
    else:
        log.warning("Test silhouette unavailable (fewer than 2 clusters in sample).")

    # Cluster size distribution
    counts = pd.Series(test_labels).value_counts().sort_index()
    dist   = pd.DataFrame({
        "tracks": counts,
        "share %": (counts / len(test_labels) * 100).round(1),
    })
    log.info("Test cluster distribution:\n%s", dist.to_string())

    # Persist artefact
    with output_path.open("wb") as fh:
        pickle.dump({"model": model, "scaler": scaler, "features": features}, fh)
    log.info("Saved model artefact to: %s", output_path)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── cluster sub-command ──────────────────────────────────────────────
    p_cl = sub.add_parser(
        "cluster",
        help="Run the full clustering pipeline (PCA + KMeans + Hierarchical + DBSCAN).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_cl.add_argument(
        "--data", type=Path,
        default=_ROOT / "data" / "spotify-tracks-dataset.csv",
        help="Path to the raw Spotify CSV.",
    )
    p_cl.add_argument("--n-clusters",  type=int,   default=5)
    p_cl.add_argument("--pca-variance",type=float, default=0.90,
                      help="Fraction of variance for PCA.")
    p_cl.add_argument("--dbscan-eps",  type=float, default=1.5)
    p_cl.add_argument("--dbscan-min-samples", type=int, default=50)
    p_cl.add_argument("--sample-size", type=int,   default=10_000,
                      help="Max samples for silhouette computation.")
    p_cl.add_argument("--no-plots",    action="store_true",
                      help="Skip all visualisations.")

    # ── train-kmeans sub-command ─────────────────────────────────────────
    p_km = sub.add_parser(
        "train-kmeans",
        help="Train the best KMeans from hyperparameter_tuning.py output.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_km.add_argument(
        "--data", type=Path,
        default=_ROOT / "data" / "spotify-tracks-dataset.csv",
        help="Path to the raw Spotify CSV.",
    )
    p_km.add_argument(
        "--params", type=Path, default=_ROOT / "models" / "best_kmeans_params.json",
        help="JSON file written by hyperparameter_tuning.py.",
    )
    p_km.add_argument(
        "--output", type=Path, default=_ROOT / "models" / "best_kmeans_model.pkl",
        help="Destination for the pickled model artefact.",
    )

    return parser


def _cmd_cluster(args: argparse.Namespace) -> None:
    log.info("Loading data from: %s", args.data)
    df = pd.read_csv(args.data, usecols=AUDIO_FEATURES).dropna()
    X  = df.to_numpy(dtype=np.float64)
    log.info("Feature matrix: %d x %d", *X.shape)

    models = {
        "PCA":          PCA(n_components=args.pca_variance, random_state=42),
        "KMeans":       KMeans(n_clusters=args.n_clusters, random_state=42, n_init=10),
        "Hierarchical": AgglomerativeClustering(n_clusters=args.n_clusters, linkage="ward"),
        "DBSCAN":       DBSCAN(eps=args.dbscan_eps, min_samples=args.dbscan_min_samples),
    }

    pipeline = ClusteringPipeline(models, sample_size=args.sample_size)
    pipeline.fit(X, feature_names=AUDIO_FEATURES)

    metrics = pipeline.evaluate()
    print("\n=== Evaluation Metrics ===")
    print(metrics.to_string())

    pipeline.profile()
    for name, prof in pipeline.profiles_.items():
        print(f"\n--- Cluster profile: {name} ---")
        print(prof.round(3).to_string())

    if not args.no_plots:
        pipeline.plot_pca_scatter()
        pipeline.plot_profiles()
        pipeline.plot_dendrogram()
        pipeline.plot_dbscan_kdist(min_samples=args.dbscan_min_samples)
        for name in pipeline.clustering_models:
            if len(set(pipeline.labels_[name]) - {-1}) > 1:
                pipeline.plot_silhouette(name)


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    if args.command == "cluster":
        _cmd_cluster(args)
    elif args.command == "train-kmeans":
        train_kmeans(
            data_path=args.data,
            params_path=args.params,
            output_path=args.output,
        )


if __name__ == "__main__":
    main()
