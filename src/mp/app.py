from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from features import Features, extract_cached, is_analyzed
from library import Track, get_album_art, scan_library
from viz import plot_chroma, plot_rms_with_beats

st.set_page_config(
    page_title="mp",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner="Scanning library…")
def cached_scan(folder: str) -> list[Track]:
    return scan_library(folder)


@st.cache_data(show_spinner=False)
def cached_art(path: str) -> bytes | None:
    return get_album_art(path)


@st.cache_data(show_spinner=False)
def cached_features(path: str, mtime: float) -> Features:
    return extract_cached(path)


@st.cache_data(show_spinner=False)
def cached_is_analyzed(path: str, mtime: float) -> bool:
    return is_analyzed(path)


def tracks_to_df(tracks: list[Track]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Title": t.display_title,
                "Artist": t.artist,
                "Album": t.album,
                "Duration": t.duration_str,
                "_path": t.path,
            }
            for t in tracks
        ]
    )


def show_fig(fig) -> None:
    st.pyplot(fig)
    plt.close(fig)


st.title("mp")
st.caption("a music player + visualizer")

with st.sidebar:
    st.header("Library")
    folder = st.text_input("Music folder", value="~/Music", key="music_folder")
    if st.button("Rescan", width="stretch"):
        cached_scan.clear()
        st.rerun()

tracks = cached_scan(folder)

if not tracks:
    st.info(
        "No audio files found. Point the sidebar at a folder containing "
        "`.mp3, .flac, .wav, .m4a, .ogg, .opus, .aac` files."
    )
    st.stop()

with st.sidebar:
    st.metric("Tracks", len(tracks))

# Pre-allocate slots so now-playing renders ABOVE the table
# even though selection events come from the table below.
nowplaying = st.container()
st.divider()

df = tracks_to_df(tracks)
event = st.dataframe(
    df.drop(columns=["_path"]),
    selection_mode="single-row",
    on_select="rerun",
    width="stretch",
    hide_index=True,
    key="library_table",
)

# Selection-change guard: only react when the dataframe selection actually
# changes. Without this, prev/next buttons get stomped on every rerun.
selected = tuple(event.selection.rows) if event.selection else ()
prev_selected = st.session_state.get("_prev_table_sel", ())
if selected and selected != prev_selected:
    st.session_state.current_index = int(selected[0])
st.session_state._prev_table_sel = selected

# Clamp index in case the library shrank.
idx: int | None = st.session_state.get("current_index")
if idx is not None and idx >= len(tracks):
    idx = None
    st.session_state.current_index = None


def _go_to(new_idx: int) -> None:
    st.session_state.current_index = max(0, min(len(tracks) - 1, new_idx))


with nowplaying:
    if idx is None:
        st.caption("Pick a track below to start.")
    else:
        track = tracks[idx]
        art_col, info_col = st.columns([1, 4], vertical_alignment="center")

        with art_col:
            art = cached_art(track.path)
            if art:
                st.image(art, width="stretch")
            else:
                st.markdown(
                    "<div style='aspect-ratio:1;background:#222;border-radius:8px;"
                    "display:flex;align-items:center;justify-content:center;"
                    "font-size:3rem;'>🎵</div>",
                    unsafe_allow_html=True,
                )

        with info_col:
            st.subheader(track.display_title)
            st.caption(f"{track.artist} — {track.album}")
            st.caption(f"Duration: {track.duration_str}  ·  {idx + 1} / {len(tracks)}")
            st.audio(track.path)

            prev_col, next_col = st.columns(2)
            with prev_col:
                st.button(
                    "⏮ Previous",
                    width="stretch",
                    disabled=idx == 0,
                    on_click=_go_to,
                    args=(idx - 1,),
                )
            with next_col:
                st.button(
                    "Next ⏭",
                    width="stretch",
                    disabled=idx >= len(tracks) - 1,
                    on_click=_go_to,
                    args=(idx + 1,),
                )

        st.divider()
        st.markdown("##### Audio analysis")

        track_path_obj = Path(track.path)
        mtime = track_path_obj.stat().st_mtime if track_path_obj.exists() else 0.0

        if cached_is_analyzed(track.path, mtime):
            feat = cached_features(track.path, mtime)
            m1, m2, m3 = st.columns(3)
            m1.metric("Tempo", f"{feat.tempo_bpm:.1f} BPM")
            m2.metric("Beats", len(feat.beat_times))
            m3.metric("Frames", len(feat.onset_env))

            show_fig(plot_rms_with_beats(feat))
            with st.expander("Show chroma"):
                show_fig(plot_chroma(feat))
        else:
            st.caption(
                "This track hasn't been analyzed yet. Extracting beats + spectral "
                "features now will unlock generative visuals in Phase 4."
            )
            if st.button("Analyze track", type="primary", key=f"analyze_{idx}"):
                with st.spinner("Extracting features… (5–15s the first time)"):
                    cached_features(track.path, mtime)
                    cached_is_analyzed.clear()
                st.rerun()
