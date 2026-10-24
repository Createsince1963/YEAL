"""Find extra drives so the app can offer them as download target. No Qt imports.

Windows: a cheap drive-letter check (GetLogicalDrives) tells when something changed; only then every
fixed or removable volume except the system drive is listed (Win32 API, no PowerShell). This finds USB
sticks, USB SSDs behind UASP bridges and secondary internal disks alike, whatever bus type Windows
reports. Pseudo drives (virtual CD-like volumes such as the 16 MB "Ugreen Driver", empty card readers)
are skipped by a minimum size. Linux: mounts below /media, /run/media, /mnt.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path
from typing import List, Optional

_SAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Volumes smaller than this are driver CD-ROMs / empty readers, not places to store downloads.
MIN_DRIVE_BYTES = 1 << 30


def drive_mask() -> int:
    """Cheap fingerprint of the mounted drives (changes when one is plugged in or removed)."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            return int(ctypes.windll.kernel32.GetLogicalDrives())  # type: ignore[attr-defined]
        except (OSError, AttributeError):
            return 0
    return len(_linux_mounts())


def clean_folder_name(name: str, default: str = "Yeal") -> str:
    name = _SAFE.sub("_", (name or "").strip()).strip(" .")[:60]
    return name or default


def drive_id(root: str, label: str, total: int) -> str:
    return f"{root}|{label}|{total}"


def _entry(root: str, label: str) -> Optional[dict]:
    try:
        usage = shutil.disk_usage(root)
    except OSError:
        return None
    return {"root": root, "label": label or "", "free": usage.free, "total": usage.total,
            "id": drive_id(root, label or "", usage.total)}


def _linux_mounts() -> List[str]:
    out = []
    try:
        for line in Path("/proc/mounts").read_text().splitlines():
            mp = line.split()[1].replace("\\040", " ")
            if mp.startswith(("/media/", "/run/media/", "/mnt/")) and os.path.isdir(mp):
                out.append(mp)
    except OSError:
        pass
    return out


def user_downloads_dir() -> Path:
    """The user's Windows Downloads folder (known folder, also when it was moved), else ~/Downloads."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            import uuid
            from ctypes import wintypes

            class _GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

            u = uuid.UUID("374DE290-123F-4565-9164-39C4925E467B")      # FOLDERID_Downloads
            guid = _GUID(u.time_low, u.time_mid, u.time_hi_version, (ctypes.c_ubyte * 8)(*u.bytes[8:]))
            fn = ctypes.windll.shell32.SHGetKnownFolderPath          # type: ignore[attr-defined]
            fn.argtypes = [ctypes.POINTER(_GUID), wintypes.DWORD, wintypes.HANDLE,
                           ctypes.POINTER(ctypes.c_wchar_p)]
            out = ctypes.c_wchar_p()
            hr = fn(ctypes.byref(guid), 0, None, ctypes.byref(out))
            if hr == 0 and out.value:
                path = out.value
                ctypes.windll.ole32.CoTaskMemFree(ctypes.cast(out, ctypes.c_void_p))  # type: ignore[attr-defined]
                return Path(path)
        except (OSError, AttributeError, ValueError):
            pass
    return Path.home() / "Downloads"


def _windows_drives() -> List[dict]:
    """All fixed/removable volumes except the system drive (USB, UASP/SCSI/SATA enclosures, 2nd disks)."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32                            # type: ignore[attr-defined]
        mask = int(kernel32.GetLogicalDrives())
    except (OSError, AttributeError):
        return []
    system = (os.environ.get("SystemDrive") or "C:").upper().rstrip("\\/")
    found = []
    old_mode = kernel32.SetErrorMode(1)      # SEM_FAILCRITICALERRORS: no "insert a disk" popups
    try:
        for i in range(26):
            if not mask >> i & 1:
                continue
            letter = chr(ord("A") + i)
            root = f"{letter}:\\"
            if f"{letter}:" == system:
                continue
            if kernel32.GetDriveTypeW(root) not in (2, 3):           # 2 removable, 3 fixed
                continue
            label = ctypes.create_unicode_buffer(261)
            if not kernel32.GetVolumeInformationW(root, label, 261, None, None, None, None, 0):
                continue                                              # not ready (empty reader)
            e = _entry(root, label.value.strip())
            if e and e["total"] >= MIN_DRIVE_BYTES:
                found.append(e)
    finally:
        kernel32.SetErrorMode(old_mode)
    return found


def external_drives() -> List[dict]:
    """Writable extra drives: [{root, label, free, total, id}]."""
    if sys.platform.startswith("win"):
        found = _windows_drives()
    elif sys.platform.startswith("linux") and "ANDROID_ARGUMENT" not in os.environ:
        found = [e for e in (_entry(mp, Path(mp).name) for mp in _linux_mounts()) if e]
    else:
        found = []
    return [d for d in found if d["total"] >= MIN_DRIVE_BYTES and os.access(d["root"], os.W_OK)]
