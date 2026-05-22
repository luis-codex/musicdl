from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from musicdl.application import (
    DownloadMediaCommand,
    DownloadTranscriptsCommand,
    ListPlaylistCommand,
)
from musicdl.domain import (
    AudioFormat,
    CookieSource,
    MediaType,
    SubtitleFormat,
    VideoFormat,
)

for stream in (sys.stdout, sys.stderr):
    if isinstance(stream, io.TextIOWrapper):
        stream.reconfigure(encoding="utf-8", errors="replace")

PLAYLIST_URL = "https://music.youtube.com/playlist?list=LM"
DEFAULT_BROWSER = os.environ.get("MUSICDL_BROWSER", "firefox")
DEFAULT_PROFILE = os.environ.get("MUSICDL_BROWSER_PROFILE", "")

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="YouTube Music helpers — list, download (audio/video), sync, and grab transcripts.",
)
console = Console()


# --- Reusable typer annotations -------------------------------------------------

UrlArg = Annotated[str, typer.Argument(help="Video or playlist URL.")]
MediaOpt = Annotated[MediaType, typer.Option("--type", "-t", help="Download audio or video.")]
AudioFormatOpt = Annotated[
    AudioFormat, typer.Option("--audio-format", "-a", help="Audio codec when --type audio.")
]
VideoFormatOpt = Annotated[
    VideoFormat, typer.Option("--video-format", "-v", help="Container when --type video.")
]
QualityOpt = Annotated[
    str, typer.Option("--quality", "-q", help="Audio quality: 0 (best) to 9, or kbps like '192'.")
]
MaxHeightOpt = Annotated[
    int | None, typer.Option("--max-height", help="Cap video resolution (e.g. 1080, 720).")
]
OutputOpt = Annotated[Path, typer.Option("--output", "-o", help="Output directory.")]
ThumbnailOpt = Annotated[
    bool, typer.Option("--thumbnail/--no-thumbnail", help="Embed cover/thumbnail.")
]
MetadataOpt = Annotated[
    bool, typer.Option("--metadata/--no-metadata", help="Embed track metadata.")
]
ArchiveOpt = Annotated[
    Path | None,
    typer.Option(
        "--archive",
        help="Archive file tracking downloaded IDs. Defaults to <output>/.musicdl-archive.txt.",
    ),
]
ConcurrentOpt = Annotated[
    int,
    typer.Option(
        "--concurrent",
        "-j",
        min=1,
        help="Parallel workers for playlists (default 1 = serial).",
    ),
]


@app.callback()
def _global(
    ctx: typer.Context,
    browser: Annotated[
        str, typer.Option("--browser", help="Browser to read cookies from.")
    ] = DEFAULT_BROWSER,
    profile: Annotated[
        str, typer.Option("--profile", help="Browser profile path (for Zen/Firefox forks).")
    ] = DEFAULT_PROFILE,
) -> None:
    ctx.obj = CookieSource(browser=browser, profile=profile or None)


def _cookies(ctx: typer.Context) -> CookieSource:
    return ctx.obj


def _build_download(
    *,
    url: str,
    cookies: CookieSource,
    media: MediaType,
    audio_format: AudioFormat,
    video_format: VideoFormat,
    quality: str,
    max_height: int | None,
    output: Path,
    thumbnail: bool,
    metadata: bool,
    archive: Path | None,
    concurrent: int,
) -> DownloadMediaCommand:
    return DownloadMediaCommand(
        url=url,
        cookies=cookies,
        media_type=media,
        audio_format=audio_format,
        video_format=video_format,
        audio_quality=quality,
        max_height=max_height,
        output_dir=output,
        embed_thumbnail=thumbnail,
        embed_metadata=metadata,
        archive_file=archive,
        concurrent=concurrent,
        console=console,
    )


