"""Speech-to-text for the audio track of a video/audio file (TXT output), using WhisperX
(faster-whisper) from Tools_Central. No Qt imports; the engine runs as an external process.
Language is detected automatically. Used only when no subtitle transcript exists."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional

DEFAULT_MODEL = "small"


class TranscribeError(RuntimeError):
    pass


def build_command(exe, media: Path, work_dir: Path, model: str = DEFAULT_MODEL,
                  language: str = "", device: str = "") -> list:
    """whisperx command line: TXT only, no word alignment (faster, no extra model download)."""
    cmd = [str(exe), str(media), "--model", model, "--compute_type", "int8",
           "--output_format", "txt", "--output_dir", str(work_dir), "--no_align"]
    if language:
        cmd += ["--language", language]
    if device:
        cmd += ["--device", device]
    return cmd


def build_env(ffmpeg_dir: Optional[Path], models_dir: Optional[Path]) -> dict:
    env = os.environ.copy()
    if ffmpeg_dir:
        env["PATH"] = str(ffmpeg_dir) + os.pathsep + env.get("PATH", "")
    if models_dir:
        env["HF_HOME"] = str(models_dir)
    env["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def transcribe(exe, media: Path, out_txt: Path, ffmpeg_dir: Optional[Path] = None,
               models_dir: Optional[Path] = None, model: str = "", language: str = "",
               register: Optional[Callable] = None) -> Path:
    """Write the transcript of `media` to `out_txt` (never overwrites an existing file).
    `register(proc)` lets the caller terminate the process on shutdown. Raises TranscribeError."""
    media, out_txt = Path(media), Path(out_txt)
    if not media.is_file():
        raise TranscribeError("The media file was not found.")
    if out_txt.exists():
        raise TranscribeError("A transcript with this name already exists.")
    model = model or os.environ.get("YEAL_WHISPER_MODEL", DEFAULT_MODEL)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    env = build_env(ffmpeg_dir, models_dir)
    with tempfile.TemporaryDirectory(prefix="yeal_tr_") as tmp:
        work = Path(tmp)
        last_err = ""
        for device in ("", "cpu"):      # automatic first; fall back to CPU if CUDA is unusable
            cmd = build_command(exe, media, work, model, language, device)
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                                        text=True, encoding="utf-8", errors="replace", creationflags=flags)
            except OSError as exc:
                raise TranscribeError(f"WhisperX could not be started: {exc}") from exc
            if register:
                register(proc)
            _out, err = proc.communicate()
            found = sorted(work.glob("*.txt"))
            if proc.returncode == 0 and found:
                out_txt.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(found[0], out_txt)
                return out_txt
            last_err = (err or "").strip().splitlines()[-1][:300] if (err or "").strip() else ""
            if "cuda" not in (err or "").lower() and "cudnn" not in (err or "").lower():
                break
        raise TranscribeError(last_err or "Speech recognition failed.")
