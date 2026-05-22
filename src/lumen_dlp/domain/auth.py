from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AuthMode = Literal["auto", "force_browser", "no_cookies"]


@dataclass(frozen=True, slots=True)
class AuthStrategy:
    """How the client should authenticate.

    - ``auto``: anonymous first; on auth-needed error, retry with browser cookies
      (auto-detected unless ``browser`` is set as a hint).
    - ``force_browser``: skip anonymous, go straight with the given browser+profile.
    - ``no_cookies``: anonymous only; never retry with cookies.
    """

    mode: AuthMode = "auto"
    browser: str | None = None
    profile: str | None = None

    @classmethod
    def auto(cls) -> AuthStrategy:
        return cls(mode="auto")

    @classmethod
    def force_browser(cls, browser: str, profile: str | None = None) -> AuthStrategy:
        return cls(mode="force_browser", browser=browser, profile=profile)

    @classmethod
    def no_cookies(cls) -> AuthStrategy:
        return cls(mode="no_cookies")
