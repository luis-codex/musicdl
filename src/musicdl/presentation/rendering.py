from __future__ import annotations

from rich.table import Table

from musicdl.domain import Track


def render_tracks(tracks: list[Track], title: str | None = None) -> Table:
    table = Table(title=title or f"Songs ({len(tracks)})")
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Artist", style="cyan")
    table.add_column("Duration", justify="right")
    for t in tracks:
        table.add_row(str(t.index), t.title, t.artist, t.duration_str)
    return table
