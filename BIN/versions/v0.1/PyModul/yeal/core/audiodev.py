"""Audio outputs of this computer (Windows shows Bluetooth headphones, HDMI monitors, wired speakers all as outputs).

No Qt in here: the Qt side (ui/backend.py) hands in the descriptions; this module only decides what kind of device it is
(for the icon and the order) and builds the list shown in the Speaker planet.
"""
from __future__ import annotations

from typing import List

_HEADPHONES = ("kopfh", "headphone", "headset", "hands-free", "handsfree", "airpods", "buds", "wh-1000", "wf-1000",
               "earbud", "earphone", "bluetooth")
_MONITORS = ("hdmi", "displayport", "display", "nvidia high definition", "monitor", "tv")


def output_kind(description: str) -> str:
    """'headphones' (Bluetooth / wired headphones and headsets), 'monitor' (HDMI / DisplayPort audio) or 'speaker'."""
    text = (description or "").lower()
    if any(word in text for word in _HEADPHONES):
        return "headphones"
    if any(word in text for word in _MONITORS):
        return "monitor"
    return "speaker"


def describe_outputs(devices: List[dict], selected_id: str = "") -> List[dict]:
    """devices: [{'id', 'description', 'isDefault'}] -> [{'id', 'name', 'kind', 'isDefault', 'selected'}].
    The device chosen in the settings is 'selected'; without a (still existing) choice the system default is."""
    ids = {d["id"] for d in devices}
    chosen = selected_id if selected_id in ids else ""
    out = []
    for d in devices:
        out.append({"id": d["id"], "name": d["description"] or d["id"], "kind": output_kind(d["description"]),
                    "isDefault": bool(d.get("isDefault")),
                    "selected": (d["id"] == chosen) if chosen else bool(d.get("isDefault"))})
    return out
