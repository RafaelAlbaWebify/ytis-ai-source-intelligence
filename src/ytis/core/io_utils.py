from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def now_stamp() -> str:
    """Timestamp safe for filenames, with microseconds to avoid same-second collisions."""
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def safe_slug(text: str, fallback: str = "item", max_len: int = 90) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", (text or "").strip())
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:max_len] or fallback


def unique_child_path(parent: Path, stem: str, suffix: str = "", max_attempts: int = 200) -> Path:
    """Return a child path that does not exist, adding numeric suffixes if needed."""
    parent.mkdir(parents=True, exist_ok=True)
    candidate = parent / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate
    for index in range(2, max_attempts + 1):
        candidate = parent / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not create unique path under {parent}: {stem}{suffix}")


def read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write a text file via temp file + atomic replace.

    This avoids half-written JSON/Markdown files if the app is interrupted while saving.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    tmp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def atomic_write_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
