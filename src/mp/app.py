from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from features import Features, extract_cached, is_analyzed
from library import Track, get_album_art, scan_library
from render import cached_video_path, render_for_track
from viz import plot_chroma, plot_rms_with_beats

DEFAULT_MUSIC_FOLDER = os.environ.get("MUSIC_FOLDER", "~/Music")

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


@st.cache_data(show_spinner=False)
def cached_video(path: str, mtime: float) -> str | None:
    p = cached_video_path(path)
    return str(p) if p else None


def filter_tracks(tracks: list[Track], query: str) -> list[Track]:
    if not query:
        return tracks
    q = query.lower()
    return [
        t for t in tracks
        if q in t.title.lower() or q in t.artist.lower() or q in t.album.lower()
    ]


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


def go_to(path: str | None) -> None:
    if path is not None:
        st.session_state.current_path = path


def prev_next_buttons(track: Track, visible: list[Track]) -> None:
    paths = [t.path for t in visible]
    try:
        i = paths.index(track.path)
    except ValueError:
        i = -1
    prev_path = paths[i - 1] if i > 0 else None
    next_path = paths[i + 1] if 0 <= i < len(paths) - 1 else None

    prev_col, next_col = st.columns(2)
    with prev_col:
        st.button(
            "⏮ Previous",
            width="stretch",
            disabled=prev_path is None,
            on_click=go_to,
            args=(prev_path,),
            key=f"prev_{track.path}",
        )
    with next_col:
        st.button(
            "Next ⏭",
            width="stretch",
            disabled=next_path is None,
            on_click=go_to,
            args=(next_path,),
            key=f"next_{track.path}",
        )


st.title("mp")
st.caption("a music player + visualizer")

with st.sidebar:
    st.header("Library")
    folder = st.text_input(
        "Music folder",
        value=DEFAULT_MUSIC_FOLDER,
        key="music_folder",
    )
    if st.button("Rescan", width="stretch"):
        cached_scan.clear()
        st.rerun()
    search = st.text_input(
        "Search",
        placeholder="title, artist, album…",
        key="search",
    )

all_tracks = cached_scan(folder)

if not all_tracks:
    st.info(
        "No audio files found. Point the sidebar at a folder containing "
        "`.mp3, .flac, .wav, .m4a, .ogg, .opus, .aac` files."
    )
    st.stop()

visible_tracks = filter_tracks(all_tracks, search)

with st.sidebar:
    if search:
        st.caption(f"{len(visible_tracks)} of {len(all_tracks)} tracks match")
    else:
        st.metric("Tracks", len(all_tracks))

nowplaying = st.container()
st.divider()

if not visible_tracks:
    st.info(f"No tracks match '{search}'.")
    df = pd.DataFrame(columns=["Title", "Artist", "Album", "Duration"])
else:
    df = tracks_to_df(visible_tracks)

event = st.dataframe(
    df.drop(columns=["_path"]) if "_path" in df.columns else df,
    selection_mode="single-row",
    on_select="rerun",
    width="stretch",
    hide_index=True,
    key="library_table",
)

selected = tuple(event.selection.rows) if event.selection else ()
prev_selected = st.session_state.get("_prev_table_sel", ())
if selected and selected != prev_selected and visible_tracks:
    st.session_state.current_path = visible_tracks[selected[0]].path
st.session_state._prev_table_sel = selected

current_path = st.session_state.get("current_path")
track: Track | None = None
if current_path:
    track = next((t for t in all_tracks if t.path == current_path), None)
    if track is None:
        st.session_state.current_path = None

with nowplaying:
    if track is None:
        st.caption("Pick a track below to start.")
    else:
        track_path_obj = Path(track.path)
        if not track_path_obj.exists():
            st.error(f"Track file not found: `{track.path}`")
            st.stop()
        mtime = track_path_obj.stat().st_mtime
        analyzed = cached_is_analyzed(track.path, mtime)
        feat: Features | None = cached_features(track.path, mtime) if analyzed else None
        video_str = cached_video(track.path, mtime) if analyzed else None

        if video_str is not None:
            st.subheader(track.display_title)
            st.caption(f"{track.artist} — {track.album}")
            st.video(video_str)
            prev_next_buttons(track, visible_tracks)
        else:
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
                st.caption(f"Duration: {track.duration_str}")
                st.audio(track.path)
                prev_next_buttons(track, visible_tracks)

        st.divider()
        st.markdown("##### Visualization")

        if not analyzed:
            st.caption(
                "Analyze this track to extract beats + spectral features, "
                "then render a generative MP4."
            )
            if st.button("Analyze track", type="primary", key=f"analyze_{track.path}"):
                with st.spinner("Extracting features… (5–15s the first time)"):
                    try:
                        cached_features(track.path, mtime)
                        cached_is_analyzed.clear()
                    except Exception as e:
                        st.error(f"Couldn't analyze this file: {e}")
                        st.stop()
                st.rerun()
        else:
            assert feat is not None
            m1, m2, m3 = st.columns(3)
            m1.metric("Tempo", f"{feat.tempo_bpm:.1f} BPM")
            m2.metric("Beats", len(feat.beat_times))
            m3.metric("Frames", len(feat.onset_env))

            if video_str is None:
                if st.button("Render visualization", type="primary", key=f"render_{track.path}"):
                    secs_estimate = max(15, int(feat.duration_s * 0.3))
                    with st.spinner(f"Rendering generative video… (~{secs_estimate}s)"):
                        try:
                            render_for_track(track.path, feat)
                            cached_video.clear()
                        except Exception as e:
                            st.error(f"Render failed: {e}")
                            st.stop()
                    st.rerun()

            with st.expander("Show RMS + beats"):
                show_fig(plot_rms_with_beats(feat))
            with st.expander("Show chroma"):
                show_fig(plot_chroma(feat))
