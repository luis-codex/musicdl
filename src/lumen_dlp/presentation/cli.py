from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from lumen_dlp.application import FetchCommand, InspectCommand
from lumen_dlp.domain import (
    AudioFormat,
    AudioRequest,
    AuthStrategy,
    OutputSpec,
    SubsRequest,
    SubtitleFormat,
    VideoFormat,
    VideoRequest,
)

for stream in (sys.stdout, sys.stderr):
    if isinstance(stream, io.TextIOWrapper):
        stream.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_PLAYLIST = "https://music.youtube.com/playlist?list=LM"

console = Console()

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help=(
        "Universal media downloader (YouTube, X, TikTok, Instagram, 1000+ sites). "
        "Powered by yt-dlp + ffmpeg.  Cookies are handled automatically."
    ),
)


# --- Reusable option types --------------------------------------------------

UrlArg = Annotated[str, typer.Argument(help="Video or playlist URL.")]

AudioFlag = Annotated[bool, typer.Option("--audio", help="Download audio.")]
AudioFormatOpt = Annotated[
    AudioFormat, typer.Option("--audio-format", "-a", help="Audio codec (with --audio).")
]
QualityOpt = Annotated[
    str, typer.Option("--quality", "-q", help="Audio quality: 0 (best) to 9, or kbps like '192'.")
]

VideoFlag = Annotated[bool, typer.Option("--video", help="Download video.")]
VideoFormatOpt = Annotated[
    VideoFormat, typer.Option("--video-format", "-v", help="Video container (with --video).")
]
MaxHeightOpt = Annotated[
    int | None, typer.Option("--max-height", help="Cap video resolution (e.g. 1080, 720).")
]

SubsFlag = Annotated[bool, typer.Option("--subs", help="Download subtitles.")]
SubsFormatOpt = Annotated[
    SubtitleFormat, typer.Option("--subs-format", help="Subtitle format (with --subs).")
]
LangsOpt = Annotated[
    str,
    typer.Option(
        "--lang",
        "-l",
        help="Comma-separated subtitle languages (e.g. 'es,en,pt'). Empty = all available.",
    ),
]
NoAutoOpt = Annotated[bool, typer.Option("--no-auto", help="Exclude auto-generated subtitles.")]

AllFlag = Annotated[bool, typer.Option("--all", help="Shortcut for --audio --video --subs.")]

BrowserOpt = Annotated[
    str | None,
    typer.Option(
        "--browser",
        help=(
            "Force cookies from this browser (skip anonymous). "
            "Default: anonymous first, auto-detect a browser on auth errors."
        ),
    ),
]
ProfileOpt = Annotated[
    str | None,
    typer.Option(
        "--profile",
        help="Browser profile path (for Firefox forks like Zen). Used with --browser.",
    ),
]
NoCookiesFlag = Annotated[
    bool,
    typer.Option("--no-cookies", help="Never use browser cookies, even when the site needs auth."),
]

