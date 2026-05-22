from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console

from musicdl.domain import Command, CookieSource, Track
from musicdl.infrastructure import YtDlpClient
from musicdl.presentation.rendering import render_tracks


@dataclass
class ListPlaylistCommand(Command):
    url: str
    cookies: CookieSource
    console: Console = field(default_factory=Console)

    def execute(self) -> int:
        client = YtDlpClient(self.cookies)
        with self.console.status(f"Fetching playlist using {self.cookies.browser} cookies..."):
            entries = client.list_playlist_entries(self.url)

        if not entries:
            self.console.print("[yellow]No songs found.[/yellow]")
            return 1

        tracks = [Track.from_entry(i, e) for i, e in enumerate(entries, 1)]
        self.console.print(render_tracks(tracks))
        return 0
