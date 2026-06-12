"""Loading and resolving the cue sidecar file.

A cue marks the start of a song section. A cue is the "active" section from its
``time`` until the next cue's ``time``. Times accept ``m:ss``, ``mm:ss``,
``h:mm:ss`` or a raw number of seconds.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Cue:
    time: float  # seconds from start
    label: str
    art: str = ""


@dataclass
class CueSheet:
    cues: list[Cue]
    show_countdown: bool = True

    @property
    def starts(self) -> list[float]:
        return [c.time for c in self.cues]

    def index_at(self, position: float) -> int:
        """Index of the active cue at ``position`` (-1 before the first cue)."""
        return bisect.bisect_right(self.starts, position) - 1

    def current(self, position: float) -> Cue | None:
        i = self.index_at(position)
        return self.cues[i] if i >= 0 else None

    def upcoming(self, position: float) -> list[Cue]:
        i = self.index_at(position)
        return self.cues[i + 1 :]


def parse_time(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    parts = str(value).strip().split(":")
    if len(parts) == 1:
        return float(parts[0])
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    return seconds


def sidecar_path(track: str | Path) -> Path:
    """Default cue path for a track: ``song.m4a`` -> ``song.cues.yaml``."""
    track = Path(track)
    return track.with_suffix(".cues.yaml")


def load_cues(path: str | Path) -> CueSheet:
    data = yaml.safe_load(Path(path).read_text()) or {}
    raw = data.get("cues", [])
    cues = [
        Cue(
            time=parse_time(item["time"]),
            label=str(item.get("label", "")),
            art=str(item.get("art", "")),
        )
        for item in raw
    ]
    cues.sort(key=lambda c: c.time)
    return CueSheet(cues=cues, show_countdown=bool(data.get("show_countdown", True)))


def load_for_track(track: str | Path, explicit: str | Path | None = None) -> CueSheet:
    """Load cues from ``explicit`` if given, else the track's sidecar, else empty."""
    if explicit is not None:
        return load_cues(explicit)
    auto = sidecar_path(track)
    if auto.exists():
        return load_cues(auto)
    return CueSheet(cues=[])
