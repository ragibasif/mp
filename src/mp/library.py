from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from mutagen import File as MutagenFile

AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".opus", ".aac"}


@dataclass(frozen=True, slots=True)
class Track:
    path: str
    title: str
    artist: str
    album: str
    duration_s: float | None

    @property
    def display_title(self) -> str:
        return self.title or Path(self.path).stem

    @property
    def duration_str(self) -> str:
        if self.duration_s is None:
            return "—"
        m, s = divmod(int(self.duration_s), 60)
        return f"{m}:{s:02d}"


def _iter_audio_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            yield p


def _read_metadata(path: Path) -> Track:
    title = path.stem
    artist = "Unknown Artist"
    album = "Unknown Album"
    duration: float | None = None
    try:
        meta = MutagenFile(path, easy=True)
        if meta is not None:
            tags = meta.tags or {}
            title = (tags.get("title") or [title])[0]
            artist = (tags.get("artist") or [artist])[0]
            album = (tags.get("album") or [album])[0]
            if meta.info is not None and getattr(meta.info, "length", None):
                duration = float(meta.info.length)
    except Exception:
        pass
    return Track(str(path), title, artist, album, duration)


def scan_library(folder: str) -> list[Track]:
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        return []
    return [_read_metadata(p) for p in sorted(_iter_audio_files(root))]


def get_album_art(path: str) -> bytes | None:
    """Return embedded album-art bytes, or None.

    Handles three container conventions:
      - ID3v2 (MP3) APIC frames
      - FLAC .pictures list
      - MP4/M4A 'covr' atom
    """
    try:
        meta = MutagenFile(path)
        if meta is None:
            return None

        if hasattr(meta, "pictures") and meta.pictures:
            return meta.pictures[0].data

        tags = getattr(meta, "tags", None)
        if tags is None:
            return None

        for key in list(tags.keys()):
            if key.startswith("APIC"):
                return tags[key].data

        covr = tags.get("covr") if hasattr(tags, "get") else None
        if covr:
            return bytes(covr[0])
    except Exception:
        pass
    return None
