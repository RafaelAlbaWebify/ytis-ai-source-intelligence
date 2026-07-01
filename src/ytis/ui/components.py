from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from nicegui import ui

from ytis.core.health import get_health_snapshot
from ytis.ui.state import AppState, fmt_int, short_path, val


YOUTUBE_VIDEO_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})")
CHANNEL_HANDLE_RE = re.compile(r"youtube\.com/@([^/?#]+)")


def open_path(path: str | Path) -> None:
    path_obj = Path(path)
    if path_obj.exists():
        os.startfile(str(path_obj))


def page_title(title: str, subtitle: str, show_action: bool = True) -> None:
    with ui.row().classes("w-full items-center justify-between mb-1"):
        with ui.column().classes("gap-0"):
            ui.label(title).classes("text-3xl font-bold")
            ui.label(subtitle).classes("text-sm text-slate-300")
        if show_action:
            ui.button("New Research Pack", icon="add", on_click=lambda: ui.navigate.to("/build"), color="primary").classes("px-5")


def metric_card(title: str, value: str, note: str = "") -> None:
    with ui.card().classes("ytis-metric p-4"):
        ui.label(title).classes("text-sm text-slate-400")
        ui.label(value).classes("text-2xl font-bold")
        if note:
            ui.label(note).classes("text-xs text-slate-500")


def project_summary_card(project: dict[str, Any], title: str = "Current Project") -> None:
    with ui.card().classes("ytis-card p-5 w-full"):
        ui.label(title).classes("text-xl font-bold")
        if not project:
            ui.label("No project built yet. Create a research pack to populate this view.").classes("text-slate-400")
            ui.button("Build Research Pack", icon="rocket_launch", on_click=lambda: ui.navigate.to("/build"), color="primary")
            return

        with ui.row().classes("w-full gap-4 items-start"):
            with ui.column().classes("gap-1 flex-1"):
                ui.label(val(project, "name", "Unnamed project")).classes("text-2xl font-bold")
                ui.label(val(project, "url")).classes("text-xs text-blue-300 break-all")
                ui.label(f"Mode: {val(project, 'build_mode', '-')}").classes("text-sm text-slate-300")
                ui.label(f"Built: {val(project, 'built_at', val(project, 'last_updated_at', '-'))}").classes("text-xs text-slate-500")
            with ui.row().classes("gap-2"):
                if project.get("project_dir"):
                    ui.button("Open Folder", icon="folder_open", on_click=lambda p=project: open_path(str(p["project_dir"]))).props("outline")
                if project.get("zip_path"):
                    ui.button("Open ZIP", icon="inventory_2", on_click=lambda p=project: open_path(str(p["zip_path"]))).props("outline")

        ui.separator().classes("bg-slate-700 my-3")
        with ui.grid(columns=5).classes("w-full gap-3"):
            metric_card("Videos", val(project, "videos_found", "0"))
            metric_card("Transcripts", val(project, "transcripts_created", "0"))
            metric_card("Missing", val(project, "missing_subtitles", "0"))
            metric_card("Words", fmt_int(project.get("total_words")))
            metric_card("ZIP", "Ready" if project.get("zip_path") else "Missing")


def command_metric_row(project: dict[str, Any]) -> None:
    with ui.grid(columns=5).classes("w-full gap-3"):
        metric_card("Videos", val(project, "videos_found", "0"), "indexed")
        metric_card("Transcripts", val(project, "transcripts_created", "0"), "clean TXT")
        metric_card("Missing", val(project, "missing_subtitles", "0"), "subtitle gaps")
        metric_card("Words", fmt_int(project.get("total_words")), "analysis volume")
        metric_card("ZIP", "Ready" if project.get("zip_path") else "Missing", "upload pack")


