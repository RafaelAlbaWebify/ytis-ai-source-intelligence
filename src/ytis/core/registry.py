from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ytis.core.io_utils import atomic_write_json, read_json


def registry_path(base_projects_dir: Path) -> Path:
    return base_projects_dir / "projects_index.json"


def read_registry(base_projects_dir: Path) -> dict[str, Any]:
    data = read_json(registry_path(base_projects_dir), {"projects": []})
    return data if isinstance(data, dict) else {"projects": []}


def write_registry(base_projects_dir: Path, data: dict[str, Any]) -> None:
    base_projects_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(registry_path(base_projects_dir), data)


def upsert_project(base_projects_dir: Path, summary: dict[str, Any]) -> None:
    data = read_registry(base_projects_dir)
    projects = data.setdefault("projects", [])

    now = datetime.now().isoformat(timespec="seconds")
    summary["last_updated_at"] = now

    for idx, project in enumerate(projects):
        if project.get("name") == summary.get("name"):
            created_at = project.get("created_at") or now
            merged = {**project, **summary, "created_at": created_at}
            projects[idx] = merged
            break
    else:
        summary["created_at"] = now
        projects.append(summary)

    projects.sort(key=lambda p: p.get("last_updated_at", ""), reverse=True)
    write_registry(base_projects_dir, data)


def read_project_summaries(base_projects_dir: Path) -> list[dict[str, Any]]:
    data = read_registry(base_projects_dir)
    projects = data.get("projects", [])
    if isinstance(projects, list):
        return [p for p in projects if isinstance(p, dict)]
    return []
