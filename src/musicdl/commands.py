from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import yt_dlp
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table


def _read_archive_ids(archive: Path) -> set[str]:
    if not archive.exists():
        return set()
    ids: set[str] = set()
    for line in archive.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            ids.add(parts[1])
    return ids


def _append_archive(archive: Path, video_id: str, lock: threading.Lock) -> None:
    with lock, archive.open("a", encoding="utf-8") as f:
        f.write(f"youtube {video_id}\n")


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


@dataclass
class ListPlaylistCommand(Command):
    url: str
    cookies: CookieSource
    console: Console = field(default_factory=Console)

    def execute(self) -> int:
        with self.console.status(f"Fetching playlist using {self.cookies.browser} cookies..."):
            entries = self._fetch_entries()

        if not entries:
            self.console.print("[yellow]No songs found.[/yellow]")
            return 1

        tracks = [Track.from_entry(i, e) for i, e in enumerate(entries, 1)]
        self.console.print(self._render(tracks))
        return 0

    def _fetch_entries(self) -> list[dict]:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "cookiesfrombrowser": self.cookies.as_ydl_tuple(),
        }
        with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(self.url, download=False)
        return info.get("entries") or []

    def _render(self, tracks: list[Track]) -> Table:
        table = Table(title=f"Songs ({len(tracks)})")
        table.add_column("#", justify="right", style="dim", no_wrap=True)
        table.add_column("Title", style="bold")
        table.add_column("Artist", style="cyan")
        table.add_column("Duration", justify="right")
        for t in tracks:
            table.add_row(str(t.index), t.title, t.artist, t.duration_str)
        return table


@dataclass
class DownloadTranscriptsCommand(Command):
    url: str
    cookies: CookieSource
    output_dir: Path = field(default_factory=lambda: Path("transcripts"))
    languages: tuple[str, ...] = ("es", "en")
    include_auto: bool = True
    subtitle_format: SubtitleFormat = SubtitleFormat.SRT
    archive_file: Path | None = None
    concurrent: int = 1
    console: Console = field(default_factory=Console)

    def execute(self) -> int:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        langs = ",".join(self.languages)
        self.console.print(
            f"[bold]Downloading transcripts[/bold] ({langs}, auto={self.include_auto}) "
            f"→ [cyan]{self.output_dir}[/cyan]"
        )

        if self.concurrent > 1:
            entries = self._expand_playlist()
            if len(entries) > 1:
                return self._download_parallel(entries)

        with yt_dlp.YoutubeDL(self._build_opts()) as ydl:  # type: ignore[arg-type]
            code = ydl.download([self.url])

        files = sorted(self.output_dir.glob(f"*.{self.subtitle_format.value}"))
        if not files:
            self.console.print("[yellow]No transcripts found.[/yellow]")
            return 1

        self.console.print(f"[green]✓[/green] {len(files)} transcript(s) saved.")
        return int(code or 0)

    def _build_opts(self, *, quiet: bool = False) -> dict:
        opts: dict = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": self.include_auto,
            "subtitleslangs": list(self.languages),
            "subtitlesformat": self.subtitle_format.value,
            "outtmpl": str(self.output_dir / "%(title)s [%(id)s].%(ext)s"),
            "ignoreerrors": True,
            "cookiesfrombrowser": self.cookies.as_ydl_tuple(),
            "postprocessors": [
                {"key": "FFmpegSubtitlesConvertor", "format": self.subtitle_format.value}
            ],
        }
        if quiet:
            opts["quiet"] = True
            opts["no_warnings"] = True
            opts["noprogress"] = True
        if self.archive_file is not None:
            self.archive_file.parent.mkdir(parents=True, exist_ok=True)
            opts["download_archive"] = str(self.archive_file)
        return opts

    def _expand_playlist(self) -> list[dict]:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "cookiesfrombrowser": self.cookies.as_ydl_tuple(),
        }
        with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(self.url, download=False)
        entries = info.get("entries") if isinstance(info, dict) else None
        if entries is None:
            return [info] if isinstance(info, dict) else []
        return [e for e in entries if e]

    def _download_parallel(self, entries: list[dict]) -> int:
        already = _read_archive_ids(self.archive_file) if self.archive_file else set()
        pending = [e for e in entries if e.get("id") and e["id"] not in already]
        skipped = len(entries) - len(pending)
        if not pending:
            self.console.print(
                f"[green]✓[/green] Nothing to download ({skipped} already in archive)."
            )
            return 0

        self.console.print(
            f"[dim]Parallel:[/dim] {self.concurrent} workers · "
            f"[dim]queued:[/dim] {len(pending)} · [dim]skipped:[/dim] {skipped}"
        )

        archive_lock = threading.Lock()
        opts_template = self._build_opts(quiet=True)
        opts_template.pop("download_archive", None)
        failures: list[tuple[str, str]] = []

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=self.console,
        )

        with progress:
            overall = progress.add_task("[bold]Transcripts[/bold]", total=len(pending))
            with ThreadPoolExecutor(max_workers=self.concurrent) as pool:
                futures = {
                    pool.submit(self._download_one, e, opts_template): e for e in pending
                }
                for future in as_completed(futures):
                    entry = futures[future]
                    title = entry.get("title") or entry.get("id") or "?"
                    try:
                        future.result()
                    except Exception as exc:  # noqa: BLE001
                        failures.append((title, str(exc)))
                        self.console.print(f"[red]✗[/red] {title} — {exc}")
                    else:
                        if self.archive_file and entry.get("id"):
                            _append_archive(self.archive_file, entry["id"], archive_lock)
                        self.console.print(f"[green]✓[/green] {title}")
                    finally:
                        progress.advance(overall)

        if failures:
            self.console.print(f"[yellow]{len(failures)} failed.[/yellow]")
            return 1
        return 0

    def _download_one(self, entry: dict, opts_template: dict) -> None:
        opts = dict(opts_template)
        opts["postprocessors"] = list(opts_template["postprocessors"])
        url = entry.get("url") or entry.get("webpage_url") or entry["id"]
        with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
            ydl.download([url])


