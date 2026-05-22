from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from musicdl.domain import AudioFormat, Command, CookieSource, MediaType, VideoFormat
from musicdl.infrastructure import YtDlpClient, entry_url, run_parallel


@dataclass
class DownloadMediaCommand(Command):
    url: str
    cookies: CookieSource
    media_type: MediaType = MediaType.AUDIO
    audio_format: AudioFormat = AudioFormat.M4A
    video_format: VideoFormat = VideoFormat.MP4
    audio_quality: str = "0"  # 0 = best (VBR); or kbps like "192"
    max_height: int | None = None
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

        client = YtDlpClient(self.cookies)

        if self.concurrent > 1:
            entries = client.list_playlist_entries(self.url)
            if len(entries) > 1:
                opts_template = self._build_opts(quiet=True)
                opts_template.pop("download_archive", None)

                def worker(entry: dict) -> None:
                    opts = dict(opts_template)
                    opts["postprocessors"] = list(opts_template["postprocessors"])
                    client.download(entry_url(entry), opts)

                return run_parallel(
                    entries=entries,
                    worker=worker,
                    concurrent=self.concurrent,
                    archive_file=self.archive_file,
                    console=self.console,
                    label=f"Downloading {self.media_type.value}",
                )

        client.download(self.url, self._build_opts())
        self.console.print("[green]✓[/green] Done.")
        return 0

    def _build_opts(self, *, quiet: bool = False) -> dict:
        opts: dict = {
            "outtmpl": str(self.output_dir / "%(title)s [%(id)s].%(ext)s"),
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
