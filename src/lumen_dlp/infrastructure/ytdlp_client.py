from __future__ import annotations

from dataclasses import dataclass

import yt_dlp

from lumen_dlp.domain import CookieSource


@dataclass(frozen=True, slots=True)
class YtDlpClient:
    """Single seam to yt-dlp. The rest of the app does not import yt_dlp."""

    cookies: CookieSource

    def list_playlist_entries(self, url: str) -> list[dict]:
        """Return flat entries (id, title, duration, artists, uploader, url)."""
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "cookiesfrombrowser": self.cookies.as_ydl_tuple(),
        }
        with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(url, download=False)
        if not isinstance(info, dict):
            return []
        entries = info.get("entries")
        if entries is None:
            return [dict(info)]
        return [dict(e) for e in entries if e]

    def download(self, url: str, opts: dict) -> int:
        """Run yt-dlp with the given opts. Returns 0 on success."""
        merged = {"cookiesfrombrowser": self.cookies.as_ydl_tuple(), **opts}
        with yt_dlp.YoutubeDL(merged) as ydl:  # type: ignore[arg-type]
            return int(ydl.download([url]) or 0)
