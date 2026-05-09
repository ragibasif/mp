# syntax=docker/dockerfile:1.7

# ---- Build stage: install dependencies into a self-contained .venv ----
FROM python:3.13-slim AS builder

WORKDIR /app

# uv: fast, lockfile-driven dependency installer.
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

# Build essentials in case any source-only wheels appear during resolution.
# Most scientific stack (numpy, scipy, numba, llvmlite) ship binary wheels
# for linux/amd64 and linux/arm64, so this rarely actually compiles anything.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

# ---- Runtime stage: copy in venv + source, drop apt + builder ----
FROM python:3.13-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY src ./src
COPY .streamlit ./.streamlit

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    MUSIC_FOLDER=/music \
    MPLCONFIGDIR=/tmp/matplotlib \
    NUMBA_CACHE_DIR=/tmp/numba

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health').read() == b'ok' else 1)"

CMD ["streamlit", "run", "src/mp/app.py"]
