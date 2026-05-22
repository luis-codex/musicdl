from __future__ import annotations

from dataclasses import dataclass

from lumen_dlp.domain.enums import AudioFormat, SubtitleFormat, VideoFormat


@dataclass(frozen=True, slots=True)
class AudioRequest:
    format: AudioFormat = AudioFormat.M4A
    quality: str = "0"  # 0 = best (VBR) per yt-dlp; or kbps like "192"


@dataclass(frozen=True, slots=True)
class VideoRequest:
    format: VideoFormat = VideoFormat.MP4
    max_height: int | None = None


@dataclass(frozen=True, slots=True)
class SubsRequest:
    format: SubtitleFormat = SubtitleFormat.SRT
    langs: tuple[str, ...] = ()  # empty tuple = all available
    include_auto: bool = True


@dataclass(frozen=True, slots=True)
class OutputSpec:
    """What the user wants out of one URL. At least one of audio/video/subs must be set."""

    audio: AudioRequest | None = None
    video: VideoRequest | None = None
    subs: SubsRequest | None = None
    embed_thumbnail: bool = True
    embed_metadata: bool = True

    @property
    def is_empty(self) -> bool:
        return self.audio is None and self.video is None and self.subs is None
