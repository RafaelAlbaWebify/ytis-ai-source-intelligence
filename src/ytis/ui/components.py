from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from nicegui import ui

from ytis.ui.formatting import compact_number, full_number
from ytis.ui.state import fmt_int, short_path, val


def open_path(path: str | Path) -> None:
    path_str = str(path or "").strip()
    if not path_str:
        ui.notify("No path available", type="warning")
        return

    try:
        if os.name == "nt":
            os.startfile(path_str)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path_str])
    except Exception as exc:
        ui.notify(f"Could not open path: {exc}", type="negative")


def page_title(title: str, subtitle: str = "") -> None:
    with ui.row().classes("w-full justify-between items-center"):
        with ui.column().classes("gap-0"):
            ui.label(title).classes("text-3xl font-bold")
            if subtitle:
                ui.label(subtitle).classes("text-sm text-slate-300")
        ui.button("New Research Pack", icon="add", on_click=lambda: ui.navigate.to("/build"), color="primary")


def _metric_card(label: str, display: str, caption: str = "", full_value: str = "") -> None:
    with ui.card().classes("ytis-metric p-4"):
        ui.label(label).classes("text-sm text-slate-400")
        value_label = ui.label(display).classes("text-2xl font-bold whitespace-nowrap")
        if full_value:
            value_label.tooltip(full_value)
        if caption:
            ui.label(caption).classes("text-xs text-slate-500")


def command_metric_row(project: dict[str, Any]) -> None:
    """Compact metric row used by the Dashboard.

    Large numbers are abbreviated to avoid cell overflow, while the full value is
    still available as a tooltip.
    """
    videos = project.get("videos_found", 0)
    transcripts = project.get("transcripts_created", 0)
    missing = project.get("missing_subtitles", 0)
    words = project.get("total_words", 0)
    zip_status = "Ready" if project.get("zip_path") else "Missing"

    with ui.grid(columns=5).classes("w-full gap-3"):
        _metric_card("Videos", compact_number(videos), "indexed", full_number(videos))
        _metric_card("Transcripts", compact_number(transcripts), "clean TXT", full_number(transcripts))
        _metric_card("Missing", compact_number(missing), "subtitle gaps", full_number(missing))
        _metric_card("Words", compact_number(words), "analysis volume", full_number(words))
        _metric_card("ZIP", zip_status, "upload pack")


def health_card(app_version: str, compact: bool = False) -> None:
    import os
    import platform
    import sys

    with ui.card().classes("ytis-card p-5 w-full"):
        ui.label("Health").classes("text-xl font-bold")
        rows = [
            ("App version", app_version),
            ("PID", str(os.getpid())),
            ("Python", platform.python_version()),
        ]
        if not compact:
            rows.append(("Executable", sys.executable))

        for key, value in rows:
            with ui.row().classes("w-full justify-between gap-3 border-b border-slate-800 py-1"):
                ui.label(key).classes("text-sm text-slate-400")
                ui.label(value).classes("text-sm text-right break-all")


def recent_projects_list(projects: list[dict[str, Any]], limit: int = 5) -> None:
    with ui.card().classes("ytis-card p-5 w-full"):
        with ui.row().classes("w-full justify-between items-center"):
            ui.label("Recent Projects").classes("text-xl font-bold")
            ui.button("View All", icon="arrow_forward", on_click=lambda: ui.navigate.to("/projects")).props("outline dense")

        if not projects:
            ui.label("No recent projects.").classes("text-slate-400")
            return

        for project in projects[:limit]:
            with ui.row().classes("w-full justify-between items-center border-b border-slate-800 py-2"):
                with ui.column().classes("gap-0"):
                    ui.label(val(project, "name", "Unnamed")).classes("font-bold")
                    words = compact_number(project.get("total_words", 0))
                    transcripts = compact_number(project.get("transcripts_created", 0))
                    ui.label(f"{transcripts} transcripts | {words} words").classes("text-xs text-slate-400")
                with ui.row().classes("gap-1"):
                    ui.button("Build", on_click=lambda: ui.navigate.to("/build")).props("outline dense")
                    if project.get("project_dir"):
                        ui.button("Folder", on_click=lambda p=project: open_path(str(p["project_dir"]))).props("outline dense")
                    if project.get("zip_path"):
                        ui.button("ZIP", on_click=lambda p=project: open_path(str(p["zip_path"]))).props("outline dense")
