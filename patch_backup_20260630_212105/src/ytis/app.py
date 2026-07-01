from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Optional, Any

from nicegui import ui

from ytis.core.builder import BuildOptions, build_research_pack
from ytis.core.health import get_health_snapshot
from ytis.core.paths import default_downloads_dir, project_root
from ytis.core.registry import read_project_summaries

APP_VERSION = "v0.2.5"
CURRENT_LOG: list[str] = []

YOUTUBE_VIDEO_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})")
CHANNEL_HANDLE_RE = re.compile(r"youtube\.com/@([^/?#]+)")
SOURCE_PLACEHOLDER = "data:image/svg+xml;utf8,%0A%3Csvg%20xmlns%3D%27http%3A//www.w3.org/2000/svg%27%20width%3D%27900%27%20height%3D%27500%27%20viewBox%3D%270%200%20900%20500%27%3E%0A%20%20%3Cdefs%3E%0A%20%20%20%20%3ClinearGradient%20id%3D%27bg%27%20x1%3D%270%27%20y1%3D%270%27%20x2%3D%271%27%20y2%3D%271%27%3E%0A%20%20%20%20%20%20%3Cstop%20offset%3D%270%25%27%20stop-color%3D%27%2307111f%27/%3E%0A%20%20%20%20%20%20%3Cstop%20offset%3D%27100%25%27%20stop-color%3D%27%23172554%27/%3E%0A%20%20%20%20%3C/linearGradient%3E%0A%20%20%20%20%3ClinearGradient%20id%3D%27bar%27%20x1%3D%270%27%20y1%3D%270%27%20x2%3D%271%27%20y2%3D%270%27%3E%0A%20%20%20%20%20%20%3Cstop%20offset%3D%270%25%27%20stop-color%3D%27%23111827%27/%3E%0A%20%20%20%20%20%20%3Cstop%20offset%3D%27100%25%27%20stop-color%3D%27%237f1d1d%27/%3E%0A%20%20%20%20%3C/linearGradient%3E%0A%20%20%3C/defs%3E%0A%20%20%3Crect%20width%3D%27900%27%20height%3D%27500%27%20rx%3D%2724%27%20fill%3D%27url%28%23bg%29%27/%3E%0A%20%20%3Crect%20x%3D%2730%27%20y%3D%2730%27%20width%3D%27840%27%20height%3D%27150%27%20rx%3D%2722%27%20fill%3D%27url%28%23bar%29%27/%3E%0A%20%20%3Ctext%20x%3D%2764%27%20y%3D%2792%27%20fill%3D%27white%27%20font-size%3D%2734%27%20font-family%3D%27Arial%27%20font-weight%3D%27700%27%3EYouTube%20Source%20Preview%3C/text%3E%0A%20%20%3Ctext%20x%3D%2764%27%20y%3D%27132%27%20fill%3D%27%23cbd5e1%27%20font-size%3D%2720%27%20font-family%3D%27Arial%27%3EChannel%20screenshot%20or%20video%20thumbnail%3C/text%3E%0A%20%20%3Ccircle%20cx%3D%27135%27%20cy%3D%27300%27%20r%3D%2770%27%20fill%3D%27%23ef4444%27/%3E%0A%20%20%3Cpolygon%20points%3D%27115%2C260%20115%2C340%20180%2C300%27%20fill%3D%27white%27/%3E%0A%20%20%3Ctext%20x%3D%27240%27%20y%3D%27290%27%20fill%3D%27white%27%20font-size%3D%2730%27%20font-family%3D%27Arial%27%20font-weight%3D%27700%27%3EPreview%20ready%3C/text%3E%0A%20%20%3Ctext%20x%3D%27240%27%20y%3D%27330%27%20fill%3D%27%2394a3b8%27%20font-size%3D%2719%27%20font-family%3D%27Arial%27%3EOne%20visual%20source%20reference%20only%3C/text%3E%0A%3C/svg%3E%0A"


