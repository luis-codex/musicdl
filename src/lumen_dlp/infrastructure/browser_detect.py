from __future__ import annotations

import os
import platform
from pathlib import Path

_PRIORITY = ["firefox", "chrome", "brave", "edge", "vivaldi", "chromium", "safari"]


def _candidate_paths() -> dict[str, list[Path]]:
    system = platform.system()
    home = Path.home()

    if system == "Windows":
        appdata = Path(os.environ.get("APPDATA") or (home / "AppData" / "Roaming"))
        local = Path(os.environ.get("LOCALAPPDATA") or (home / "AppData" / "Local"))
        return {
            "firefox": [appdata / "Mozilla" / "Firefox" / "Profiles"],
            "chrome": [local / "Google" / "Chrome" / "User Data"],
            "brave": [local / "BraveSoftware" / "Brave-Browser" / "User Data"],
            "edge": [local / "Microsoft" / "Edge" / "User Data"],
            "vivaldi": [local / "Vivaldi" / "User Data"],
        }

    if system == "Darwin":
        base = home / "Library" / "Application Support"
        return {
            "firefox": [base / "Firefox" / "Profiles"],
            "chrome": [base / "Google" / "Chrome"],
            "brave": [base / "BraveSoftware" / "Brave-Browser"],
            "edge": [base / "Microsoft Edge"],
            "vivaldi": [base / "Vivaldi"],
            "safari": [home / "Library" / "Cookies"],
        }

    cfg = home / ".config"
    return {
        "firefox": [
            home / ".mozilla" / "firefox",
            home / "snap" / "firefox" / "common" / ".mozilla" / "firefox",
        ],
        "chrome": [cfg / "google-chrome"],
        "brave": [cfg / "BraveSoftware" / "Brave-Browser"],
        "edge": [cfg / "microsoft-edge"],
        "chromium": [cfg / "chromium"],
        "vivaldi": [cfg / "vivaldi"],
    }


def detect_available_browsers() -> list[str]:
    """Return the browsers with a detectable profile directory on this system, in priority order."""
    paths = _candidate_paths()
    return [name for name in _PRIORITY if name in paths and any(p.exists() for p in paths[name])]
