from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yt_dlp

from lumen_dlp.domain import AuthStrategy, OutputSpec, Subtitle
from lumen_dlp.infrastructure.browser_detect import detect_available_browsers

_AUTH_NEEDED = re.compile(
    r"(sign in|login required|members?[- ]only|private video|must be logged in|"
    r"requires.*cookies|HTTP Error 401|HTTP Error 403|Use --cookies|"
    r"Cookies are no longer valid|video is unavailable.*member)",
    re.IGNORECASE,
)


def _is_auth_error(exc: Exception) -> bool:
    return _AUTH_NEEDED.search(str(exc)) is not None


@dataclass(frozen=True, slots=True)
class InspectionEntry:
    id: str
    title: str
    artist: str
    duration: int | None
    webpage_url: str
    subtitles: tuple[Subtitle, ...]
    raw: dict


@dataclass
class YtDlpClient:
    """Single seam to yt-dlp. Owns the auth retry flow and the OutputSpec -> opts translation."""

    auth: AuthStrategy
    _learned_browser: str | None = field(default=None, init=False, repr=False)

    # --- public API -------------------------------------------------------------

    def fetch(
        self,
        url: str,
        output: OutputSpec,
        output_dir: Path,
        *,
        archive: Path | None = None,
        quiet: bool = False,
    ) -> None:
        """Download per OutputSpec. One yt-dlp invocation. Handles auth retry transparently."""
        opts = self._build_opts(output, output_dir, archive=archive, quiet=quiet)
        self._run_with_auth(lambda merged_opts: self._download(url, merged_opts), opts)

    def inspect(self, url: str) -> tuple[list[InspectionEntry], bool]:
        """Probe URL. Returns (entries, is_playlist).

        Single-video URLs return one entry with subtitle availability populated.
        Playlists return flat entries (faster) without subtitle availability.
        """
        flat_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
        }
        info = self._run_with_auth(lambda o: self._extract(url, o), flat_opts)
        entries_raw = self._unwrap_entries(info)
        is_playlist = info is not None and info.get("_type") == "playlist" and len(entries_raw) > 1

        if not is_playlist and entries_raw:
            full_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
            full_info = self._run_with_auth(lambda o: self._extract(url, o), full_opts)
            entries_raw = self._unwrap_entries(full_info)

        return ([self._to_inspection(e) for e in entries_raw], is_playlist)

    def list_playlist_entries(self, url: str) -> list[dict]:
        """Flat-extract playlist entries. Used by parallel fan-out."""
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
        }
        info = self._run_with_auth(lambda o: self._extract(url, o), opts)
        return self._unwrap_entries(info)

    # --- auth orchestration -----------------------------------------------------

    def _run_with_auth(self, op, opts: dict):
        """Run ``op(opts_with_cookies)`` applying the auth strategy.

        - force_browser: go straight with the chosen browser.
        - no_cookies: anonymous, no retry.
        - auto: anonymous first (or learned browser if a previous call needed cookies);
                on auth error, detect a browser and retry. Learned browser is cached on success.
        """
        if self.auth.mode == "force_browser":
            return op(self._with_cookies(opts, self.auth.browser, self.auth.profile))

        if self.auth.mode == "no_cookies":
            return op(opts)

        # auto
        if self._learned_browser:
            return op(self._with_cookies(opts, self._learned_browser, None))
        try:
            return op(opts)
        except yt_dlp.utils.DownloadError as exc:
            if not _is_auth_error(exc):
                raise
        browsers = detect_available_browsers()
        if not browsers:
            raise yt_dlp.utils.DownloadError(
                "Login required, but no supported browser was detected. "
                "Pass --browser <name> [--profile <path>] or log in via a supported browser "
                "(firefox/chrome/brave/edge/vivaldi)."
            )
        chosen = browsers[0]
        result = op(self._with_cookies(opts, chosen, None))
        self._learned_browser = chosen
        return result

    @staticmethod
    def _with_cookies(opts: dict, browser: str | None, profile: str | None) -> dict:
        if not browser:
            return opts
        merged = dict(opts)
        merged["cookiesfrombrowser"] = (browser, profile) if profile else (browser,)
        return merged

    # --- yt-dlp wrappers --------------------------------------------------------

    @staticmethod
    def _download(url: str, opts: dict) -> None:
        with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
            ydl.download([url])

    @staticmethod
    def _extract(url: str, opts: dict) -> dict | None:
        with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
            return ydl.extract_info(url, download=False)

    @staticmethod
    def _unwrap_entries(info: dict | None) -> list[dict]:
        if not isinstance(info, dict):
            return []
        entries = info.get("entries")
        if entries is None:
            return [dict(info)]
        return [dict(e) for e in entries if e]

    @staticmethod
    def _to_inspection(entry: dict) -> InspectionEntry:
        subs: list[Subtitle] = []
        for lang in entry.get("subtitles") or {}:
            subs.append(Subtitle(lang=lang, is_auto=False))
        for lang in entry.get("automatic_captions") or {}:
            subs.append(Subtitle(lang=lang, is_auto=True))
        artists = entry.get("artists") or []
        artist = ", ".join(a["name"] for a in artists) or entry.get("uploader") or "—"
        return InspectionEntry(
            id=entry.get("id") or "",
            title=entry.get("title") or "—",
            artist=artist,
            duration=entry.get("duration"),
            webpage_url=entry.get("webpage_url") or entry.get("url") or "",
            subtitles=tuple(subs),
            raw=entry,
        )

    # --- OutputSpec -> yt-dlp opts ---------------------------------------------

    @staticmethod
    def _build_opts(
        output: OutputSpec,
        output_dir: Path,
        *,
        archive: Path | None,
        quiet: bool,
    ) -> dict:
        opts: dict = {
            "outtmpl": str(output_dir / "%(title)s [%(id)s].%(ext)s"),
            "ignoreerrors": True,
            "noplaylist": False,
            "postprocessors": [],
        }
        if quiet:
            opts["quiet"] = True
            opts["no_warnings"] = True
            opts["noprogress"] = True
        if archive is not None:
            archive.parent.mkdir(parents=True, exist_ok=True)
            opts["download_archive"] = str(archive)

        want_audio = output.audio is not None
        want_video = output.video is not None
        want_subs = output.subs is not None

        if want_video:
            v = output.video
            height_filter = f"[height<={v.max_height}]" if v.max_height else ""
            opts["format"] = f"bv*{height_filter}+ba/b{height_filter}"
            opts["merge_output_format"] = v.format.value
            if want_audio:
                # Keep the merged video AND extract audio to a separate file.
                opts["keepvideo"] = True
                opts["postprocessors"].append(
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": output.audio.format.value,
                        "preferredquality": output.audio.quality,
                    }
                )
        elif want_audio:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"].append(
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": output.audio.format.value,
                    "preferredquality": output.audio.quality,
                }
            )
        elif want_subs:
            # subs-only: don't pull any media file
            opts["skip_download"] = True
            opts["format"] = "bestaudio/best"  # ignored because skip_download

        if want_subs:
            s = output.subs
            opts["writesubtitles"] = True
            opts["writeautomaticsub"] = s.include_auto
            opts["subtitleslangs"] = list(s.langs) if s.langs else ["all"]
            opts["subtitlesformat"] = s.format.value
            opts["postprocessors"].append(
                {"key": "FFmpegSubtitlesConvertor", "format": s.format.value}
            )

        if want_audio or want_video:
            if output.embed_metadata:
                opts["postprocessors"].append({"key": "FFmpegMetadata"})
            if output.embed_thumbnail:
                opts["writethumbnail"] = True
                opts["postprocessors"].append({"key": "EmbedThumbnail"})

        return opts
