"""MP3 tags (ID3v2.4): fill them from the video description, read and edit them. No Qt imports.

Descriptions of music uploads often list the track data, e.g.

    Mood: Warm | Hypnotic | Chill
    Genre: Arabic Deep House | Ethnic House
    Ideal For: Relaxation | Night Drive
    #arabicdeephouse #ethnichouse

`build_tag_data` turns that (plus the yt-dlp fields) into a `TagData` proposal, `auto_fill` merges it into a
finished MP3 without wiping what is already there, `read_tags` / `write_tags` serve the editor dialog.
mutagen is optional: without it downloads work as before, only the extra tags are skipped.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Optional

try:
    from mutagen import MutagenError
    from mutagen.id3 import COMM, ID3, TALB, TCON, TDRC, TIT2, TMOO, TPE1, TXXX, ID3NoHeaderError
    AVAILABLE = True
except ImportError:   # pragma: no cover - depends on the install
    AVAILABLE = False
    MutagenError = OSError   # type: ignore[misc,assignment]


@dataclass
class TagData:
    title: str = ""
    artist: str = ""
    album: str = ""
    genre: str = ""          # several genres are joined with "; "
    year: str = ""
    mood: str = ""
    comment: str = ""        # e.g. "Ideal for: Relaxation, Night Drive"
    keywords: str = ""       # hashtags / video tags, comma separated
    source_url: str = ""


EDITABLE = ("title", "artist", "album", "genre", "year", "mood", "keywords", "comment")
_FIELDS = {f.name for f in fields(TagData)}


# ---- description parsing ------------------------------------------------------------------
_KEY_ALIASES = {
    "genre": "genre", "genres": "genre",
    "mood": "mood", "moods": "mood",
    "ideal for": "ideal_for", "perfect for": "ideal_for", "best for": "ideal_for",
}
# optional emoji/bullets in front, then "Key: value"
_LINE = re.compile(r"^\W*?([A-Za-z][A-Za-z ]{1,20}?)\s*:\s*(.+)$")
_HASHTAG = re.compile(r"(?<![\w&])#([^\W\d][\w\-]*)", re.UNICODE)
_SEP = re.compile(r"\s*(?:[|•·;,]|\s/\s)\s*")


def _split_values(text: str) -> list:
    return [v.strip() for v in _SEP.split(text) if v.strip()]


def parse_description(description: str) -> dict:
    """Genre, mood, 'ideal for' values and hashtags found in a video description."""
    result: dict = {"genre": [], "mood": [], "ideal_for": [], "hashtags": []}
    for raw in (description or "").splitlines():
        m = _LINE.match(raw.strip())
        if m:
            key = _KEY_ALIASES.get(m.group(1).strip().lower())
            if key:
                result[key].extend(_split_values(m.group(2)))
    for key in ("genre", "mood", "ideal_for"):
        result[key] = list(dict.fromkeys(result[key]))
    result["hashtags"] = list(dict.fromkeys(_HASHTAG.findall(description or "")))
    return result


def _clean_year(value: str) -> str:
    m = re.match(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", (value or "").strip())
    return m.group(0) if m else ""


def build_tag_data(info: dict) -> TagData:
    """Tag proposal from a yt-dlp info dict (the description wins for genre, mood and keywords)."""
    parsed = parse_description(str(info.get("description") or ""))
    keywords = parsed["hashtags"] or [str(t) for t in info.get("tags") or []]
    genre = "; ".join(parsed["genre"]) or str(info.get("genre") or "")
    year = str(info.get("release_year") or "") or str(info.get("upload_date") or "")[:4]
    return TagData(
        title=str(info.get("track") or info.get("title") or ""),
        artist=str(info.get("artist") or info.get("uploader") or info.get("channel") or ""),
        album=str(info.get("album") or info.get("playlist_title") or ""),
        genre=genre,
        year=_clean_year(year),
        mood=", ".join(parsed["mood"]),
        comment=("Ideal for: " + ", ".join(parsed["ideal_for"])) if parsed["ideal_for"] else "",
        keywords=", ".join(keywords),
        source_url=str(info.get("webpage_url") or info.get("original_url") or ""),
    )


def merge(existing: TagData, proposal: TagData) -> TagData:
    """Title, artist and album stay as they are when set; the other fields take the proposal when it has a value."""
    out = TagData(**asdict(existing))
    for name in _FIELDS:
        new, old = getattr(proposal, name), getattr(existing, name)
        keep_old = name in ("title", "artist", "album") and old.strip()
        setattr(out, name, old if keep_old or not new.strip() else new)
    return out


# ---- reading and writing ----------------------------------------------------------------
def read_tags(path) -> TagData:
    """Tags of an MP3 (empty TagData when it has none). Raises OSError / MutagenError on a broken file."""
    try:
        tags = ID3(str(path))
    except ID3NoHeaderError:
        return TagData()

    def text(frame: str) -> str:
        return "; ".join(str(t) for t in tags[frame].text) if frame in tags else ""

    def extra(desc: str) -> str:
        f = tags.get(f"TXXX:{desc}")
        return "; ".join(str(t) for t in f.text) if f else ""

    comments = tags.getall("COMM")
    comment = next((c for c in comments if not c.desc), comments[0] if comments else None)
    return TagData(
        title=text("TIT2"), artist=text("TPE1"), album=text("TALB"), genre=text("TCON"),
        year=_clean_year(text("TDRC")), mood=text("TMOO"),
        comment=str(comment.text[0]) if comment is not None and comment.text else "",
        keywords=extra("KEYWORDS"), source_url=extra("SOURCE_URL"))


def write_tags(path, data: TagData) -> None:
    """Write `data` into the MP3; an empty field removes its tag. Cover and lyrics are left alone."""
    path = str(path)
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()          # file without tags: save() below writes a new tag block in front of the audio

    def put(frame_cls, frame_id: str, value: str, split: bool = False) -> None:
        tags.delall(frame_id)
        value = (value or "").strip()
        if value:
            tags.add(frame_cls(encoding=3, text=[v.strip() for v in value.split(";") if v.strip()] if split else [value]))

    put(TIT2, "TIT2", data.title)
    put(TPE1, "TPE1", data.artist)
    put(TALB, "TALB", data.album)
    put(TCON, "TCON", data.genre, split=True)
    put(TDRC, "TDRC", _clean_year(data.year))
    put(TMOO, "TMOO", data.mood)

    for frame in tags.getall("COMM"):          # the plain comment only; named comments stay
        if not frame.desc:
            tags.delall(frame.HashKey)
    if (data.comment or "").strip():
        tags.add(COMM(encoding=3, lang="eng", desc="", text=[data.comment.strip()]))

    for desc, value in (("KEYWORDS", data.keywords), ("SOURCE_URL", data.source_url)):
        tags.delall(f"TXXX:{desc}")
        if (value or "").strip():
            tags.add(TXXX(encoding=3, desc=desc, text=[value.strip()]))
    tags.save(path, v2_version=4)


def auto_fill(path, info: dict) -> Optional[TagData]:
    """Fill the tags of a finished MP3 from the yt-dlp info. Returns what was written, None if skipped/failed."""
    if not AVAILABLE or not Path(path).is_file():
        return None
    try:
        data = merge(read_tags(path), build_tag_data(info))
        write_tags(path, data)
        return data
    except (OSError, MutagenError):
        return None


def from_dict(raw: dict, base: Optional[TagData] = None) -> TagData:
    """TagData from an untrusted dict (the editor): only the editable fields are taken, as text."""
    data = TagData(**asdict(base)) if base else TagData()
    for name in EDITABLE:
        if name in (raw or {}):
            setattr(data, name, str(raw[name] if raw[name] is not None else "")[:5000])
    return data
