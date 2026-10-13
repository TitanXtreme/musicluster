"""
FastAPI wrapper around the trained KMeans model (best_kmeans_model.pkl).

Endpoints
---------
GET  /health          → health check (alias: GET /)
GET  /clusters        → list all cluster labels with descriptions
POST /predict         → predict cluster for a song
GET  /stats           → dataset-level statistics
GET  /songs/search    → search songs by name or artist
POST /suggest         → nearest-neighbour song recommendations
"""

from __future__ import annotations

import math
import pickle
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sklearn.neighbors import NearestNeighbors

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FEATURES: list[str] = [
    "popularity",
    "duration_ms",
    "explicit",
    "danceability",
    "energy",
    "key",
    "loudness",
    "mode",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "time_signature",
]

# Cluster labels (3 clusters from KMeans with k=3)
# Profiles from training (means of standardised features):
#   Cluster 0: high explicit (0.97), high danceability, high speechiness  → Hip-Hop / Party
#   Cluster 1: zero explicit, high energy (0.75), high valence (0.53)     → Workout / Upbeat Pop
#   Cluster 2: low energy (0.30), very high acousticness (0.75), quiet    → Chill / Study / Acoustic
CLUSTER_LABELS: dict[int, dict[str, str]] = {
    0: {
        "label": "Hip-Hop / Party",
        "emoji": "",
        "description": (
            "Energetic tracks with explicit lyrics and strong rhythmic speech. "
            "High danceability and loudness — perfect for parties and rap sessions."
        ),
        "vibe": "party",
        "color": "#2a78d6",
    },
    1: {
        "label": "Workout / Upbeat Pop",
        "emoji": "",
        "description": (
            "High-energy, feel-good mainstream pop and rock with positive valence. "
            "Great for workouts, commutes, and staying motivated."
        ),
        "vibe": "workout",
        "color": "#eb6834",
    },
    2: {
        "label": "Chill / Study / Acoustic",
        "emoji": "",
        "description": (
            "Low-energy, highly acoustic tracks with calm moods. "
            "Ideal for studying, relaxing, or unwinding at the end of the day."
        ),
        "vibe": "study",
        "color": "#1baf7a",
    },
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
_MODEL_PATH = _ROOT / "models" / "best_kmeans_model.pkl"
_DATASET_PATH = _ROOT / "data" / "spotify-tracks-dataset.csv"

# ---------------------------------------------------------------------------
# Global state (populated at startup)
# ---------------------------------------------------------------------------
_artifact: dict[str, Any] | None = None
_df: pd.DataFrame | None = None          # full dataset (rows with complete features)
_scaled_matrix: np.ndarray | None = None # scaler-transformed feature matrix
_nn_model: NearestNeighbors | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_artifact() -> dict[str, Any]:
    global _artifact
    if _artifact is not None:
        return _artifact
    if not _MODEL_PATH.is_file():
        raise RuntimeError(
            f"Model file not found at {_MODEL_PATH}. "
            "Run model_training.py train-kmeans first."
        )
    with _MODEL_PATH.open("rb") as fh:
        artifact = pickle.load(fh)
    required = {"model", "scaler", "features"}
    if missing := required - artifact.keys():
        raise RuntimeError(f"Artifact missing keys: {missing}")
    _artifact = artifact
    return _artifact


def _load_dataset(scaler) -> tuple[pd.DataFrame, np.ndarray]:
    """Load CSV, keep rows with complete feature values, attach cluster labels."""
    df = pd.read_csv(_DATASET_PATH, low_memory=False)

    # Normalise explicit: True/False strings → 0/1
    if "explicit" in df.columns:
        df["explicit"] = df["explicit"].map(
            lambda v: 1.0 if str(v).strip().lower() == "true" else 0.0
        )

    # Keep only columns we need (plus metadata)
    meta_cols = ["track_id", "track_name", "artists", "track_genre"]
    available_features = [f for f in FEATURES if f in df.columns]
    available_meta = [c for c in meta_cols if c in df.columns]

    df = df[available_meta + available_features].copy()
    df = df.dropna(subset=available_features)
    df = df.reset_index(drop=True)

    # Coerce feature columns to float
    for col in available_features:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=available_features).reset_index(drop=True)

    # Scale features
    X = df[available_features].values.astype(np.float64)
    X_scaled = scaler.transform(X)

    return df, X_scaled


