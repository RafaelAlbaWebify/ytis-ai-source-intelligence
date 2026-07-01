from __future__ import annotations

import re
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_downloads_dir() -> Path:
    return Path.home() / "Downloads"


def safe_name(value: str) -> str:
    value = value.strip()
    value = re.sub(r'[<>:"/\\|?*]+', "_", value)
    value = re.sub(r"\s+", "_", value)
    value = value.strip("._ ")
    return value or "YTIS_Project"