@dataclass
class DownloadMediaCommand(Command):
    url: str
    cookies: CookieSource
    media_type: MediaType = MediaType.AUDIO
    audio_format: AudioFormat = AudioFormat.M4A
    video_format: VideoFormat = VideoFormat.MP4
    audio_quality: str = "0"  # 0 = best (VBR); or a kbps number like "192"
    max_height: int | None = None  # e.g. 1080, 720; None = best
    output_dir: Path = field(default_factory=lambda: Path("downloads"))
    embed_thumbnail: bool = True
    embed_metadata: bool = True
    archive_file: Path | None = None
    concurrent: int = 1
    console: Console = field(default_factory=Console)

    def execute(self) -> int:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.audio_format if self.media_type is MediaType.AUDIO else self.video_format
        self.console.print(
            f"[bold]Downloading {self.media_type.value}[/bold] as [cyan]{target}[/cyan] "
            f"→ [cyan]{self.output_dir}[/cyan]"
        )

        if self.concurrent > 1:
            entries = self._expand_playlist()
            if len(entries) > 1:
                return self._download_parallel(entries)

        with yt_dlp.YoutubeDL(self._build_opts()) as ydl:  # type: ignore[arg-type]
            code = ydl.download([self.url])
        self.console.print("[green]✓[/green] Done.")
        return int(code or 0)

    # --- single-thread / fallback path ---

    def _build_opts(self, *, quiet: bool = False) -> dict:
        opts: dict = {
            "outtmpl": str(self.output_dir / "%(title)s [%(id)s].%(ext)s"),
            "cookiesfrombrowser": self.cookies.as_ydl_tuple(),
            "ignoreerrors": True,
            "noplaylist": False,
            "postprocessors": [],
        }
        if quiet:
            opts["quiet"] = True
            opts["no_warnings"] = True
            opts["noprogress"] = True
        if self.archive_file is not None:
            self.archive_file.parent.mkdir(parents=True, exist_ok=True)
            opts["download_archive"] = str(self.archive_file)

        if self.media_type is MediaType.AUDIO:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"].append(
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": self.audio_format.value,
                    "preferredquality": self.audio_quality,
                }
            )
        else:
            height_filter = f"[height<={self.max_height}]" if self.max_height else ""
            opts["format"] = f"bv*{height_filter}+ba/b{height_filter}"
            opts["merge_output_format"] = self.video_format.value

        if self.embed_metadata:
            opts["postprocessors"].append({"key": "FFmpegMetadata"})
        if self.embed_thumbnail:
            opts["writethumbnail"] = True
            opts["postprocessors"].append({"key": "EmbedThumbnail"})

        return opts

    # --- parallel path ---

    def _expand_playlist(self) -> list[dict]:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "cookiesfrombrowser": self.cookies.as_ydl_tuple(),
        }
        with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(self.url, download=False)
        entries = info.get("entries") if isinstance(info, dict) else None
        if entries is None:
            return [info] if isinstance(info, dict) else []
        return [e for e in entries if e]

    def _download_parallel(self, entries: list[dict]) -> int:
        already = _read_archive_ids(self.archive_file) if self.archive_file else set()
        pending = [e for e in entries if e.get("id") and e["id"] not in already]
        skipped = len(entries) - len(pending)

        if not pending:
            self.console.print(
                f"[green]✓[/green] Nothing to download ({skipped} already in archive)."
            )
            return 0

        self.console.print(
            f"[dim]Parallel:[/dim] {self.concurrent} workers · "
            f"[dim]queued:[/dim] {len(pending)} · "
            f"[dim]skipped:[/dim] {skipped}"
        )

        archive_lock = threading.Lock()
        failures: list[tuple[str, str]] = []

        # Build a quiet opts template once; per-worker creates its own YoutubeDL.
        # We disable yt-dlp's own download_archive — we update it ourselves on success.
        opts_template = self._build_opts(quiet=True)
        opts_template.pop("download_archive", None)

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=self.console,
            transient=False,
        )

        with progress:
            overall = progress.add_task(
                f"[bold]Downloading {self.media_type.value}[/bold]", total=len(pending)
            )
            with ThreadPoolExecutor(max_workers=self.concurrent) as pool:
                futures = {
                    pool.submit(self._download_one, entry, opts_template): entry
                    for entry in pending
                }
                for future in as_completed(futures):
                    entry = futures[future]
                    title = entry.get("title") or entry.get("id") or "?"
                    try:
                        future.result()
                    except Exception as exc:  # noqa: BLE001
                        failures.append((title, str(exc)))
                        self.console.print(f"[red]✗[/red] {title} — {exc}")
                    else:
                        if self.archive_file and entry.get("id"):
                            _append_archive(self.archive_file, entry["id"], archive_lock)
                        self.console.print(f"[green]✓[/green] {title}")
                    finally:
                        progress.advance(overall)

        if failures:
            self.console.print(f"[yellow]{len(failures)} failed.[/yellow]")
            return 1
        return 0

    def _download_one(self, entry: dict, opts_template: dict) -> None:
        opts = dict(opts_template)
        # Each worker mutates its own copy of postprocessors list
        opts["postprocessors"] = list(opts_template["postprocessors"])
        url = entry.get("url") or entry.get("webpage_url") or entry["id"]
        with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
            ydl.download([url])