OutputOpt = Annotated[Path, typer.Option("--output", "-o", help="Output directory.")]
ThumbnailOpt = Annotated[
    bool, typer.Option("--thumbnail/--no-thumbnail", help="Embed cover/thumbnail.")
]
MetadataOpt = Annotated[
    bool, typer.Option("--metadata/--no-metadata", help="Embed track metadata.")
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
ArchiveOpt = Annotated[
    Path | None,
    typer.Option(
        "--archive",
        help="Archive file tracking downloaded IDs. Defaults to <output>/.lumen-dlp-archive.txt.",
    ),
]


# --- Helpers ----------------------------------------------------------------


def _auth_from_flags(
    browser_flag: str | None, profile_flag: str | None, no_cookies: bool
) -> AuthStrategy:
    if no_cookies:
        return AuthStrategy.no_cookies()
    browser = browser_flag or os.environ.get("LUMEN_DLP_BROWSER")
    if browser:
        profile = profile_flag or os.environ.get("LUMEN_DLP_BROWSER_PROFILE") or None
        return AuthStrategy.force_browser(browser=browser, profile=profile)
    return AuthStrategy.auto()


def _build_output_spec(
    *,
    audio: bool,
    audio_format: AudioFormat,
    quality: str,
    video: bool,
    video_format: VideoFormat,
    max_height: int | None,
    subs: bool,
    subs_format: SubtitleFormat,
    langs: str,
    no_auto: bool,
    all_: bool,
    thumbnail: bool,
    metadata: bool,
) -> OutputSpec:
    if all_:
        audio = video = subs = True
    # No output flag at all → sensible default: audio m4a.
    if not (audio or video or subs):
        audio = True

    lang_tuple = tuple(token.strip() for token in langs.split(",") if token.strip())

    return OutputSpec(
        audio=AudioRequest(format=audio_format, quality=quality) if audio else None,
        video=VideoRequest(format=video_format, max_height=max_height) if video else None,
        subs=(
            SubsRequest(format=subs_format, langs=lang_tuple, include_auto=not no_auto)
            if subs
            else None
        ),
        embed_thumbnail=thumbnail,
        embed_metadata=metadata,
    )


# --- Commands ---------------------------------------------------------------


@app.command("get")
def get(
    url: UrlArg = DEFAULT_PLAYLIST,
    audio: AudioFlag = False,
    audio_format: AudioFormatOpt = AudioFormat.M4A,
    quality: QualityOpt = "0",
    video: VideoFlag = False,
    video_format: VideoFormatOpt = VideoFormat.MP4,
    max_height: MaxHeightOpt = None,
    subs: SubsFlag = False,
    subs_format: SubsFormatOpt = SubtitleFormat.SRT,
    langs: LangsOpt = "",
    no_auto: NoAutoOpt = False,
    all_: AllFlag = False,
    browser: BrowserOpt = None,
    profile: ProfileOpt = None,
    no_cookies: NoCookiesFlag = False,
    output: OutputOpt = Path("downloads"),
    thumbnail: ThumbnailOpt = True,
    metadata: MetadataOpt = True,
    concurrent: ConcurrentOpt = 1,
) -> None:
    """Download from a URL. Any combo of --audio, --video, --subs (default: audio m4a)."""
    auth = _auth_from_flags(browser, profile, no_cookies)
    output_spec = _build_output_spec(
        audio=audio,
        audio_format=audio_format,
        quality=quality,
        video=video,
        video_format=video_format,
        max_height=max_height,
        subs=subs,
        subs_format=subs_format,
        langs=langs,
        no_auto=no_auto,
        all_=all_,
        thumbnail=thumbnail,
        metadata=metadata,
    )
    cmd = FetchCommand(
        url=url,
        output=output_spec,
        auth=auth,
        output_dir=output,
        archive_file=None,
        concurrent=concurrent,
        console=console,
    )
    raise typer.Exit(code=cmd.execute())


@app.command("sync")
def sync(
    url: UrlArg = DEFAULT_PLAYLIST,
    audio: AudioFlag = False,
    audio_format: AudioFormatOpt = AudioFormat.M4A,
    quality: QualityOpt = "0",
    video: VideoFlag = False,
    video_format: VideoFormatOpt = VideoFormat.MP4,
    max_height: MaxHeightOpt = None,
    subs: SubsFlag = False,
    subs_format: SubsFormatOpt = SubtitleFormat.SRT,
    langs: LangsOpt = "",
    no_auto: NoAutoOpt = False,
    all_: AllFlag = False,
    archive: ArchiveOpt = None,
    browser: BrowserOpt = None,
    profile: ProfileOpt = None,
    no_cookies: NoCookiesFlag = False,
    output: OutputOpt = Path("downloads"),
    thumbnail: ThumbnailOpt = True,
    metadata: MetadataOpt = True,
    concurrent: ConcurrentOpt = 1,
) -> None:
    """Incremental download — skip what's already archived. Pair with cron / Task Scheduler."""
    auth = _auth_from_flags(browser, profile, no_cookies)
    output_spec = _build_output_spec(
        audio=audio,
        audio_format=audio_format,
        quality=quality,
        video=video,
        video_format=video_format,
        max_height=max_height,
        subs=subs,
        subs_format=subs_format,
        langs=langs,
        no_auto=no_auto,
        all_=all_,
        thumbnail=thumbnail,
        metadata=metadata,
    )
    archive_path = archive if archive is not None else output / ".lumen-dlp-archive.txt"
    cmd = FetchCommand(
        url=url,
        output=output_spec,
        auth=auth,
        output_dir=output,
        archive_file=archive_path,
        concurrent=concurrent,
        console=console,
    )
    console.print(f"[dim]Archive:[/dim] {archive_path}")
    raise typer.Exit(code=cmd.execute())


@app.command("list")
def list_cmd(
    url: UrlArg = DEFAULT_PLAYLIST,
    browser: BrowserOpt = None,
    profile: ProfileOpt = None,
    no_cookies: NoCookiesFlag = False,
) -> None:
    """Show what's at a URL without downloading.

    For a single video: title, duration, available subtitles.  For a playlist: track list.
    """
    auth = _auth_from_flags(browser, profile, no_cookies)
    cmd = InspectCommand(url=url, auth=auth, console=console)
    raise typer.Exit(code=cmd.execute())


def main() -> None:
    app()
