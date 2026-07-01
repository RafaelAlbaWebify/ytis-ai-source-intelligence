from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ytis.core.paths import default_downloads_dir, project_root
from ytis.core.registry import read_project_summaries


@dataclass
class AppState:
    app_version: str
    project_root_path: Path = field(default_factory=project_root)
    downloads_dir: Path = field(default_factory=default_downloads_dir)
    current_project: dict[str, Any] = field(default_factory=dict)

    def projects_dir(self) -> Path:
        return self.project_root_path / "projects"

    def load_projects(self) -> list[dict[str, Any]]:
        return read_project_summaries(self.projects_dir())

    def load_latest_project(self) -> dict[str, Any]:
        projects = self.load_projects()
        self.current_project = projects[0] if projects else {}
        return self.current_project

    def set_current_project(self, project: dict[str, Any]) -> None:
        self.current_project = project or {}


def fmt_int(value: Any, default: str = "0") -> str:
    try:
        if value in {None, ""}:
            return default
        return f"{int(value):,}"
    except Exception:
        return default


def val(project: dict[str, Any], key: str, default: str = "-") -> str:
    value = project.get(key, default)
    if value is None or value == "":
        return default
    return str(value)


def short_path(value: Any, max_len: int = 64) -> str:
    text = str(value or "-")
    if len(text) <= max_len:
        return text
    return "..." + text[-(max_len - 3):]
