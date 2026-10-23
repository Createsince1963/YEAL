"""Turn the tracks split from one long file (DJ mix, album rip) into an album folder:
ID3/MP4 tags (album, artist, track n/N) and a playlist file in track order. No Qt imports."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional

AUDIO_EXT = {".mp3", ".m4a", ".opus", ".flac", ".ogg", ".webm", ".aac"}
_NUM = re.compile(r"^(\d+)\s*-\s*")


def find_album_dir(media_dir: Path, video_id: str) -> Optional[Path]:
    """Folder created by the chapter split: `<title> [<id>]` next to the full file."""
    try:
        for p in sorted(Path(media_dir).iterdir()):
            if p.is_dir() and p.name.endswith(f"[{video_id}]"):
                return p
    except OSError:
        pass
    return None


def tracks_in(folder: Path) -> List[Path]:
    return sorted(p for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXT)


def tag_track(ffmpeg: str, path: Path, album: str, artist: str, number: int, total: int, title: str) -> bool:
    """Rewrite tags without re-encoding; returns False (file untouched) on any failure."""
    tmp = path.with_name(path.stem + ".tagged" + path.suffix)
    cmd = [str(ffmpeg), "-v", "error", "-y", "-i", str(path), "-map", "0", "-c", "copy",
           "-metadata", f"album={album}", "-metadata", f"artist={artist}",
           "-metadata", f"album_artist={artist}", "-metadata", f"title={title}",
           "-metadata", f"track={number}/{total}", str(tmp)]
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(cmd, check=True, capture_output=True, timeout=300, creationflags=flags)
        os.replace(tmp, path)
        return True
    except (OSError, subprocess.SubprocessError):
        try:
            tmp.unlink()
        except OSError:
            pass
        return False


def write_playlist(folder: Path, name: str, tracks: List[Path], chapters: list) -> Path:
    """UTF-8 extended M3U with relative paths, in track order. VLC and Windows players are picky: the encoding is
    declared (#EXTENC), lines end with CRLF, and the title line has no characters that confuse the parser."""
    lines = ["#EXTM3U", "#EXTENC:UTF-8", f"#PLAYLIST:{_one_line(name)}"]
    for i, t in enumerate(tracks):
        ch = chapters[i] if i < len(chapters) else {}
        secs = int(round(float(ch.get("end_time", 0) or 0) - float(ch.get("start_time", 0) or 0)))
        title = track_title(chapters, i + 1, t)
        lines += [f"#EXTINF:{secs if secs > 0 else -1},{_one_line(title)}", t.name]
    safe = re.sub(r'[<>:"/\\|?*]', "_", name)[:100] or "playlist"
    out = Path(folder) / f"{safe}.m3u8"
    with open(out, "w", encoding="utf-8", newline="") as fh:
        fh.write("\r\n".join(lines) + "\r\n")
    return out


def _one_line(text: str) -> str:
    return re.sub(r"[\r\n]+", " ", str(text)).strip()


def track_title(chapters: list, number: int, path: Path) -> str:
    """Name of track `number` from the tracklist (chapter title); falls back to the file name."""
    if 0 < number <= len(chapters):
        title = re.sub(r"\s+", " ", str(chapters[number - 1].get("title") or "")).strip()
        if title:
            return title
    return _NUM.sub("", path.stem)


def finish(ffmpeg: Optional[str], folder: Path, album: str, artist: str, chapters: list) -> int:
    """Tag the tracks and write the playlist. Returns the number of tracks."""
    tracks = tracks_in(folder)
    if not tracks:
        return 0
    if ffmpeg:
        for i, t in enumerate(tracks, 1):
            tag_track(ffmpeg, t, album, artist, i, len(tracks), track_title(chapters, i, t))
    write_playlist(folder, album, tracks, chapters)
    return len(tracks)
