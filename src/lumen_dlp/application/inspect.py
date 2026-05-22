from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console

from lumen_dlp.domain import AuthStrategy, Command, Track
from lumen_dlp.infrastructure import YtDlpClient
from lumen_dlp.presentation.rendering import render_subs, render_tracks


@dataclass
class InspectCommand(Command):
    """Show what a URL contains without downloading. For single videos: title, subs available.
    For playlists: track list."""

    url: str
    auth: AuthStrategy
    console: Console = field(default_factory=Console)

    def execute(self) -> int:
        client = YtDlpClient(self.auth)
        try:
            entries, is_playlist = client.inspect(self.url)
        except Exception as exc:
            self.console.print(f"[red]✗[/red] {exc}")
            return 1

        if not entries:
            self.console.print("[yellow]Nothing found at this URL.[/yellow]")
            return 1

        if is_playlist:
            tracks = [
                Track(
                    index=i,
                    title=e.title,
                    artist=e.artist,
                    duration=e.duration,
                )
                for i, e in enumerate(entries, 1)
            ]
            self.console.print(render_tracks(tracks))
            self.console.print("[dim]Run with a single video URL to see available subtitles.[/dim]")
            return 0

        only = entries[0]
        self.console.print(
            f"[bold]{only.title}[/bold]"
            + (f"  [dim]by[/dim] {only.artist}" if only.artist != "—" else "")
        )
        if only.duration:
            mins, secs = only.duration // 60, only.duration % 60
            self.console.print(f"[dim]Duration:[/dim] {mins}:{secs:02d}")
        self.console.print(f"[dim]URL:[/dim] {only.webpage_url}")
        if only.subtitles:
            self.console.print(render_subs(only.subtitles))
        else:
            self.console.print("[dim]No subtitles available.[/dim]")
        return 0
