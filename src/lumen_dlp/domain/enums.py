from __future__ import annotations

from enum import StrEnum


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
