from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from lumen_dlp.domain import AuthStrategy, Command, OutputSpec
from lumen_dlp.infrastructure import YtDlpClient, entry_url, run_parallel


@dataclass
class FetchCommand(Command):
    """Download whatever the OutputSpec asks for (audio/video/subs in any combo).

    `sync` mode is just this command with ``archive_file`` set.
    """

    url: str
    output: OutputSpec
    auth: AuthStrategy
    output_dir: Path = field(default_factory=lambda: Path("downloads"))
    archive_file: Path | None = None
    concurrent: int = 1
    console: Console = field(default_factory=Console)

    def execute(self) -> int:
        if self.output.is_empty:
            self.console.print(
                "[red]Nothing to download — specify --audio, --video, or --subs.[/red]"
            )
            return 2

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._announce()

        client = YtDlpClient(self.auth)

        if self.concurrent > 1:
            entries = client.list_playlist_entries(self.url)
            if len(entries) > 1:
                return self._run_parallel(client, entries)

        try:
            client.fetch(
                self.url,
                self.output,
                self.output_dir,
                archive=self.archive_file,
            )
        except Exception as exc:
            self.console.print(f"[red]✗[/red] {exc}")
            return 1

        self.console.print("[green]✓[/green] Done.")
        return 0

    def _run_parallel(self, client: YtDlpClient, entries: list[dict]) -> int:
        # yt-dlp's download_archive isn't thread-safe; manage manually in run_parallel.
        def worker(entry: dict) -> None:
            client.fetch(
                entry_url(entry),
                self.output,
                self.output_dir,
                archive=None,
                quiet=True,
            )

        return run_parallel(
            entries=entries,
            worker=worker,
            concurrent=self.concurrent,
            archive_file=self.archive_file,
            console=self.console,
            label=self._label(),
        )

    def _announce(self) -> None:
        parts: list[str] = []
        if self.output.audio:
            parts.append(f"audio:{self.output.audio.format.value}")
        if self.output.video:
            parts.append(f"video:{self.output.video.format.value}")
        if self.output.subs:
            langs = ",".join(self.output.subs.langs) if self.output.subs.langs else "all"
            parts.append(f"subs:{self.output.subs.format.value}({langs})")
        self.console.print(
            f"[bold]Downloading[/bold] {' + '.join(parts)} → [cyan]{self.output_dir}[/cyan]"
        )

    def _label(self) -> str:
        bits = []
        if self.output.audio:
            bits.append("audio")
        if self.output.video:
            bits.append("video")
        if self.output.subs:
            bits.append("subs")
        return "Downloading " + "+".join(bits)
