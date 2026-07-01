from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Optional

from nicegui import ui

from ytis.core.builder import BuildOptions, build_research_pack
from ytis.core.health import get_health_snapshot
from ytis.core.paths import default_downloads_dir, project_root
from ytis.core.registry import read_project_summaries

APP_VERSION = "v0.2.3"
CURRENT_LOG: list[str] = []
YOUTUBE_VIDEO_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})")
CHANNEL_HANDLE_RE = re.compile(r"youtube\.com/@([^/?#]+)")
SOURCE_PLACEHOLDER = "data:image/svg+xml;utf8,%0A%3Csvg%20xmlns%3D%27http%3A//www.w3.org/2000/svg%27%20width%3D%27900%27%20height%3D%27500%27%20viewBox%3D%270%200%20900%20500%27%3E%0A%20%20%3Cdefs%3E%0A%20%20%20%20%3ClinearGradient%20id%3D%27bg%27%20x1%3D%270%27%20y1%3D%270%27%20x2%3D%271%27%20y2%3D%271%27%3E%0A%20%20%20%20%20%20%3Cstop%20offset%3D%270%25%27%20stop-color%3D%27%2307111f%27/%3E%0A%20%20%20%20%20%20%3Cstop%20offset%3D%27100%25%27%20stop-color%3D%27%230f1b2d%27/%3E%0A%20%20%20%20%3C/linearGradient%3E%0A%20%20%20%20%3ClinearGradient%20id%3D%27bar%27%20x1%3D%270%27%20y1%3D%270%27%20x2%3D%271%27%20y2%3D%270%27%3E%0A%20%20%20%20%20%20%3Cstop%20offset%3D%270%25%27%20stop-color%3D%27%230f172a%27/%3E%0A%20%20%20%20%20%20%3Cstop%20offset%3D%27100%25%27%20stop-color%3D%27%237f1d1d%27/%3E%0A%20%20%20%20%3C/linearGradient%3E%0A%20%20%3C/defs%3E%0A%20%20%3Crect%20width%3D%27900%27%20height%3D%27500%27%20rx%3D%2724%27%20fill%3D%27url%28%23bg%29%27/%3E%0A%20%20%3Crect%20x%3D%2734%27%20y%3D%2734%27%20width%3D%27832%27%20height%3D%27116%27%20rx%3D%2718%27%20fill%3D%27url%28%23bar%29%27/%3E%0A%20%20%3Ccircle%20cx%3D%27110%27%20cy%3D%27250%27%20r%3D%2762%27%20fill%3D%27%23ef4444%27/%3E%0A%20%20%3Cpolygon%20points%3D%2792%2C216%2092%2C284%20148%2C250%27%20fill%3D%27white%27/%3E%0A%20%20%3Ctext%20x%3D%2772%27%20y%3D%2792%27%20fill%3D%27white%27%20font-size%3D%2734%27%20font-family%3D%27Arial%27%20font-weight%3D%27700%27%3ESource%20Preview%3C/text%3E%0A%20%20%3Ctext%20x%3D%2772%27%20y%3D%27125%27%20fill%3D%27%23cbd5e1%27%20font-size%3D%2718%27%20font-family%3D%27Arial%27%3EChannel%20screenshot%20or%20video%20thumbnail%3C/text%3E%0A%20%20%3Ctext%20x%3D%27205%27%20y%3D%27238%27%20fill%3D%27white%27%20font-size%3D%2728%27%20font-family%3D%27Arial%27%20font-weight%3D%27700%27%3EReady%20for%20source%20capture%3C/text%3E%0A%20%20%3Ctext%20x%3D%27205%27%20y%3D%27272%27%20fill%3D%27%2394a3b8%27%20font-size%3D%2718%27%20font-family%3D%27Arial%27%3EOne%20visual%20reference%20only%3C/text%3E%0A%20%20%3Crect%20x%3D%2770%27%20y%3D%27360%27%20width%3D%27160%27%20height%3D%2754%27%20rx%3D%2712%27%20fill%3D%27%230f172a%27%20stroke%3D%27%23334155%27/%3E%0A%20%20%3Crect%20x%3D%27250%27%20y%3D%27360%27%20width%3D%27160%27%20height%3D%2754%27%20rx%3D%2712%27%20fill%3D%27%230f172a%27%20stroke%3D%27%23334155%27/%3E%0A%20%20%3Crect%20x%3D%27430%27%20y%3D%27360%27%20width%3D%27160%27%20height%3D%2754%27%20rx%3D%2712%27%20fill%3D%27%230f172a%27%20stroke%3D%27%23334155%27/%3E%0A%20%20%3Crect%20x%3D%27610%27%20y%3D%27360%27%20width%3D%27160%27%20height%3D%2754%27%20rx%3D%2712%27%20fill%3D%27%230f172a%27%20stroke%3D%27%23334155%27/%3E%0A%3C/svg%3E%0A"


