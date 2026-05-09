from __future__ import annotations

import colorsys
import subprocess
import tempfile
from pathlib import Path

import imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

import cache as feat_cache
from features import Features

# Render configuration. Bumping any of these should trigger re-render via the
# config hash baked into the cached filename.
FPS = 24
SIZE = 480
N_BARS = 32
BASE_R = 90
MAX_BAR_LEN = 130
PARTICLE_LIFE = 1.2     # seconds
PARTICLE_SPEED = 280.0  # px/s outward
PARTICLE_BURST = 18     # spawned per beat
BEAT_DECAY = 5.0        # exponential decay rate for beat pulse


def _render_config_key() -> str:
    return f"fps{FPS}_sz{SIZE}_n{N_BARS}_br{BASE_R}_ml{MAX_BAR_LEN}"


def _color_for_centroid(centroid_hz: float) -> tuple[int, int, int]:
    # 500..4000 Hz -> hue 0.72..0.02 (deep purple -> warm orange).
    norm = float(np.clip((centroid_hz - 500.0) / 3500.0, 0.0, 1.0))
    hue = 0.72 - 0.70 * norm
    r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 1.0)
    return int(r * 255), int(g * 255), int(b * 255)


def _beat_pulse(t: float, beat_times: np.ndarray) -> float:
    if beat_times.size == 0:
        return 0.0
    past = beat_times[beat_times <= t]
    if past.size == 0:
        return 0.0
    return float(np.exp(-BEAT_DECAY * (t - past[-1])))


def _sample_at(arr: np.ndarray, t: float, duration: float) -> float:
    if duration <= 0 or arr.size == 0:
        return 0.0
    i = int(t / duration * arr.size)
    return float(arr[max(0, min(arr.size - 1, i))])


def _sample_mel(feat: Features, t: float) -> np.ndarray:
    n = feat.mel_db.shape[1]
    if feat.duration_s <= 0 or n == 0:
        return np.zeros(feat.mel_db.shape[0], dtype=np.float32)
    i = int(t / feat.duration_s * n)
    i = max(0, min(n - 1, i))
    lo, hi = max(0, i - 1), min(n, i + 2)
    return feat.mel_db[:, lo:hi].mean(axis=1)


class Particles:
    __slots__ = ("xs", "ys", "vxs", "vys", "ages", "colors")

    def __init__(self) -> None:
        self.xs: list[float] = []
        self.ys: list[float] = []
        self.vxs: list[float] = []
        self.vys: list[float] = []
        self.ages: list[float] = []
        self.colors: list[tuple[int, int, int]] = []

    def burst(
        self,
        n: int,
        color: tuple[int, int, int],
        speed: float,
        rng: np.random.Generator,
    ) -> None:
        for _ in range(n):
            angle = float(rng.random() * 2 * np.pi)
            v = float(rng.uniform(0.6, 1.0)) * speed
            self.xs.append(0.0)
            self.ys.append(0.0)
            self.vxs.append(v * float(np.cos(angle)))
            self.vys.append(v * float(np.sin(angle)))
            self.ages.append(0.0)
            self.colors.append(color)

    def update(self, dt: float) -> None:
        keep_x, keep_y, keep_vx, keep_vy, keep_age, keep_color = [], [], [], [], [], []
        for x, y, vx, vy, age, c in zip(
            self.xs, self.ys, self.vxs, self.vys, self.ages, self.colors
        ):
            new_age = age + dt
            if new_age >= PARTICLE_LIFE:
                continue
            keep_x.append(x + vx * dt)
            keep_y.append(y + vy * dt)
            keep_vx.append(vx)
            keep_vy.append(vy)
            keep_age.append(new_age)
            keep_color.append(c)
        self.xs, self.ys, self.vxs, self.vys, self.ages, self.colors = (
            keep_x, keep_y, keep_vx, keep_vy, keep_age, keep_color,
        )

    def draw(self, draw: ImageDraw.ImageDraw, cx: float, cy: float) -> None:
        for x, y, age, c in zip(self.xs, self.ys, self.ages, self.colors):
            life = max(0.0, 1.0 - age / PARTICLE_LIFE)
            r = 1.5 + 4.0 * life
            faded = (int(c[0] * life), int(c[1] * life), int(c[2] * life))
            px, py = cx + x, cy + y
            draw.ellipse([px - r, py - r, px + r, py + r], fill=faded)


