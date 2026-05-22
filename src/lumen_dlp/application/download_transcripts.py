from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from lumen_dlp.domain import Command, CookieSource, SubtitleFormat
from lumen_dlp.infrastructure import YtDlpClient, entry_url, run_parallel


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
                    label="Transcripts",
                )

        client.download(self.url, self._build_opts())

        files = sorted(self.output_dir.glob(f"*.{self.subtitle_format.value}"))
        if not files:
            self.console.print("[yellow]No transcripts found.[/yellow]")
            return 1

        self.console.print(f"[green]✓[/green] {len(files)} transcript(s) saved.")
        return 0

    def _build_opts(self, *, quiet: bool = False) -> dict:
        opts: dict = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": self.include_auto,
            "subtitleslangs": list(self.languages),
            "subtitlesformat": self.subtitle_format.value,
            "outtmpl": str(self.output_dir / "%(title)s [%(id)s].%(ext)s"),
            "ignoreerrors": True,
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