@app.command("list")
def list_songs(
    ctx: typer.Context,
    url: UrlArg = PLAYLIST_URL,
) -> None:
    """List songs from a YouTube Music playlist (defaults to Liked Music)."""
    command = ListPlaylistCommand(url=url, cookies=_cookies(ctx), console=console)
    raise typer.Exit(code=command.execute())


@app.command("download")
def download(
    ctx: typer.Context,
    url: UrlArg = PLAYLIST_URL,
    media: MediaOpt = MediaType.AUDIO,
    audio_format: AudioFormatOpt = AudioFormat.M4A,
    video_format: VideoFormatOpt = VideoFormat.MP4,
    quality: QualityOpt = "0",
    max_height: MaxHeightOpt = None,
    output: OutputOpt = Path("downloads"),
    thumbnail: ThumbnailOpt = True,
    metadata: MetadataOpt = True,
    concurrent: ConcurrentOpt = 1,
) -> None:
    """Download a video or playlist as audio or video, in the chosen format."""
    command = _build_download(
        url=url,
        cookies=_cookies(ctx),
        media=media,
        audio_format=audio_format,
        video_format=video_format,
        quality=quality,
        max_height=max_height,
        output=output,
        thumbnail=thumbnail,
        metadata=metadata,
        archive=None,
        concurrent=concurrent,
    )
    raise typer.Exit(code=command.execute())


@app.command("sync")
def sync(
    ctx: typer.Context,
    url: UrlArg = PLAYLIST_URL,
    media: MediaOpt = MediaType.AUDIO,
    audio_format: AudioFormatOpt = AudioFormat.M4A,
    video_format: VideoFormatOpt = VideoFormat.MP4,
    quality: QualityOpt = "0",
    max_height: MaxHeightOpt = None,
    output: OutputOpt = Path("downloads"),
    archive: ArchiveOpt = None,
    thumbnail: ThumbnailOpt = True,
    metadata: MetadataOpt = True,
    concurrent: ConcurrentOpt = 1,
) -> None:
    """Download only new items from a playlist, skipping anything already downloaded."""
    archive_path = archive if archive is not None else output / ".musicdl-archive.txt"
    command = _build_download(
        url=url,
        cookies=_cookies(ctx),
        media=media,
        audio_format=audio_format,
        video_format=video_format,
        quality=quality,
        max_height=max_height,
        output=output,
        thumbnail=thumbnail,
        metadata=metadata,
        archive=archive_path,
        concurrent=concurrent,
    )
    console.print(f"[dim]Archive:[/dim] {archive_path}")
    raise typer.Exit(code=command.execute())


@app.command("transcripts")
def transcripts(
    ctx: typer.Context,
    url: UrlArg = PLAYLIST_URL,
    output: OutputOpt = Path("transcripts"),
    lang: Annotated[
        list[str], typer.Option("--lang", "-l", help="Subtitle languages (repeatable).")
    ] = ["es", "en"],  # noqa: B006 — typer requires a mutable default for repeatable options
    auto: Annotated[
        bool, typer.Option("--auto/--no-auto", help="Include auto-generated subtitles.")
    ] = True,
    fmt: Annotated[
        SubtitleFormat, typer.Option("--format", "-f", help="Subtitle format.")
    ] = SubtitleFormat.SRT,
    archive: ArchiveOpt = None,
    concurrent: ConcurrentOpt = 1,
) -> None:
    """Download transcripts/subtitles from a video or playlist (when available)."""
    archive_path = archive if archive is not None else output / ".musicdl-archive.txt"
    command = DownloadTranscriptsCommand(
        url=url,
        cookies=_cookies(ctx),
        output_dir=output,
        languages=tuple(lang),
        include_auto=auto,
        subtitle_format=fmt,
        archive_file=archive_path,
        concurrent=concurrent,
        console=console,
    )
    console.print(f"[dim]Archive:[/dim] {archive_path}")
    raise typer.Exit(code=command.execute())


def main() -> None:
    app()