def add_log(message: str) -> None:
    CURRENT_LOG.append(message)


def open_path(path: str | Path) -> None:
    path_obj = Path(path)
    if path_obj.exists():
        os.startfile(str(path_obj))


def extract_video_id(url: str) -> str | None:
    match = YOUTUBE_VIDEO_RE.search(url or "")
    return match.group(1) if match else None


def get_source_meta(url: str, project_name: str) -> dict[str, str]:
    url = (url or "").strip()
    project_name = (project_name or "").strip()
    video_id = extract_video_id(url)

    if video_id:
        title = project_name or "Selected YouTube Video"
        return {
            "type": "Video",
            "title": title,
            "subtitle": f"Video ID: {video_id}",
            "image": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            "status": "Video thumbnail loaded. Later we can capture a full video page screenshot.",
            "url": url or "-",
        }

    handle_match = CHANNEL_HANDLE_RE.search(url)
    handle = handle_match.group(1) if handle_match else "youtube-channel"
    title = project_name or handle.replace("-", " ").title() or "YouTube Channel"
    return {
        "type": "Channel",
        "title": title,
        "subtitle": f"@{handle}",
        "image": SOURCE_PLACEHOLDER,
        "status": "Channel placeholder. Real screenshot capture is the next technical step.",
        "url": url or "-",
    }


