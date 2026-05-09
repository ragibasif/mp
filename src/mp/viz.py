from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from features import Features

matplotlib.rcParams.update({
    "axes.facecolor": "#16161f",
    "figure.facecolor": "#0b0b12",
    "axes.edgecolor": "#3a3a4a",
    "axes.labelcolor": "#aaa",
    "xtick.color": "#aaa",
    "ytick.color": "#aaa",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 9,
})

ACCENT = "#7c5cff"
BEAT_COLOR = "#ffffff33"


def plot_rms_with_beats(feat: Features) -> Figure:
    fig, ax = plt.subplots(figsize=(10, 1.8))
    rms_norm = feat.rms / max(feat.rms.max(), 1e-9)
    ax.plot(feat.times, rms_norm, color=ACCENT, linewidth=1.0)
    ax.fill_between(feat.times, rms_norm, alpha=0.25, color=ACCENT)
    for t in feat.beat_times:
        ax.axvline(float(t), color=BEAT_COLOR, linewidth=0.5)
    ax.set_xlim(0, feat.duration_s)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([])
    ax.set_xlabel("time (s)")
    fig.tight_layout()
    return fig


def plot_chroma(feat: Features) -> Figure:
    fig, ax = plt.subplots(figsize=(10, 2.2))
    ax.imshow(
        feat.chroma,
        aspect="auto",
        origin="lower",
        cmap="magma",
        extent=(0.0, float(feat.duration_s), 0, 12),
        interpolation="nearest",
    )
    ax.set_yticks(np.arange(12) + 0.5)
    ax.set_yticklabels(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])
    ax.set_xlabel("time (s)")
    fig.tight_layout()
    return fig