def _attach_cluster_ids(df: pd.DataFrame, X_scaled: np.ndarray, model) -> pd.DataFrame:
    df = df.copy()
    df["cluster_id"] = model.predict(X_scaled.astype(model.cluster_centers_.dtype))
    return df


def _build_nn_model(X_scaled: np.ndarray) -> NearestNeighbors:
    nn = NearestNeighbors(n_neighbors=50, metric="cosine", algorithm="brute")
    nn.fit(X_scaled)
    return nn


def _row_to_song_dict(row: pd.Series, include_cluster_label: bool = False) -> dict:
    """Convert a DataFrame row to the standardised song dict."""
    features = {f: float(row[f]) for f in FEATURES if f in row.index}
    result: dict = {
        "track_id": str(row.get("track_id", "")),
        "track_name": str(row.get("track_name", "")),
        "artists": str(row.get("artists", "")),
        "track_genre": str(row.get("track_genre", "")),
        "cluster_id": int(row["cluster_id"]) if "cluster_id" in row.index else -1,
        "features": features,
    }
    if include_cluster_label:
        cid = result["cluster_id"]
        info = CLUSTER_LABELS.get(cid, {})
        result["cluster_label"] = info.get("label", "Unknown")
        result["cluster_color"] = info.get("color", "#888888")
    return result


