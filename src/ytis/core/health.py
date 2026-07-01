from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from ytis.core.paths import default_downloads_dir, project_root


def _run_text(args: list[str], timeout: int = 12) -> str:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        text = (completed.stdout or completed.stderr or "").strip()
        return text or f"exit code {completed.returncode}"
    except Exception as exc:
        return f"unavailable: {exc}"


def get_health_snapshot() -> dict[str, Any]:
    root = project_root()
    venv_python = root / ".venv" / "Scripts" / "python.exe"

    if venv_python.exists():
        yt_dlp_version = _run_text([str(venv_python), "-m", "yt_dlp", "--version"])
    else:
        yt_dlp_version = _run_text([sys.executable, "-m", "yt_dlp", "--version"])

    return {
        "pid": os.getpid(),
        "python": sys.executable,
        "python_version": sys.version.split()[0],
        "yt_dlp_version": yt_dlp_version,
        "project_root": str(root),
        "projects_dir": str(root / "projects"),
        "downloads_dir": str(default_downloads_dir()),
        "venv_python_exists": venv_python.exists(),
    }