def open_path(path: str | Path) -> None:
    path_obj = Path(path)
    if path_obj.exists():
        os.startfile(str(path_obj))


def extract_video_id(url: str) -> str | None:
    match = YOUTUBE_VIDEO_RE.search(url or "")
    return match.group(1) if match else None


def source_meta(url: str, project_name: str) -> dict[str, str]:
    url = (url or "").strip()
    project_name = (project_name or "").strip()
    video_id = extract_video_id(url)
    if video_id:
        return {
            "type": "Video",
            "title": project_name or "Selected YouTube Video",
            "subtitle": f"Video ID: {video_id}",
            "image": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            "status": "Video thumbnail loaded.",
            "url": url or "-",
        }

    handle_match = CHANNEL_HANDLE_RE.search(url)
    handle = handle_match.group(1) if handle_match else "youtube-channel"
    return {
        "type": "Channel",
        "title": project_name or handle,
        "subtitle": f"@{handle}",
        "image": SOURCE_PLACEHOLDER,
        "status": "Channel placeholder. Real screenshot capture comes next.",
        "url": url or "-",
    }


def short_path(value: str, max_len: int = 48) -> str:
    value = value or "-"
    if len(value) <= max_len:
        return value
    return "..." + value[-(max_len - 3):]


@ui.page("/")
def index() -> None:
    ui.add_head_html("""
    <style>
    body {
        background: radial-gradient(circle at top, #091426 0%, #07111f 55%, #050b16 100%);
    }
    .ytis-shell { gap: 0; }
    .ytis-sidebar {
        width: 270px;
        min-height: 100vh;
        background: linear-gradient(180deg, rgba(8,19,33,0.98), rgba(6,14,25,0.98));
        border-right: 1px solid rgba(255,255,255,0.07);
    }
    .ytis-main { min-height: 100vh; max-width: 1660px; }
    .ytis-card {
        background: linear-gradient(145deg, rgba(15,27,45,0.98), rgba(18,31,51,0.95));
        border: 1px solid rgba(88, 136, 255, 0.16);
        border-radius: 18px;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.24);
    }
    .ytis-mini-card {
        background: rgba(15,27,45,0.78);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 14px;
    }
    .ytis-metric {
        background: linear-gradient(180deg, rgba(16,27,45,0.96), rgba(12,20,35,0.92));
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
    }
    .q-field__control { min-height: 38px !important; }
    .q-field__label { font-size: 12px !important; }
    .q-field__native { font-size: 13px !important; }
    .q-btn { font-size: 12px !important; }
    .ytis-process-log {
        font-family: Consolas, monospace;
        font-size: 12px;
        line-height: 1.45;
    }

    .ytis-sidebar .q-btn { min-height: 32px !important; }
    .ytis-sidebar .ytis-mini-card { box-shadow: none; }
    </style>
    """)

    projects_dir = project_root() / "projects"
    project_summaries = read_project_summaries(projects_dir)
    latest_project = project_summaries[0] if project_summaries else {}
    health = get_health_snapshot()

    def value(project: dict[str, Any], key: str, default: str = "-") -> str:
        raw = project.get(key, default)
        if raw is None or raw == "":
            return default
        return str(raw)

    with ui.row().classes("w-full text-white ytis-shell"):
        with ui.column().classes("ytis-sidebar p-4 gap-2"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("smart_display").classes("text-5xl text-red-500")
                with ui.column().classes("gap-0"):
                    ui.label("YTIS").classes("text-3xl font-bold text-blue-400")
                    ui.label("YouTube Intelligence System").classes("text-sm text-slate-300")
                    ui.label(APP_VERSION).classes("text-xs text-slate-500")

            with ui.row().classes("gap-2 w-full"):
                dashboard_button = ui.button("Dashboard", icon="home").classes("flex-1 justify-start")
                projects_button = ui.button("Projects", icon="folder").classes("flex-1 justify-start").props("outline dense")

            current_project_title = ui.label(value(latest_project, "name", "No project loaded")).classes("font-bold text-base")
            current_project_subtitle = ui.label("Full Channel Pack" if latest_project.get("name") else "Current project").classes("text-xs text-slate-400")
            current_mode = ui.label(value(latest_project, "build_mode", "reuse") + " mode").classes("text-xs text-blue-300")
            current_videos = ui.label(value(latest_project, "videos_found", "0")).classes("font-bold")
            current_transcripts = ui.label(value(latest_project, "transcripts_created", "0")).classes("font-bold")
            current_words = ui.label(f"{int(latest_project.get('total_words', 0)):,}" if str(latest_project.get("total_words", "")).isdigit() else "0").classes("font-bold")
            current_zip = ui.label("Ready" if latest_project.get("zip_path") else "Not ready").classes("font-bold text-green-400" if latest_project.get("zip_path") else "font-bold text-slate-400")

            with ui.card().classes("ytis-mini-card p-3 w-full"):
                ui.label("CURRENT PROJECT").classes("text-[11px] text-slate-400")
                current_project_title
                current_project_subtitle
                current_mode
                ui.separator().classes("bg-slate-700 my-2")
                with ui.column().classes("gap-1"):
                    with ui.row().classes("items-center justify-between"):
                        ui.label("Videos").classes("text-sm text-slate-400")
                        current_videos
                    with ui.row().classes("items-center justify-between"):
                        ui.label("Transcripts").classes("text-sm text-slate-400")
                        current_transcripts
                    with ui.row().classes("items-center justify-between"):
                        ui.label("Words").classes("text-sm text-slate-400")
                        current_words
                    with ui.row().classes("items-center justify-between"):
                        ui.label("ZIP").classes("text-sm text-slate-400")
                        current_zip

            with ui.card().classes("ytis-mini-card p-2 w-full"):
                ui.label("QUICK ACTIONS").classes("text-[11px] text-slate-400")
                quick_new_project_button = ui.button("New Project", icon="add", color="primary").classes("w-full mt-1").props("dense")
                quick_load_last_button = ui.button("Load Last", icon="bolt").classes("w-full").props("outline dense")
                quick_open_downloads_button = ui.button("Open Downloads", icon="folder_open").classes("w-full").props("outline dense")
                quick_open_zip_button = ui.button("Open Last ZIP", icon="inventory_2").classes("w-full").props("outline dense")
                quick_open_project_button = ui.button("Open Project", icon="folder").classes("w-full").props("outline dense")

            with ui.card().classes("ytis-mini-card p-2 w-full"):
                ui.label("SYSTEM").classes("text-[11px] text-slate-400")
                with ui.row().classes("justify-between"):
                    ui.label("App").classes("text-sm text-slate-400")
                    ui.label(APP_VERSION).classes("text-sm")
                with ui.row().classes("justify-between"):
                    ui.label("PID").classes("text-sm text-slate-400")
                    ui.label(str(health["pid"])).classes("text-sm")
                with ui.row().classes("justify-between"):
                    ui.label("yt-dlp").classes("text-sm text-slate-400")
                    ui.label(str(health["yt_dlp_version"])).classes("text-sm")
                ui.label("System Ready").classes("text-green-400 text-xs mt-1")

            health_button = ui.button("Health Check", icon="health_and_safety").classes("w-full justify-start").props("outline dense")
            ui.button("Search Transcripts", icon="search").classes("w-full justify-start").props("outline dense")

        with ui.column().classes("ytis-main p-5 gap-3 flex-1"):
            with ui.row().classes("w-full justify-between items-center"):
                with ui.column().classes("gap-0"):
                    ui.label("Dashboard").classes("text-3xl font-bold")
                    ui.label("Build upload-ready YouTube research packs").classes("text-sm text-slate-300")
                top_new_project_button = ui.button("New Project", icon="add", color="primary").classes("px-6")

            metric_labels: dict[str, ui.label] = {}
            last_summary_labels: dict[str, ui.label] = {}
            last_paths: dict[str, Path] = {}

            with ui.row().classes("w-full gap-4 items-stretch"):
                with ui.card().classes("ytis-card p-3 gap-1").style("flex: 1.08; min-width: 420px; height: 465px; overflow: hidden;"):
                    ui.label("Build Research Pack").classes("text-xl font-bold")
                    name = ui.input("Project name", placeholder="Kieran Moloney - Full Channel Pack").classes("w-full")
                    url = ui.input("Channel/Video URL", placeholder="https://www.youtube.com/@KieranMoloney/videos").classes("w-full")
                    with ui.row().classes("w-full gap-3"):
                        lang = ui.select(["en", "es"], value="en", label="Language").classes("flex-1")
                        output = ui.input("Downloads output folder", value=str(default_downloads_dir())).classes("flex-[2]")
                        browse_button = ui.button("Browse", icon="folder_open").props("outline dense")
                    mode = ui.select(["reuse", "refresh", "repackage"], value="reuse", label="Build mode").classes("w-full")
                    ui.label("reuse = use existing subtitles | refresh = contact YouTube again | repackage = ZIP only").classes("text-xs text-slate-400")
                    with ui.row().classes("w-full items-center justify-between mt-1"):
                        status = ui.label("Ready to build").classes("text-sm text-slate-300")
                        progress_label = ui.label("0%").classes("text-sm text-slate-300 ml-auto")
                    progress = ui.linear_progress(value=0).classes("w-full")
                    log_area = ui.textarea("Hidden build log mirror").classes("w-full").props("readonly").style("display:none;")
                    with ui.row().classes("gap-2 mt-2 wrap"):
                        build_button = ui.button("Build Research Pack", icon="rocket_launch", color="primary").props("dense")
                        open_downloads_button = ui.button("Open Downloads", icon="folder_open").props("outline dense")
                        open_zip_button = ui.button("Open Last ZIP", icon="inventory_2").props("outline dense")
                        open_project_button = ui.button("Project Folder", icon="folder").props("outline dense")
                    open_zip_button.disable()
                    open_project_button.disable()

                with ui.card().classes("ytis-card p-3 gap-1").style("flex: 1.05; min-width: 360px; height: 465px; overflow: hidden;"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Process Log").classes("text-xl font-bold")
                        process_status = ui.label("Waiting").classes("text-sm text-green-500")
                    process_log = ui.log(max_lines=300).classes("w-full ytis-process-log").style("height: 388px;")

                with ui.card().classes("ytis-card p-3 gap-1").style("flex: 1.2; min-width: 420px; height: 465px; overflow: hidden;"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Source Preview").classes("text-xl font-bold")
                        source_type = ui.label("Channel").classes("text-xs text-red-400")
                    source_image = ui.image(SOURCE_PLACEHOLDER).classes("w-full rounded-xl").style("height: 220px; object-fit: cover;")
                    source_title = ui.label("No source selected").classes("text-base font-bold")
                    source_subtitle = ui.label("Enter a YouTube channel or video URL").classes("text-sm text-slate-400")
                    source_status = ui.label("Preview area ready.").classes("text-xs text-slate-400")
                    source_url = ui.label("-").classes("text-xs text-blue-300 break-all")

            with ui.row().classes("w-full gap-3"):
                for title, key, default in [
                    ("Videos Found", "videos", "0"),
                    ("Subtitles", "subtitles", "0"),
                    ("TXT Files", "txt", "0"),
                    ("Total Words", "words", "0"),
                    ("ZIP Package", "zip", "-"),
                ]:
                    with ui.card().classes("ytis-metric p-3").style("flex: 1; min-width: 170px; height: 94px;"):
                        ui.label(title).classes("text-sm text-slate-400")
                        metric_labels[key] = ui.label(default).classes("text-2xl font-bold")

            with ui.row().classes("w-full gap-4 items-stretch"):
                with ui.card().classes("ytis-card p-3 gap-1").style("flex: 1.08; min-width: 500px; height: 245px; overflow: hidden;"):
                    ui.label("Last Build Summary").classes("text-lg font-bold")
                    with ui.grid(columns=2).classes("w-full gap-2"):
                        for key, title in [
                            ("mode", "Build Mode"),
                            ("missing", "Missing Subtitles"),
                            ("videos", "Videos Found"),
                            ("duplicate", "Duplicate Check"),
                            ("transcripts", "Transcripts"),
                            ("zip", "ZIP Path"),
                            ("words", "Total Words"),
                            ("project", "Project Folder"),
                        ]:
                            with ui.column().classes("gap-0"):
                                ui.label(title).classes("text-[11px] text-slate-400")
                                last_summary_labels[key] = ui.label("-").classes("text-xs text-slate-200 break-all")

                with ui.card().classes("ytis-card p-3 gap-1").style("flex: 1; min-width: 520px; height: 245px; overflow: hidden;"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Recent Projects").classes("text-lg font-bold")
                        ui.button("View all", icon="expand_more").props("outline dense")
                    if not project_summaries:
                        ui.label("No saved projects yet.").classes("text-slate-400")
                    else:
                        for project in project_summaries[:4]:
                            with ui.row().classes("w-full items-center justify-between gap-2"):
                                with ui.column().classes("gap-0"):
                                    ui.label(str(project.get("name", "Unnamed"))).classes("font-bold text-sm")
                                    ui.label(str(project.get("built_at", project.get("last_updated_at", "")))).classes("text-xs text-slate-400")
                                with ui.row().classes("gap-1"):
                                    ui.button("Load", on_click=lambda p=project: load_project(p)).props("outline dense")
                                    if project.get("project_dir"):
                                        ui.button("Open Folder", on_click=lambda p=project: open_path(str(p.get("project_dir")))).props("outline dense")
                                    if project.get("zip_path"):
                                        ui.button("Open ZIP", on_click=lambda p=project: open_path(str(p.get("zip_path")))).props("outline dense")

            def update_source_preview() -> None:
                meta = source_meta(url.value or "", name.value or "")
                source_type.text = meta["type"]
                source_title.text = meta["title"]
                source_subtitle.text = meta["subtitle"]
                source_status.text = meta["status"]
                source_url.text = meta["url"]
                source_image.set_source(meta["image"])
                for element in [source_type, source_title, source_subtitle, source_status, source_url, source_image]:
                    element.update()

            def set_metric_values(project: dict[str, Any]) -> None:
                total_words_value = project.get("total_words", "")
                words_display = f"{int(total_words_value):,}" if str(total_words_value).isdigit() else "0"
                metric_labels["videos"].text = value(project, "videos_found", "0")
                metric_labels["subtitles"].text = value(project, "transcripts_created", "0")
                metric_labels["txt"].text = value(project, "transcripts_created", "0")
                metric_labels["words"].text = words_display
                metric_labels["zip"].text = "1" if project.get("zip_path") else "-"
                for label in metric_labels.values():
                    label.update()

            def set_sidebar_project(project: dict[str, Any]) -> None:
                total_words_value = project.get("total_words", "")
                words_display = f"{int(total_words_value):,}" if str(total_words_value).isdigit() else "0"
                current_project_title.text = value(project, "name", "No project loaded")
                current_project_subtitle.text = "Full Channel Pack" if project.get("name") else "Current project"
                current_mode.text = value(project, "build_mode", "reuse") + " mode"
                current_videos.text = value(project, "videos_found", "0")
                current_transcripts.text = value(project, "transcripts_created", "0")
                current_words.text = words_display
                current_zip.text = "Ready" if project.get("zip_path") else "Not ready"
                for element in [current_project_title, current_project_subtitle, current_mode, current_videos, current_transcripts, current_words, current_zip]:
                    element.update()

            def set_summary(project: dict[str, Any]) -> None:
                total_words_value = project.get("total_words", "")
                words_display = f"{int(total_words_value):,}" if str(total_words_value).isdigit() else "-"
                last_summary_labels["mode"].text = value(project, "build_mode")
                last_summary_labels["videos"].text = value(project, "videos_found")
                last_summary_labels["transcripts"].text = value(project, "transcripts_created")
                last_summary_labels["words"].text = words_display
                last_summary_labels["missing"].text = value(project, "missing_subtitles")
                last_summary_labels["duplicate"].text = "Passed" if project.get("transcripts_created") == project.get("unique_transcript_ids") else "Review"
                last_summary_labels["zip"].text = short_path(value(project, "zip_path"))
                last_summary_labels["project"].text = short_path(value(project, "project_dir"))
                for label in last_summary_labels.values():
                    label.update()

            def fill_from_project(project: dict[str, Any]) -> None:
                name.value = value(project, "name", "")
                url.value = value(project, "url", "")
                lang.value = value(project, "language", "en")
                output.value = str(default_downloads_dir())
                mode.value = "reuse"
                for element in [name, url, lang, output, mode]:
                    element.update()
                update_source_preview()
                set_metric_values(project)
                set_sidebar_project(project)
                set_summary(project)
                if project.get("zip_path"):
                    last_paths["zip"] = Path(str(project.get("zip_path")))
                    open_zip_button.enable()
                    quick_open_zip_button.enable()
                if project.get("project_dir"):
                    last_paths["project"] = Path(str(project.get("project_dir")))
                    open_project_button.enable()
                    quick_open_project_button.enable()
                progress.value = 1.0
                progress_label.text = "100%"
                status.text = "Latest project loaded"
                process_status.text = "Loaded latest project"
                progress.update()
                progress_label.update()
                status.update()
                process_status.update()
                process_log.push(f"Loaded latest project: {project.get('name', 'Unnamed')}")
                process_log.push(f"Mode: {project.get('build_mode', '-')}")
                process_log.push(f"Videos: {project.get('videos_found', '-')} | Transcripts: {project.get('transcripts_created', '-')} | Words: {project.get('total_words', '-')}")
                process_log.push(f"ZIP: {project.get('zip_path', '-')}")

            async def refresh_log() -> None:
                log_area.value = "\\n".join(CURRENT_LOG[-250:])
                log_area.update()

            def reset_form() -> None:
                name.value = ""
                url.value = ""
                lang.value = "en"
                output.value = str(default_downloads_dir())
                mode.value = "reuse"
                progress.value = 0
                progress_label.text = "0%"
                status.text = "Ready to build"
                process_status.text = "Waiting"
                CURRENT_LOG.clear()
                try:
                    process_log.clear()
                except Exception:
                    pass
                update_source_preview()
                for element in [name, url, lang, output, mode, progress, progress_label, status, process_status]:
                    element.update()
                ui.notify("New project form ready", type="info")

            def load_project(project: dict[str, Any]) -> None:
                fill_from_project(project)
                ui.notify(f"Loaded project: {project.get('name', 'Unnamed')}", type="positive")

            def update_after_build(result) -> None:
                project = {
                    "name": name.value,
                    "url": url.value,
                    "language": lang.value,
                    "build_mode": result.mode,
                    "videos_found": result.videos_found,
                    "transcripts_created": result.transcripts_created,
                    "unique_transcript_ids": result.transcripts_created,
                    "missing_subtitles": result.missing_subtitles,
                    "total_words": result.total_words,
                    "zip_path": str(result.zip_path),
                    "project_dir": str(result.project_dir),
                }
                set_metric_values(project)
                set_sidebar_project(project)
                set_summary(project)
                last_paths["zip"] = result.zip_path
                last_paths["project"] = result.project_dir
                open_zip_button.enable()
                open_project_button.enable()
                quick_open_zip_button.enable()
                quick_open_project_button.enable()

            async def run_build() -> None:
                CURRENT_LOG.clear()
                try:
                    process_log.clear()
                except Exception:
                    pass

                if not name.value or not url.value:
                    ui.notify("Project name and channel URL are required", type="warning")
                    return

                build_button.disable()
                progress.value = 0.05
                progress_label.text = "5%"
                status.text = f"Starting build in {mode.value} mode..."
                process_status.text = "Running"
                for element in [progress, progress_label, status, process_status]:
                    element.update()

                def callback(message: str, percent: Optional[float] = None) -> None:
                    CURRENT_LOG.append(message)
                    process_log.push(message)
                    if percent is not None:
                        progress.value = max(0.0, min(1.0, percent))
                        progress_label.text = f"{int(progress.value * 100)}%"

                try:
                    options = BuildOptions(
                        name=name.value.strip(),
                        url=url.value.strip(),
                        lang=lang.value or "en",
                        output_downloads=Path(output.value).expanduser(),
                        base_projects_dir=project_root() / "projects",
                        mode=mode.value or "reuse",
                    )
                    result = await asyncio.to_thread(build_research_pack, options, callback)
                    progress.value = 1.0
                    progress_label.text = "100%"
                    status.text = "Build completed successfully"
                    process_status.text = "Build completed successfully"
                    ui.notify("Research pack is ready", type="positive")
                    process_log.push(f"ZIP READY: {result.zip_path}")
                    update_after_build(result)
                except Exception as exc:
                    status.text = "Build failed"
                    process_status.text = "Build failed"
                    process_log.push(f"ERROR: {exc}")
                    ui.notify(f"Build failed: {exc}", type="negative")
                finally:
                    build_button.enable()
                    for element in [progress, progress_label, status, process_status]:
                        element.update()
                    await refresh_log()

            def open_last_zip() -> None:
                path = last_paths.get("zip")
                if path:
                    open_path(path)

            def open_last_project() -> None:
                path = last_paths.get("project")
                if path:
                    open_path(path)

            def load_last_project() -> None:
                if project_summaries:
                    fill_from_project(project_summaries[0])
                else:
                    ui.notify("No saved projects yet", type="warning")

            async def scroll_to_top() -> None:
                ui.run_javascript("window.scrollTo({top: 0, behavior: 'smooth'});")

            async def scroll_to_bottom() -> None:
                ui.run_javascript("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});")

            def new_project_action() -> None:
                reset_form()
                ui.run_javascript("window.scrollTo({top: 0, behavior: 'smooth'});")

            build_button.on("click", run_build)
            top_new_project_button.on("click", new_project_action)
            quick_new_project_button.on("click", new_project_action)
            dashboard_button.on("click", scroll_to_top)
            projects_button.on("click", scroll_to_bottom)
            health_button.on("click", scroll_to_bottom)

            browse_button.on("click", lambda: open_path(default_downloads_dir()))
            open_downloads_button.on("click", lambda: open_path(default_downloads_dir()))
            quick_open_downloads_button.on("click", lambda: open_path(default_downloads_dir()))
            open_zip_button.on("click", open_last_zip)
            quick_open_zip_button.on("click", open_last_zip)
            open_project_button.on("click", open_last_project)
            quick_open_project_button.on("click", open_last_project)
            quick_load_last_button.on("click", load_last_project)

            url.on("update:model-value", lambda e: update_source_preview())
            name.on("update:model-value", lambda e: update_source_preview())
            ui.timer(1.0, refresh_log)

            if latest_project:
                fill_from_project(latest_project)
            else:
                quick_open_zip_button.disable()
                quick_open_project_button.disable()
                update_source_preview()


def main() -> None:
    ui.run(
        title="YTIS - Dashboard",
        host="127.0.0.1",
        port=8080,
        reload=False,
        dark=True,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
