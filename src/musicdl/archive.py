from __future__ import annotations

import threading
from pathlib import Path


def read_ids(archive: Path) -> set[str]:
    if not archive.exists():
        return set()
    ids: set[str] = set()
    for line in archive.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            ids.add(parts[1])
    return ids


def append_id(archive: Path, video_id: str, lock: threading.Lock) -> None:
    with lock, archive.open("a", encoding="utf-8") as f:
        f.write(f"youtube {video_id}\n")