def _build_why(query_scaled: np.ndarray, row_scaled: np.ndarray, cluster_id: int) -> str:
    """Return a 1-line human-readable reason using the top-2 closest features."""
    diffs = np.abs(query_scaled - row_scaled)
    top2_idx = np.argsort(diffs)[:2]
    available = [f for f in FEATURES if f in FEATURES]
    names = [available[i] for i in top2_idx if i < len(available)]
    cluster_info = CLUSTER_LABELS.get(cluster_id, {})
    label = cluster_info.get("label", f"cluster {cluster_id}")
    if len(names) >= 2:
        return f"Very close on {names[0]} and {names[1]}, same cluster ({label})"
    elif len(names) == 1:
        return f"Very close on {names[0]}, same cluster ({label})"
    return f"Same cluster ({label})"


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model, dataset, and NearestNeighbors index at startup."""
    global _artifact, _df, _scaled_matrix, _nn_model

    try:
        artifact = _load_artifact()
        scaler = artifact["scaler"]
        model = artifact["model"]

        df, X_scaled = _load_dataset(scaler)
        df = _attach_cluster_ids(df, X_scaled, model)

        _df = df
        _scaled_matrix = X_scaled
        _nn_model = _build_nn_model(X_scaled)
    except Exception as exc:
        # Startup failure is non-fatal for the app object itself; endpoints
        # will surface the error when called.
        print(f"[startup] WARNING — could not load resources: {exc}")

    yield  # app runs here


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Spotify Cluster Predictor",
    description="Predicts which mood cluster a song belongs to using KMeans.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class SongFeatures(BaseModel):
    """Audio features for a single Spotify track."""

    popularity: float = Field(..., ge=0, le=100, description="Track popularity (0-100)")
    duration_ms: float = Field(..., gt=0, description="Track duration in milliseconds")
    explicit: float = Field(..., ge=0, le=1, description="Explicit flag (0 or 1)")
    danceability: float = Field(..., ge=0, le=1, description="Danceability score (0-1)")
    energy: float = Field(..., ge=0, le=1, description="Energy score (0-1)")
    key: float = Field(..., ge=0, le=11, description="Musical key (0-11)")
    loudness: float = Field(..., ge=-60, le=5, description="Loudness in dB")
    mode: float = Field(..., ge=0, le=1, description="Mode — major(1) or minor(0)")
    speechiness: float = Field(..., ge=0, le=1, description="Speechiness (0-1)")
    acousticness: float = Field(..., ge=0, le=1, description="Acousticness (0-1)")
    instrumentalness: float = Field(..., ge=0, le=1, description="Instrumentalness (0-1)")
    liveness: float = Field(..., ge=0, le=1, description="Liveness (0-1)")
    valence: float = Field(..., ge=0, le=1, description="Valence / musical positivity (0-1)")
    tempo: float = Field(..., gt=0, description="Tempo in BPM")
    time_signature: float = Field(..., ge=1, le=7, description="Time signature (1-7)")

    @field_validator("explicit", "mode")
    @classmethod
    def must_be_binary(cls, v: float, info) -> float:
        if v not in (0.0, 1.0, 0, 1):
            raise ValueError(f"{info.field_name} must be 0 or 1")
        return float(v)


class PredictionResponse(BaseModel):
    cluster_id: int
    label: str
    emoji: str
    vibe: str
    description: str
    color: str
    distance_to_center: float


class ClusterInfo(BaseModel):
    cluster_id: int
    label: str
    emoji: str
    vibe: str
    description: str
    color: str


class SuggestRequest(BaseModel):
    features: dict[str, float] = Field(..., description="All 15 audio feature values")
    count: int = Field(10, ge=1, le=100, description="Number of suggestions to return")
    diversity: float = Field(
        0.0, ge=0.0, le=1.0,
        description="Fraction of results from neighbouring clusters (0=none, 1=all)"
    )
    exclude_ids: list[str] = Field(
        default_factory=list,
        description="track_ids to exclude from results"
    )


class SuggestResult(BaseModel):
    track_id: str
    track_name: str
    artists: str
    track_genre: str
    cluster_id: int
    cluster_label: str
    cluster_color: str
    match_pct: float
    why: str
    features: dict[str, float]


# ---------------------------------------------------------------------------
# Routes — existing
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
def health() -> dict:
    """Health check."""
    return {"status": "ok", "model": str(_MODEL_PATH.name)}


@app.get("/clusters", response_model=list[ClusterInfo], tags=["Clusters"])
def list_clusters() -> list[ClusterInfo]:
    """Return all cluster labels with metadata."""
    return [
        ClusterInfo(cluster_id=cid, **info)
        for cid, info in CLUSTER_LABELS.items()
    ]


@app.post("/predict", response_model=PredictionResponse, tags=["Predict"])
def predict(song: SongFeatures) -> PredictionResponse:
    """
    Predict the mood cluster for a given set of Spotify audio features.

    Returns the cluster label (e.g. 'Chill / Study / Acoustic') plus metadata
    and the distance to the cluster centroid (lower = better fit).
    """
    try:
        artifact = _load_artifact()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    features: list[str] = artifact["features"]
    values = song.model_dump()

    # Build input row in the exact feature order the model was trained on
    row = np.asarray([[values[f] for f in features]], dtype=np.float64)

    model = artifact["model"]
    scaler = artifact["scaler"]

    scaled = scaler.transform(row).astype(model.cluster_centers_.dtype, copy=False)
    cluster_id = int(model.predict(scaled)[0])
    distance = float(model.transform(scaled)[0][cluster_id])

    info = CLUSTER_LABELS[cluster_id]
    return PredictionResponse(
        cluster_id=cluster_id,
        distance_to_center=round(distance, 4),
        **info,
    )


# ---------------------------------------------------------------------------
# Routes — new
# ---------------------------------------------------------------------------
@app.get("/stats", tags=["Stats"])
def stats() -> dict:
    """Return dataset-level statistics."""
    if _df is None:
        raise HTTPException(status_code=503, detail="Dataset not loaded yet.")

    cluster_sizes: dict[str, int] = {}
    for cid in range(3):
        cluster_sizes[str(cid)] = int((_df["cluster_id"] == cid).sum())

    return {
        "total_songs": len(_df),
        "total_clusters": int(_df["cluster_id"].nunique()),
        "features_count": len(FEATURES),
        "cluster_sizes": {0: cluster_sizes["0"], 1: cluster_sizes["1"], 2: cluster_sizes["2"]},
    }


@app.get("/songs/search", tags=["Songs"])
def search_songs(
    q: str = Query(..., min_length=1, description="Search query (track name or artist)"),
    limit: int = Query(20, ge=1, le=200, description="Maximum results to return"),
) -> list[dict]:
    """
    Search songs by track_name or artists (case-insensitive substring match).

    Returns a list of songs with their features and cluster assignment.
    """
    if _df is None:
        raise HTTPException(status_code=503, detail="Dataset not loaded yet.")

    q_lower = q.lower()
    mask = pd.Series(False, index=_df.index)

    if "track_name" in _df.columns:
        mask |= _df["track_name"].str.lower().str.contains(q_lower, na=False)
    if "artists" in _df.columns:
        mask |= _df["artists"].str.lower().str.contains(q_lower, na=False)

    results = _df[mask].head(limit)
    return [_row_to_song_dict(row) for _, row in results.iterrows()]


@app.post("/suggest", response_model=list[SuggestResult], tags=["Suggest"])
def suggest(req: SuggestRequest) -> list[SuggestResult]:
    """
    Return nearest-neighbour song recommendations based on input audio features.

    - Uses cosine similarity in the scaled feature space.
    - Supports `diversity` to mix in songs from neighbouring clusters.
    - Excludes any track_ids listed in `exclude_ids`.
    - Returns `count` results with match_pct and a short human-readable `why` string.
    """
    if _df is None or _scaled_matrix is None or _nn_model is None:
        raise HTTPException(status_code=503, detail="Dataset or NN index not loaded yet.")

    try:
        artifact = _load_artifact()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    scaler = artifact["scaler"]
    model = artifact["model"]

    # ---- Build query vector ----
    try:
        query_vec = np.array(
            [[req.features.get(f, 0.0) for f in FEATURES]], dtype=np.float64
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Feature extraction error: {exc}") from exc

    query_scaled = scaler.transform(query_vec)  # shape (1, 15)
    query_cluster = int(model.predict(query_scaled.astype(model.cluster_centers_.dtype))[0])

    exclude_set = set(req.exclude_ids)
    total_needed = req.count

    # How many from neighbouring clusters?
    diversity_count = math.floor(total_needed * req.diversity) if req.diversity > 0.0 else 0
    primary_count = total_needed - diversity_count

    # ---- Query NearestNeighbors (use headroom of 50 neighbours) ----
    n_query = min(50, len(_df))
    distances, indices = _nn_model.kneighbors(query_scaled, n_neighbors=n_query)
    distances = distances[0]   # shape (n_query,)
    indices = indices[0]       # shape (n_query,)

    # max_distance for normalising match_pct (avoid div-by-zero)
    max_dist = float(distances.max()) if distances.max() > 0 else 1.0

    def make_result(idx: int, dist: float) -> SuggestResult:
        row = _df.iloc[idx]
        cid = int(row["cluster_id"])
        info = CLUSTER_LABELS.get(cid, {})

        row_scaled = _scaled_matrix[idx]  # shape (15,)
        why = _build_why(query_scaled[0], row_scaled, cid)

        match_pct = float(np.clip(100.0 * (1.0 - dist / max_dist), 0.0, 100.0))

        features_dict = {f: float(row[f]) for f in FEATURES if f in row.index}

        return SuggestResult(
            track_id=str(row.get("track_id", "")),
            track_name=str(row.get("track_name", "")),
            artists=str(row.get("artists", "")),
            track_genre=str(row.get("track_genre", "")),
            cluster_id=cid,
            cluster_label=info.get("label", "Unknown"),
            cluster_color=info.get("color", "#888888"),
            match_pct=round(match_pct, 2),
            why=why,
            features=features_dict,
        )

    # ---- Collect primary results (same cluster preferred) ----
    primary_results: list[SuggestResult] = []
    diversity_results: list[SuggestResult] = []

    for idx, dist in zip(indices, distances):
        row = _df.iloc[idx]
        tid = str(row.get("track_id", ""))
        if tid in exclude_set:
            continue

        cid = int(row["cluster_id"])
        result = make_result(int(idx), float(dist))

        if cid == query_cluster and len(primary_results) < primary_count:
            primary_results.append(result)
        elif cid != query_cluster and len(diversity_results) < diversity_count:
            diversity_results.append(result)

        if len(primary_results) >= primary_count and len(diversity_results) >= diversity_count:
            break

    # If we didn't fill primary from same cluster, back-fill from any cluster
    if len(primary_results) < primary_count:
        seen_track_ids = {r.track_id for r in primary_results + diversity_results}
        for idx, dist in zip(indices, distances):
            if len(primary_results) >= primary_count:
                break
            row = _df.iloc[idx]
            tid = str(row.get("track_id", ""))
            if tid in exclude_set or tid in seen_track_ids:
                continue
            primary_results.append(make_result(int(idx), float(dist)))
            seen_track_ids.add(tid)

    final = primary_results + diversity_results
    return final[:total_needed]


# ---------------------------------------------------------------------------
# Dev runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
