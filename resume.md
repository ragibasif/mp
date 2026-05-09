# Resume Bullets — `mp` (music player + generative visualizer)

**Project header (one-liner)**

> Music Player and Generative Audio Visualizer — Python, Streamlit, librosa, NumPy, PIL, Docker, ffmpeg

---

## Bullet points (ATS-friendly)

- Designed and built a full-stack Python 3.13 audio analysis and visualization application with Streamlit, librosa, NumPy, and PIL, supporting 7 audio formats (MP3, FLAC, WAV, M4A, OGG, OPUS, AAC) and generating beat-synchronized MP4 videos with embedded AAC audio at 24 fps.

- Engineered a two-layer caching architecture combining in-memory Streamlit caches (`@st.cache_data`) with a content-hash-keyed disk cache using streaming SHA-256, reducing repeat audio feature extraction from 30 seconds to under 10 milliseconds — a 3,000x speedup on cache hits.

- Implemented a digital signal processing pipeline using librosa to extract tempo, beat times, onset envelopes, RMS energy, spectral centroid, 12-band chroma, and 32-band mel spectrograms; benchmarked at 5-10 seconds per track across an 8,294-track library.

- Developed a custom PIL-based generative video renderer that composites radial mel-spectrum bars, beat-reactive particle systems, RMS-modulated center pulses, and spectral-centroid-driven HSV hue shifts, completing a 3-minute MP4 render in 10.3 seconds (~6 ms/frame, roughly 5x faster than matplotlib animation).

- Containerized the application with a multi-stage Dockerfile using `uv` for reproducible, lockfile-driven Python dependency installation, paired with `docker-compose.yml` for read-only host music library mounts and a named volume that persists analysis caches across container restarts.

- Wrote integration tests using Streamlit's `AppTest` framework, covering selection-state persistence, full-text search filtering, prev/next navigation through filtered subsets, and cache invalidation across UI state changes (5+ scenarios).

- Diagnosed and resolved a SIGSEGV crash in `librosa.beat.beat_track` caused by ABI-incompatible numba bitcode caches in site-packages `__pycache__`; documented the recovery procedure in project documentation.

- Designed a cache invalidation strategy using SHA-256 content hashing (over mtime) to preserve correctness across file moves, backups, and metadata-only retag operations, paired with versioned cache directories (`v1/`, `v2/`) for clean schema migrations.

- Optimized library scanning with the mutagen library, extracting ID3, Vorbis, and MP4 metadata across an 8,294-track collection in 25 seconds (~3 ms per file), with format-specific album art extraction (ID3 APIC frames, FLAC Picture blocks, MP4 'covr' atoms).

---

## Compact (3-bullet) version for tight-space resumes

- Built and shipped a Python music player and generative visualizer with Streamlit, librosa, and Docker; generates beat-synchronized MP4 videos from arbitrary audio files at 480x480 / 24 fps with embedded audio.

- Engineered a two-layer caching system (in-memory + SHA-256 content-hashed disk cache) achieving a 3,000x speedup on repeat audio analysis (30 seconds to 10 milliseconds) across an 8,294-track library.

- Containerized with a multi-stage Dockerfile (`uv`, Python 3.13 slim) and `docker-compose` with read-only volume mounts for host libraries and persistent caches; verified end-to-end with Streamlit `AppTest` integration tests.

---

## One-paragraph summary (for cover letters / LinkedIn)

Built a Python music player and generative audio visualizer using Streamlit, librosa, NumPy, and PIL. The application scans local music libraries (up to 8,000+ tracks), extracts musical features including tempo, beats, onset envelopes, and mel spectrograms via a librosa-based DSP pipeline, and renders beat-synchronized MP4 videos at 24 fps with embedded audio — completing a 3-minute render in roughly 10 seconds. A two-layer caching architecture (in-memory Streamlit caches plus SHA-256 content-keyed disk caches) accelerates repeat operations 3,000x. Deployment is handled by a multi-stage Dockerfile using `uv` plus `docker-compose` with read-only host mounts and a persistent cache volume; behavior is verified by integration tests using Streamlit's `AppTest` framework.

---

## Skills / keywords inventory (for skills section or ATS keyword stuffing)

**Languages:** Python 3.13

**Frameworks / libraries:** Streamlit, librosa, NumPy, pandas, PIL/Pillow, matplotlib, mutagen, imageio, imageio-ffmpeg, numba, scipy, scikit-learn

**Tooling:** uv (package manager), Docker, docker-compose, ffmpeg, multi-stage Docker builds

**Concepts:** audio signal processing, FFT / mel spectrogram, beat detection, content-addressable storage, SHA-256 hashing, cache invalidation, integration testing, schema versioning, dependency lockfiles, multi-stage container builds, read-only volume mounts
