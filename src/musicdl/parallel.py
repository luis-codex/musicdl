from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from rich.console import Console

from musicdl.archive import append_id, read_ids
from musicdl.rendering import make_progress

Worker = Callable[[dict], None]
"""Function that downloads a single entry. Receives the yt-dlp entry dict."""


def run_parallel(
    *,
    entries: list[dict],
    worker: Worker,
    concurrent: int,
    archive_file: Path | None,
    console: Console,
    label: str,
) -> int:
    """Fan out `worker` across `concurrent` threads, honoring the archive.

    Returns the count of failures (0 = full success).
    """
    already = read_ids(archive_file) if archive_file else set()
    pending = [e for e in entries if e.get("id") and e["id"] not in already]
    skipped = len(entries) - len(pending)

    if not pending:
        console.print(f"[green]✓[/green] Nothing to download ({skipped} already in archive).")
        return 0

    console.print(
        f"[dim]Parallel:[/dim] {concurrent} workers · "
        f"[dim]queued:[/dim] {len(pending)} · [dim]skipped:[/dim] {skipped}"
    )

    archive_lock = threading.Lock()
    failures: list[tuple[str, str]] = []
    progress = make_progress(console)

    with progress:
        overall = progress.add_task(f"[bold]{label}[/bold]", total=len(pending))
        with ThreadPoolExecutor(max_workers=concurrent) as pool:
            futures = {pool.submit(worker, e): e for e in pending}
            for future in as_completed(futures):
                entry = futures[future]
                title = entry.get("title") or entry.get("id") or "?"
                try:
                    future.result()
                except Exception as exc:  # noqa: BLE001
                    failures.append((title, str(exc)))
                    console.print(f"[red]✗[/red] {title} — {exc}")
                else:
                    if archive_file and entry.get("id"):
                        append_id(archive_file, entry["id"], archive_lock)
                    console.print(f"[green]✓[/green] {title}")
                finally:
                    progress.advance(overall)

    if failures:
        console.print(f"[yellow]{len(failures)} failed.[/yellow]")
        return 1
    return 0


def entry_url(entry: dict) -> str:
    return entry.get("url") or entry.get("webpage_url") or entry["id"]
