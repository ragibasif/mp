from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

import cache as feat_cache

DEFAULT_SR = 22050
HOP_LENGTH = 512


@dataclass(frozen=True, slots=True)
class Features:
    sr: int
    duration_s: float
    tempo_bpm: float
    beat_times: np.ndarray   # (n_beats,)
    onset_env: np.ndarray    # (n_frames,)
    rms: np.ndarray          # (n_frames,)
    centroid: np.ndarray     # (n_frames,)
    chroma: np.ndarray       # (12, n_frames)
    times: np.ndarray        # (n_frames,)


def _f32(a: np.ndarray) -> np.ndarray:
    return a.astype(np.float32, copy=False)


def extract(path: str) -> Features:
    y, sr = librosa.load(path, sr=DEFAULT_SR, mono=True)
    duration = len(y) / sr

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP_LENGTH)
    tempo, beats = librosa.beat.beat_track(
        onset_envelope=onset_env, sr=sr, hop_length=HOP_LENGTH
    )
    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=HOP_LENGTH)

    rms = librosa.feature.rms(y=y, hop_length=HOP_LENGTH)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=HOP_LENGTH)[0]
    chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=HOP_LENGTH)

    n_frames = onset_env.shape[0]
    times = librosa.frames_to_time(np.arange(n_frames), sr=sr, hop_length=HOP_LENGTH)

    return Features(
        sr=int(sr),
        duration_s=float(duration),
        tempo_bpm=float(np.atleast_1d(tempo)[0]),
        beat_times=_f32(beat_times),
        onset_env=_f32(onset_env),
        rms=_f32(rms),
        centroid=_f32(centroid),
        chroma=_f32(chroma),
        times=_f32(times),
    )


def _features_from_npz(d: dict[str, np.ndarray]) -> Features:
    return Features(
        sr=int(d["sr"]),
        duration_s=float(d["duration_s"]),
        tempo_bpm=float(d["tempo_bpm"]),
        beat_times=d["beat_times"],
        onset_env=d["onset_env"],
        rms=d["rms"],
        centroid=d["centroid"],
        chroma=d["chroma"],
        times=d["times"],
    )


def _features_to_npz(f: Features) -> dict[str, np.ndarray]:
    return {
        "sr": np.asarray(f.sr),
        "duration_s": np.asarray(f.duration_s, dtype=np.float32),
        "tempo_bpm": np.asarray(f.tempo_bpm, dtype=np.float32),
        "beat_times": f.beat_times,
        "onset_env": f.onset_env,
        "rms": f.rms,
        "centroid": f.centroid,
        "chroma": f.chroma,
        "times": f.times,
    }


def is_analyzed(path: str) -> bool:
    if not Path(path).is_file():
        return False
    return feat_cache.is_cached(feat_cache.cache_key(path))


def extract_cached(path: str) -> Features:
    key = feat_cache.cache_key(path)
    cached = feat_cache.load(key)
    if cached is not None:
        return _features_from_npz(cached)
    feat = extract(path)
    feat_cache.save(key, _features_to_npz(feat))
    return feat