@ui.page("/")
def dashboard() -> None:
    ui.add_head_html("""
    <style>
    body { background: radial-gradient(circle at top, #091426 0%, #07111f 55%, #050b16 100%); }
    .ytis-shell { gap: 0; }
    .ytis-sidebar {
        width: 245px;
        min-height: 100vh;
        background: linear-gradient(180deg, rgba(8,19,33,0.98), rgba(6,14,25,0.98));
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    .ytis-main { min-height: 100vh; max-width: 1660px; }
    .ytis-card {
        background: linear-gradient(145deg, rgba(15,27,45,0.98), rgba(18,31,51,0.95));
        border: 1px solid rgba(88, 136, 255, 0.15);
        border-radius: 18px;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.24);
    }
    .ytis-metric {
        background: linear-gradient(180deg, rgba(16,27,45,0.96), rgba(12,20,35,0.92));
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
    }
    .q-field__control { min-height: 38px !important; }
    .q-field__native { font-size: 13px !important; }
    .ytis-compact-label { font-size: 12px; color: #94a3b8; }
    .ytis-process-log {
        font-family: Consolas, monospace;
        font-size: 12px;
        line-height: 1.45;
    }

    .q-field__label { font-size: 12px !important; }
    .q-field__bottom { min-height: 0 !important; }
    .q-btn { font-size: 12px !important; }
    </style>
    """)

    projects_dir = project_root() / "projects"
    project_summaries = read_project_summaries(projects_dir)
    health = get_health_snapshot()

    with ui.row().classes("w-full text-white ytis-shell"):
        with ui.column().classes("ytis-sidebar p-5 gap-4"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("smart_display").classes("text-5xl text-red-500")
                with ui.column().classes("gap-0"):
                    ui.label("YTIS").classes("text-4xl font-bold text-blue-400")
                    ui.label("YouTube Intelligence System").classes("text-sm text-slate-300")
                    ui.label(f"{APP_VERSION}  |  PID: {os.getpid()}").classes("text-xs text-slate-500")
            ui.separator().classes("bg-slate-700")
            dashboard_button = ui.button("Dashboard", icon="home").classes("w-full justify-start")
            projects_button = ui.button("Projects", icon="folder").classes("w-full justify-start").props("outline")
            new_project_button = ui.button("New Project", icon="add").classes("w-full justify-start").props("outline")
            health_button = ui.button("Health Check", icon="health_and_safety").classes("w-full justify-start").props("outline")
            ui.button("Search Transcripts", icon="search").classes("w-full justify-start").props("outline")
            ui.space()
            with ui.card().classes("ytis-card p-4 w-full mt-auto"):
                ui.label("Operator Mode").classes("text-sm")
                ui.label("Local").classes("text-slate-400")
                ui.label("System Ready").classes("text-green-400 text-xs mt-2")

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
                with ui.card().classes("ytis-card p-3 gap-1").style("flex: 1.18; min-width: 430px; height: 455px; overflow: hidden;"):
                    ui.label("Build Research Pack").classes("text-xl font-bold")

                    name = ui.input("Project name", placeholder="Kieran Moloney - Full Channel Pack").classes("w-full")
                    url = ui.input("Channel/Video URL", placeholder="https://www.youtube.com/@KieranMoloney/videos").classes("w-full")

                    with ui.row().classes("w-full gap-3"):
                        lang = ui.select(["en", "es"], value="en", label="Language").classes("flex-1")
                        output = ui.input("Downloads output folder", value=str(default_downloads_dir())).classes("flex-[2]")
                        browse_button = ui.button("Browse", icon="folder_open").props("outline dense")

                    mode = ui.select(["reuse", "refresh", "repackage"], value="reuse", label="Build mode").classes("w-full")
                    ui.label("reuse = use existing subtitles if available | refresh = contact YouTube again | repackage = ZIP only from existing files").classes("text-xs text-slate-400")

                    with ui.row().classes("w-full items-center justify-between mt-1"):
                        status = ui.label("Ready to build").classes("text-sm text-slate-300")
                        progress_label = ui.label("0%").classes("text-sm text-slate-300 ml-auto")
                    progress = ui.linear_progress(value=0).classes("w-full")

                    log_area = ui.textarea("Hidden build log mirror").classes("w-full").props("readonly").style("display:none;")

                    with ui.row().classes("gap-2 mt-2 wrap"):
                        build_button = ui.button("Build Research Pack", icon="rocket_launch", color="primary").props("dense")
                        open_downloads_button = ui.button("Open Downloads", icon="folder_open").props("outline dense")
                        open_zip_button = ui.button("Open Last ZIP", icon="inventory_2").props("outline dense")
                        open_project_button = ui.button("Open Last Project Folder", icon="folder").props("outline dense")

                    open_zip_button.disable()
                    open_project_button.disable()

                with ui.card().classes("ytis-card p-3 gap-1").style("flex: 1.06; min-width: 360px; height: 455px; overflow: hidden;"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Process Log").classes("text-xl font-bold")
                        process_status = ui.label("Waiting").classes("text-sm text-green-500")
                    process_log = ui.log(max_lines=300).classes("w-full ytis-process-log").style("height: 370px;")

                with ui.card().classes("ytis-card p-3 gap-1").style("flex: 0.96; min-width: 330px; height: 455px; overflow: hidden;"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Source Preview").classes("text-xl font-bold")
                        source_type = ui.label("Channel").classes("text-xs text-red-400")
                    source_image = ui.image(SOURCE_PLACEHOLDER).classes("w-full rounded-xl").style("height: 175px; object-fit: cover;")
                    source_title = ui.label("No source selected").classes("text-base font-bold")
                    source_subtitle = ui.label("Enter a YouTube channel or video URL").classes("text-sm text-slate-400")
                    source_status = ui.label("Preview area ready.").classes("text-xs text-slate-400")
                    source_url = ui.label("-").classes("text-xs text-blue-300 break-all")

            with ui.row().classes("w-full gap-3"):
                metric_defs = [
                    ("Videos Found", "videos", "0"),
                    ("Subtitles", "subtitles", "0"),
                    ("TXT Files", "txt", "0"),
                    ("Total Words", "words", "0"),
                    ("ZIP", "zip", "-"),
                ]
                for title, key, default in metric_defs:
                    with ui.card().classes("ytis-metric p-3").style("flex: 1; min-width: 170px; height: 94px;"):
                        ui.label(title).classes("text-sm text-slate-400")
                        metric_labels[key] = ui.label(default).classes("text-2xl font-bold")

            with ui.row().classes("w-full gap-4 items-stretch"):
                with ui.card().classes("ytis-card p-3 gap-1").style("flex: 1.15; min-width: 360px; height: 250px; overflow: hidden;"):
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
                                ui.label(title).classes("text-xs text-slate-400")
                                last_summary_labels[key] = ui.label("-").classes("text-xs text-slate-200 break-all")

                with ui.card().classes("ytis-card p-3 gap-1").style("flex: 0.85; min-width: 300px; height: 250px; overflow: hidden;"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Health Check").classes("text-lg font-bold")
                        ui.label("All Systems OK").classes("text-xs text-green-500")
                    for label, value in [
                        ("App Version", APP_VERSION),
                        ("Process ID", str(health["pid"])),
                        ("Python Version", health["python_version"]),
                        ("yt-dlp Version", health["yt_dlp_version"]),
                        ("Project Root", health["project_root"]),
                        ("Downloads Dir", health["downloads_dir"]),
                    ]:
                        with ui.row().classes("w-full justify-between items-start gap-3"):
                            ui.label(label).classes("text-xs text-slate-400")
                            ui.label(str(value)).classes("text-xs text-right break-all")

                with ui.card().classes("ytis-card p-3 gap-1").style("flex: 1.2; min-width: 360px; height: 250px; overflow: hidden;"):
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
                                        ui.button("Folder", on_click=lambda p=project: open_path(str(p.get("project_dir")))).props("outline dense")
                                    if project.get("zip_path"):
                                        ui.button("ZIP", on_click=lambda p=project: open_path(str(p.get("zip_path")))).props("outline dense")

            def update_source_preview() -> None:
                meta = get_source_meta(url.value or "", name.value or "")
                source_type.text = meta["type"]
                source_title.text = meta["title"]
                source_subtitle.text = meta["subtitle"]
                source_status.text = meta["status"]
                source_url.text = meta["url"]
                source_image.set_source(meta["image"])
                for element in [source_type, source_title, source_subtitle, source_status, source_url, source_image]:
                    element.update()

            async def refresh_log() -> None:
                log_area.value = "\n".join(CURRENT_LOG[-250:])
                log_area.update()

            def fill_dashboard_from_project(project: dict) -> None:
                """Populate the dashboard from the latest registry entry on startup."""
                name.value = str(project.get("name", ""))
                url.value = str(project.get("url", ""))
                lang.value = str(project.get("language", "en"))
                output.value = str(default_downloads_dir())
                mode.value = "reuse"
                update_source_preview()

                videos_value = str(project.get("videos_found", "-"))
                transcripts_value = str(project.get("transcripts_created", "-"))
                total_words_value = project.get("total_words", "")
                words_display = f"{int(total_words_value):,}" if str(total_words_value).isdigit() else "-"

                metric_labels["videos"].text = videos_value
                metric_labels["subtitles"].text = transcripts_value
                metric_labels["txt"].text = transcripts_value
                metric_labels["words"].text = words_display
                metric_labels["zip"].text = "1" if project.get("zip_path") else "-"

                last_summary_labels["mode"].text = str(project.get("build_mode", "-"))
                last_summary_labels["videos"].text = videos_value
                last_summary_labels["transcripts"].text = transcripts_value
                last_summary_labels["words"].text = words_display
                last_summary_labels["missing"].text = str(project.get("missing_subtitles", "-"))
                last_summary_labels["duplicate"].text = "Passed" if project.get("transcripts_created") == project.get("unique_transcript_ids") else "Review"
                last_summary_labels["zip"].text = str(project.get("zip_path", "-"))
                last_summary_labels["project"].text = str(project.get("project_dir", "-"))

                for element in [name, url, lang, output, mode]:
                    element.update()
                for label in metric_labels.values():
                    label.update()
                for label in last_summary_labels.values():
                    label.update()

                if project.get("zip_path"):
                    last_paths["zip"] = Path(str(project.get("zip_path")))
                    open_zip_button.enable()
                if project.get("project_dir"):
                    last_paths["project"] = Path(str(project.get("project_dir")))
                    open_project_button.enable()

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
                process_log.push(f"Videos: {videos_value} | Transcripts: {transcripts_value} | Words: {words_display}")
                process_log.push(f"ZIP: {project.get('zip_path', '-')}")

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

            def load_project(project: dict) -> None:
                name.value = str(project.get("name", ""))
                url.value = str(project.get("url", ""))
                lang.value = str(project.get("language", "en"))
                output.value = str(default_downloads_dir())
                mode.value = "reuse"
                update_source_preview()
                for element in [name, url, lang, output, mode]:
                    element.update()
                ui.notify(f"Loaded project: {name.value}", type="positive")

            def update_last_summary(result) -> None:
                last_summary_labels["mode"].text = str(result.mode)
                last_summary_labels["videos"].text = str(result.videos_found)
                last_summary_labels["transcripts"].text = str(result.transcripts_created)
                last_summary_labels["words"].text = f"{result.total_words:,}"
                last_summary_labels["missing"].text = str(result.missing_subtitles)
                last_summary_labels["duplicate"].text = "Passed"
                last_summary_labels["zip"].text = str(result.zip_path)
                last_summary_labels["project"].text = str(result.project_dir)
                for label in last_summary_labels.values():
                    label.update()
                last_paths["zip"] = result.zip_path
                last_paths["project"] = result.project_dir
                open_zip_button.enable()
                open_project_button.enable()

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
                progress.update()
                progress_label.update()
                status.update()
                process_status.update()

                def callback(message: str, percent: Optional[float] = None) -> None:
                    add_log(message)
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
                    add_log(f"ZIP READY: {result.zip_path}")
                    process_log.push(f"ZIP READY: {result.zip_path}")
                    metric_labels["videos"].text = str(result.videos_found)
                    metric_labels["subtitles"].text = str(result.transcripts_created)
                    metric_labels["txt"].text = str(result.transcripts_created)
                    metric_labels["words"].text = f"{result.total_words:,}"
                    metric_labels["zip"].text = "1"
                    for label in metric_labels.values():
                        label.update()
                    update_last_summary(result)
                except Exception as exc:
                    status.text = "Build failed"
                    process_status.text = "Build failed"
                    add_log(f"ERROR: {exc}")
                    process_log.push(f"ERROR: {exc}")
                    ui.notify(f"Build failed: {exc}", type="negative")
                finally:
                    build_button.enable()
                    progress.update()
                    progress_label.update()
                    status.update()
                    process_status.update()
                    await refresh_log()

            def open_downloads() -> None:
                open_path(default_downloads_dir())

            def open_last_zip() -> None:
                path = last_paths.get("zip")
                if path:
                    open_path(path)

            def open_last_project() -> None:
                path = last_paths.get("project")
                if path:
                    open_path(path)

            async def scroll_to_top() -> None:
                ui.run_javascript("window.scrollTo({top: 0, behavior: 'smooth'});")

            async def scroll_to_projects() -> None:
                ui.run_javascript("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});")

            async def scroll_to_health() -> None:
                ui.run_javascript("window.scrollTo({top: document.body.scrollHeight * 0.72, behavior: 'smooth'});")

            def new_project_action() -> None:
                reset_form()
                ui.run_javascript("window.scrollTo({top: 0, behavior: 'smooth'});")

            build_button.on("click", run_build)
            open_downloads_button.on("click", open_downloads)
            open_zip_button.on("click", open_last_zip)
            open_project_button.on("click", open_last_project)
            browse_button.on("click", open_downloads)
            dashboard_button.on("click", scroll_to_top)
            projects_button.on("click", scroll_to_projects)
            health_button.on("click", scroll_to_health)
            new_project_button.on("click", new_project_action)
            top_new_project_button.on("click", new_project_action)
            url.on("update:model-value", lambda e: update_source_preview())
            name.on("update:model-value", lambda e: update_source_preview())
            ui.timer(1.0, refresh_log)

            # Auto-load the most recent project on startup so the dashboard is not empty.
            if project_summaries:
                fill_dashboard_from_project(project_summaries[0])
            else:
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
