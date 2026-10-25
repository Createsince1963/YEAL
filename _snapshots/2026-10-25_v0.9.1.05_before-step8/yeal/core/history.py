"""Remember finished downloads between sessions (no Qt imports).

History file: `history.json` in the data folder. Only finished jobs are kept (newest 500). Used for the
date-grouped list and to ask before downloading the same video twice.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
from dataclasses import asdict, fields
from pathlib import Path
from typing import List, Optional

from .models import DownloadJob, DownloadOptions, JobState

MAX_ITEMS = 500
_YT = re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|live/|embed/))([\w-]{6,})", re.I)
_LIST = re.compile(r"[?&]list=([\w-]+)", re.I)


def video_key(url: str) -> str:
    """Stable identity of a link: the YouTube video id, else the link without fragment/trailing slash."""
    url = (url or "").strip()
    m = _YT.search(url)
    if m:
        return "yt:" + m.group(1)
    m = _LIST.search(url)
    if m and "playlist" in url:
        return "list:" + m.group(1)
    return url.split("#", 1)[0].rstrip("/").lower()


def section_label(created: float, now: Optional[_dt.datetime] = None) -> str:
    """Group name of the list: Today, Yesterday, a weekday of this week, 'Week NN', or the year."""
    now = now or _dt.datetime.now()
    day = _dt.datetime.fromtimestamp(created or 0)
    delta = (now.date() - day.date()).days
    if delta <= 0:
        return "Today"
    if delta == 1:
        return "Yesterday"
    if delta < 7:
        return day.strftime("%A, %d %b")
    if day.year == now.year:
        return "Week %02d" % day.isocalendar()[1]
    return str(day.year)


def _job_to_dict(job: DownloadJob) -> dict:
    return {"url": job.url, "title": job.title, "state": job.state.value, "error": job.error,
            "error_detail": job.error_detail, "note": job.note, "filename": job.filename,
            "thumbnail": job.thumbnail, "uploader": job.uploader, "duration": job.duration,
            "size": job.size, "created": job.created, "saved_description": job.saved_description,
            "saved_transcript": job.saved_transcript, "saved_lyrics": job.saved_lyrics,
            "options": asdict(job.options)}


def save(path: Path, jobs: List[DownloadJob]) -> None:
    keep = [j for j in jobs if j.state.finished]
    keep.sort(key=lambda j: j.created, reverse=True)
    data = [_job_to_dict(j) for j in keep[:MAX_ITEMS]]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"v": 1, "jobs": data}), encoding="utf-8")
    os.replace(tmp, path)


def load(path: Path) -> List[DownloadJob]:
    """Oldest first (so that inserting them one by one leaves the newest on top)."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        items = raw["jobs"]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    known = {f.name for f in fields(DownloadOptions)}
    out: List[DownloadJob] = []
    for d in items if isinstance(items, list) else []:
        try:
            state = JobState(d.get("state"))
            if not state.finished:
                continue
            opts = DownloadOptions(**{k: v for k, v in (d.get("options") or {}).items() if k in known}).normalized()
            job = DownloadJob(0, str(d["url"]), opts)
            job.state = state
            for key in ("title", "error", "error_detail", "note", "filename", "thumbnail", "uploader",
                        "duration", "size", "saved_lyrics"):
                setattr(job, key, str(d.get(key) or ""))
            job.saved_description = bool(d.get("saved_description"))
            job.saved_transcript = bool(d.get("saved_transcript"))
            job.created = float(d.get("created") or 0)
            if state is JobState.DONE:
                job.progress = job.dl_progress = job.pp_progress = 1.0
            out.append(job)
        except (ValueError, KeyError, TypeError):
            continue
    out.sort(key=lambda j: j.created)
    return out


def find_done(jobs: List[DownloadJob], url: str, mode: str) -> Optional[DownloadJob]:
    """Newest finished download of this link in the same mode whose file still exists."""
    key = video_key(url)
    best = None
    for j in jobs:
        if j.state is JobState.DONE and j.options.mode == mode and video_key(j.url) == key \
                and j.filename and Path(j.filename).exists():
            if best is None or j.created > best.created:
                best = j
    return best
