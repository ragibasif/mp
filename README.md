# mp

A local music player with a generative MP4 visualizer, built in Python with
Streamlit. Point it at a folder of audio files; pick a track; analyze it once
to extract beats + spectral features (cached to disk); render a video whose
radial spectrum bars, beat-reactive particle bursts, and centroid-driven hue
shift all derive from the music itself.

## What it does

- Recursive scan of a music folder (mp3 / flac / wav / m4a / ogg / opus / aac)
- Track table with embedded metadata (title / artist / album / duration) and
  full-text search
- Audio playback with previous / next within the current filtered view
- Per-track audio analysis via librosa — tempo, beat times, onset envelope,
  RMS, spectral centroid, chroma, 32-band mel — cached as compressed `.npz`
  keyed by content hash
- Generative MP4 render driven by those features, audio embedded so the
  visuals stay in lockstep with playback (browser plays one media stream, not
  two unsynchronized ones)
- All caches live on disk in `.cache/` and survive restarts

## Run locally

```sh
uv run streamlit run src/mp/app.py
```

The app opens at http://localhost:8501. Default music folder is `~/Music` —
override in the sidebar or set `MUSIC_FOLDER=/path/to/music` before running.

## Run with Docker

The image contains the app and its Python dependencies (including a bundled
ffmpeg via `imageio-ffmpeg`). Your music library stays on the host and is
mounted into the container read-only.

### docker compose (recommended)

```sh
HOST_MUSIC=/Users/you/Music docker compose up --build
```

Cache (extracted features, rendered videos) persists across runs in a named
volume `mp_cache`. To wipe it: `docker compose down -v`.

### plain docker

```sh
docker build -t mp .
docker run --rm -p 8501:8501 \
    -v "$HOME/Music:/music:ro" \
    -v mp_cache:/app/.cache \
    mp
```

## Project layout

```
src/mp/
    app.py        Streamlit entrypoint
    library.py    Folder scan + metadata + album-art extraction
    features.py   librosa feature extraction + npz round-trip
    render.py     PIL frame compositing + MP4 mux
    viz.py        matplotlib helpers (RMS+beats, chroma)
    cache.py      Content-hash keyed disk cache
.streamlit/
    config.toml   Dark theme, hot-reload
.cache/           Git-ignored. features/v2/, videos/v1/
```

## Development notes

- Python 3.13. Dependencies pinned in `uv.lock`.
- Streamlit 1.57+ uses `width="stretch"` for full-width widgets — older
  `use_container_width=True` is deprecated.
- If `librosa.beat.beat_track` segfaults, clear stale numba bitcode:
  `find .venv -name "*.nbi" -o -name "*.nbc" | xargs rm -f`
- Pyright warnings about `streamlit` / `librosa` / `numpy` not being importable
  are usually the IDE pointing at the system Python instead of `.venv`. Set
  your editor's interpreter to `.venv/bin/python`.
