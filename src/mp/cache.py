from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

CACHE_VERSION = "v2"
VIDEO_VERSION = "v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / ".cache" / "features" / CACHE_VERSION
VIDEO_DIR = REPO_ROOT / ".cache" / "videos" / VIDEO_VERSION


def _hash_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def cache_key(path: str) -> str:
    return _hash_file(Path(path))


def cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{key}.npz"


def is_cached(key: str) -> bool:
    return (CACHE_DIR / f"{key}.npz").exists()


def load(key: str) -> dict[str, np.ndarray] | None:
    p = cache_path(key)
    if not p.exists():
        return None
    with np.load(p) as z:
        return {k: z[k] for k in z.files}


def save(key: str, data: dict[str, np.ndarray]) -> None:
    np.savez_compressed(cache_path(key), **data)


def video_path(audio_key: str, config_key: str) -> Path:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    return VIDEO_DIR / f"{audio_key}_{config_key}.mp4"


def video_is_cached(audio_key: str, config_key: str) -> bool:
    return (VIDEO_DIR / f"{audio_key}_{config_key}.mp4").exists()
