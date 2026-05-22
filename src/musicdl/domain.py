from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class MediaType(StrEnum):
    AUDIO = "audio"
    VIDEO = "video"


class AudioFormat(StrEnum):
    MP3 = "mp3"
    M4A = "m4a"
    OPUS = "opus"
    FLAC = "flac"
    WAV = "wav"
    VORBIS = "vorbis"


class VideoFormat(StrEnum):
    MP4 = "mp4"
    MKV = "mkv"
    WEBM = "webm"


class SubtitleFormat(StrEnum):
    SRT = "srt"
    VTT = "vtt"
    ASS = "ass"
    LRC = "lrc"


@dataclass(frozen=True, slots=True)
class CookieSource:
    browser: str
    profile: str | None = None

    def as_ydl_tuple(self) -> tuple:
        return (self.browser, self.profile) if self.profile else (self.browser,)


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


class Command(ABC):
    @abstractmethod
    def execute(self) -> int:
        """Run the command. Return an exit code (0 = success)."""