def quick_actions_card(project: dict[str, Any]) -> None:
    with ui.card().classes("ytis-card p-5 w-full"):
        ui.label("Quick Actions").classes("text-xl font-bold")
        with ui.grid(columns=2).classes("w-full gap-3 mt-2"):
            ui.button("Build Pack", icon="rocket_launch", on_click=lambda: ui.navigate.to("/build"), color="primary").classes("w-full")
            ui.button("Search Transcripts", icon="search", on_click=lambda: ui.navigate.to("/search")).props("outline").classes("w-full")
            if project.get("project_dir"):
                ui.button("Open Project Folder", icon="folder_open", on_click=lambda p=project: open_path(str(p["project_dir"]))).props("outline").classes("w-full")
            else:
                ui.button("Open Project Folder", icon="folder_open").props("outline disable").classes("w-full")
            if project.get("zip_path"):
                ui.button("Open ZIP", icon="inventory_2", on_click=lambda p=project: open_path(str(p["zip_path"]))).props("outline").classes("w-full")
            else:
                ui.button("Open ZIP", icon="inventory_2").props("outline disable").classes("w-full")


def recent_projects_list(projects: list[dict[str, Any]], limit: int = 6) -> None:
    with ui.card().classes("ytis-card p-5 w-full"):
        with ui.row().classes("w-full justify-between items-center"):
            ui.label("Recent Projects").classes("text-xl font-bold")
            ui.button("View all", icon="arrow_forward", on_click=lambda: ui.navigate.to("/projects")).props("outline")
        if not projects:
            ui.label("No saved projects yet.").classes("text-slate-400")
            return

        for project in projects[:limit]:
            with ui.row().classes("w-full items-center justify-between border-b border-slate-700 py-2"):
                with ui.column().classes("gap-0"):
                    ui.label(val(project, "name", "Unnamed")).classes("font-bold")
                    ui.label(f"{val(project, 'transcripts_created', '0')} transcripts | {fmt_int(project.get('total_words'))} words").classes("text-xs text-slate-400")
                with ui.row().classes("gap-2"):
                    ui.button("Build", on_click=lambda p=project: ui.navigate.to("/build")).props("outline dense")
                    if project.get("project_dir"):
                        ui.button("Folder", on_click=lambda p=project: open_path(str(p["project_dir"]))).props("outline dense")
                    if project.get("zip_path"):
                        ui.button("ZIP", on_click=lambda p=project: open_path(str(p["zip_path"]))).props("outline dense")


def health_card(app_version: str, compact: bool = False) -> None:
    health = get_health_snapshot()
    with ui.card().classes("ytis-card p-5 w-full"):
        ui.label("Health").classes("text-xl font-bold")
        rows = [
            ("App version", app_version),
            ("PID", str(health.get("pid", "-"))),
            ("Python", str(health.get("python_version", "-"))),
            ("yt-dlp", str(health.get("yt_dlp_version", "-"))),
            ("Project root", short_path(health.get("project_root", "-"), 80)),
            ("Downloads", short_path(health.get("downloads_dir", "-"), 80)),
        ]
        if compact:
            rows = rows[:4]
        for key, value in rows:
            with ui.row().classes("w-full justify-between gap-4"):
                ui.label(key).classes("text-sm text-slate-400")
                ui.label(value).classes("text-sm text-right break-all")


def source_preview(url: str, project_name: str, compact: bool = False) -> None:
    video_match = YOUTUBE_VIDEO_RE.search(url or "")
    if video_match:
        video_id = video_match.group(1)
        image_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        source_type = "Video"
        subtitle = f"Video ID: {video_id}"
    else:
        handle_match = CHANNEL_HANDLE_RE.search(url or "")
        handle = handle_match.group(1) if handle_match else "youtube-channel"
        image_url = "https://www.youtube.com/img/desktop/yt_1200.png"
        source_type = "Channel"
        subtitle = f"@{handle}"

    image_height = "150px" if compact else "210px"

    with ui.card().classes("ytis-card p-5 w-full"):
        with ui.row().classes("w-full justify-between items-center"):
            ui.label("Source Preview").classes("text-xl font-bold")
            ui.label(source_type).classes("text-xs text-red-400")
        ui.image(image_url).classes("w-full rounded-xl").style(f"height: {image_height}; object-fit: cover; background: #0f172a;")
        ui.label(project_name or "YouTube Source").classes("text-lg font-bold")
        ui.label(subtitle).classes("text-sm text-slate-400")
        ui.label(url or "-").classes("text-xs text-blue-300 break-all")
        ui.label("Video URLs show a thumbnail. Channel screenshot capture is planned.").classes("text-xs text-slate-500")
