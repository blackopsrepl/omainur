"""Where generated MP3s land. Override with OST_DIR if the library isn't ~/Music/ost."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OST_DIR = Path(os.environ.get("OST_DIR", Path.home() / "Music" / "ost"))


def track_path(pool: str, name: str) -> str:
    dest = OST_DIR / pool / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    return str(dest)