def _render_frame(t: float, feat: Features, particles: Particles) -> np.ndarray:
    cx = cy = SIZE / 2.0
    img = Image.new("RGB", (SIZE, SIZE), (11, 11, 18))
    draw = ImageDraw.Draw(img)

    rms_at = _sample_at(feat.rms, t, feat.duration_s)
    centroid_at = _sample_at(feat.centroid, t, feat.duration_s)
    pulse = _beat_pulse(t, feat.beat_times)
    color = _color_for_centroid(centroid_at)

    glow_r = 28.0 + 36.0 * rms_at + 18.0 * pulse
    glow_color = (int(color[0] * 0.4), int(color[1] * 0.4), int(color[2] * 0.4))
    draw.ellipse(
        [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r],
        fill=glow_color,
    )

    inner_r = 14.0 + 12.0 * pulse
    draw.ellipse(
        [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
        fill=color,
    )

    mel = _sample_mel(feat, t)
    bars_norm = np.clip((mel + 80.0) / 80.0, 0.0, 1.0) ** 1.4
    boost = 1.0 + 0.45 * pulse

    for i in range(N_BARS):
        angle = 2.0 * np.pi * i / N_BARS - np.pi / 2.0
        height = float(bars_norm[i]) * MAX_BAR_LEN * boost
        ca, sa = float(np.cos(angle)), float(np.sin(angle))
        x1, y1 = cx + BASE_R * ca, cy + BASE_R * sa
        x2, y2 = cx + (BASE_R + height) * ca, cy + (BASE_R + height) * sa
        draw.line([(x1, y1), (x2, y2)], fill=color, width=4)

    particles.draw(draw, cx, cy)
    return np.asarray(img)


def _render_silent_video(feat: Features, silent_path: Path) -> None:
    n_frames = max(1, int(feat.duration_s * FPS))
    dt = 1.0 / FPS
    rng = np.random.default_rng(0)
    particles = Particles()

    writer = imageio.get_writer(
        str(silent_path),
        fps=FPS,
        codec="libx264",
        quality=8,
        macro_block_size=1,
    )
    try:
        for k in range(n_frames):
            t = k * dt
            beats_in_window = (feat.beat_times > t - dt) & (feat.beat_times <= t)
            if bool(beats_in_window.any()):
                centroid_at = _sample_at(feat.centroid, t, feat.duration_s)
                color = _color_for_centroid(centroid_at)
                particles.burst(PARTICLE_BURST, color, PARTICLE_SPEED, rng)
            particles.update(dt)
            writer.append_data(_render_frame(t, feat, particles))
    finally:
        writer.close()


def _mux_audio(silent_path: Path, audio_path: str, out_path: Path) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run(
        [
            ffmpeg, "-y",
            "-i", str(silent_path),
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(out_path),
        ],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg mux failed: {proc.stderr.decode(errors='replace')[:500]}"
        )


def render_video(feat: Features, audio_path: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        silent = Path(td) / "silent.mp4"
        _render_silent_video(feat, silent)
        _mux_audio(silent, audio_path, out_path)


def render_for_track(audio_path: str, feat: Features) -> Path:
    audio_key = feat_cache.cache_key(audio_path)
    config_key = _render_config_key()
    out = feat_cache.video_path(audio_key, config_key)
    if out.exists():
        return out
    render_video(feat, audio_path, out)
    return out


def cached_video_path(audio_path: str) -> Path | None:
    audio_key = feat_cache.cache_key(audio_path)
    config_key = _render_config_key()
    if feat_cache.video_is_cached(audio_key, config_key):
        return feat_cache.video_path(audio_key, config_key)
    return None
