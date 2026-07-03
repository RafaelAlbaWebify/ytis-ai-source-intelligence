from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _safe_read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def project_root_from_state(state: Any) -> Path:
    for name in ("project_root_path", "project_root"):
        value = getattr(state, name, None)
        if value:
            return Path(value)
    return Path.cwd()


def current_mission_id(state: Any) -> str:
    root = project_root_from_state(state)
    data = _safe_read_json(root / "ytis_state" / "current_mission.json")
    return str(data.get("mission_id") or "")


def _mission_json_files(root: Path) -> list[Path]:
    missions_root = root / "missions"
    if not missions_root.exists():
        return []
    return sorted(missions_root.glob("*/mission.json"), reverse=True)


def current_mission_data(state: Any) -> dict[str, Any]:
    root = project_root_from_state(state)
    wanted_id = current_mission_id(state)
    records: list[dict[str, Any]] = []

    for path in _mission_json_files(root):
        data = _safe_read_json(path)
        if not data:
            continue
        data["_metadata_path"] = str(path)
        data["_folder"] = str(path.parent)
        records.append(data)
        if wanted_id and str(data.get("mission_id") or "") == wanted_id:
            return data

    active = [m for m in records if str(m.get("status") or "") == "active"]
    if active:
        return active[0]
    visible = [m for m in records if str(m.get("status") or "") != "archived"]
    if visible:
        return visible[0]
    return records[0] if records else {}


def current_mission_project_names(state: Any) -> list[str]:
    data = current_mission_data(state)
    raw = data.get("projects") or []
    if isinstance(raw, str):
        raw = [raw]
    result: list[str] = []
    for value in raw:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def preferred_project_name(state: Any, available_names: list[str] | None = None) -> str:
    allowed = set(available_names or [])

    for name in current_mission_project_names(state):
        if not allowed or name in allowed:
            return name

    current_project = getattr(state, "current_project", None) or {}
    if isinstance(current_project, dict):
        name = str(current_project.get("name") or "").strip()
        if name and (not allowed or name in allowed):
            return name

    if available_names:
        return available_names[0]
    return ""


def sidebar_context_label(state: Any) -> str:
    mission = current_mission_data(state)
    projects = current_mission_project_names(state)
    if len(projects) == 1:
        return projects[0]
    if len(projects) > 1:
        return projects[0] + f" + {len(projects) - 1}"

    current_project = getattr(state, "current_project", None) or {}
    if isinstance(current_project, dict):
        name = str(current_project.get("name") or "").strip()
        if name:
            return name

    mission_name = str(mission.get("name") or "").strip()
    if mission_name:
        return "Mission: " + mission_name
    return "No active project"
