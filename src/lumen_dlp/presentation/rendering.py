from __future__ import annotations

from collections.abc import Iterable

from rich.table import Table

from lumen_dlp.domain import Subtitle, Track


def render_tracks(tracks: list[Track], title: str | None = None) -> Table:
    table = Table(title=title or f"Tracks ({len(tracks)})")
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Artist", style="cyan")
    table.add_column("Duration", justify="right")
    for t in tracks:
        table.add_row(str(t.index), t.title, t.artist, t.duration_str)
    return table


def render_subs(subs: Iterable[Subtitle]) -> Table:
    by_lang: dict[str, dict[str, bool]] = {}
    for s in subs:
        flags = by_lang.setdefault(s.lang, {"manual": False, "auto": False})
        flags["auto" if s.is_auto else "manual"] = True

    table = Table(title=f"Subtitles ({len(by_lang)})")
    table.add_column("Lang", style="bold")
    table.add_column("Manual", justify="center")
    table.add_column("Auto", justify="center")
    for lang in sorted(by_lang.keys()):
        flags = by_lang[lang]
        table.add_row(
            lang,
            "[green]✓[/green]" if flags["manual"] else "",
            "[green]✓[/green]" if flags["auto"] else "",
        )
    return table
