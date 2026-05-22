from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Track:
    index: int
    title: str
    artist: str
    duration: int | None

    @property
    def duration_str(self) -> str:
        if not self.duration:
            return "—"
        return f"{self.duration // 60}:{self.duration % 60:02d}"

    @classmethod
    def from_entry(cls, index: int, entry: dict) -> Track:
        artists = entry.get("artists") or []
        artist = ", ".join(a["name"] for a in artists) or entry.get("uploader") or "—"
        return cls(
            index=index,
            title=entry.get("title") or "—",
            artist=artist,
            duration=entry.get("duration"),
        )


@dataclass(frozen=True, slots=True)
class Subtitle:
    lang: str
    is_auto: bool
