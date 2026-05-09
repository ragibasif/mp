from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import streamlit as st

from library import Track, scan_library

st.set_page_config(
    page_title="mp",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner="Scanning library…")
def cached_scan(folder: str) -> list[Track]:
    return scan_library(folder)


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


st.title("mp")
st.caption("a music player + visualizer")

with st.sidebar:
    st.header("Library")
    folder = st.text_input("Music folder", value="~/Music", key="music_folder")
    if st.button("Rescan", use_container_width=True):
        cached_scan.clear()
        st.rerun()

tracks = cached_scan(folder)

if not tracks:
    st.info(
        "No audio files found. Point the sidebar at a folder containing "
        f"`{', '.join(sorted(['.mp3', '.flac', '.wav', '.m4a', '.ogg', '.opus', '.aac']))}` files."
    )
    st.stop()

with st.sidebar:
    st.metric("Tracks", len(tracks))

df = tracks_to_df(tracks)

event = st.dataframe(
    df.drop(columns=["_path"]),
    selection_mode="single-row",
    on_select="rerun",
    use_container_width=True,
    hide_index=True,
)

selected_rows = event.selection.rows if event.selection else []
if selected_rows:
    st.session_state.current_track = df.iloc[selected_rows[0]]["_path"]

current = st.session_state.get("current_track")
if current:
    st.divider()
    st.subheader("Now selected")
    st.code(current, language="text")
    st.caption("Playback wires up in Phase 2.")
