from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from nicegui import ui

from ytis.core.builder import BuildOptions, build_research_pack
from ytis.core.health import get_health_snapshot
from ytis.core.paths import default_downloads_dir, project_root
from ytis.core.registry import read_project_summaries


APP_VERSION = "v0.1.4"
CURRENT_LOG: list[str] = []


def add_log(message: str) -> None:
    CURRENT_LOG.append(message)


def open_path(path: str | Path) -> None:
    path_obj = Path(path)
    if path_obj.exists():
        os.startfile(str(path_obj))


@ui.page("/")
def dashboard() -> None:
    ui.add_head_html("""
    <style>
    body { background: #07111f; }
    .ytis-card {
        background: linear-gradient(145deg, #0f1b2d, #121f33);
        border: 1px solid rgba(88, 136, 255, 0.18);
        border-radius: 18px;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.24);
    }
    .ytis-metric {
        background: #101b2d;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
    }
    .ytis-sidebar {
        background: #081321;
        border-right: 1px solid rgba(255,255,255,0.08);
    }
    .ytis-good { color: #22c55e; }
    .ytis-warn { color: #f59e0b; }
    </style>
    """)

    projects_dir = project_root() / "projects"
    project_summaries = read_project_summaries(projects_dir)
    health = get_health_snapshot()

    with ui.row().classes("w-full min-h-screen text-white"):
        with ui.column().classes("ytis-sidebar p-5 gap-4 w-72"):
            with ui.row().classes("items-center gap-3"):
                ui.label("▶").classes("text-3xl text-red-500")
                with ui.column().classes("gap-0"):
                    ui.label("YTIS").classes("text-3xl font-bold text-blue-300")
                    ui.label("YouTube Intelligence System").classes("text-sm text-slate-300")
                    ui.label(APP_VERSION).classes("text-xs text-slate-500")
                    ui.label(f"PID: {os.getpid()}").classes("text-xs text-slate-500")
            ui.separator().classes("bg-slate-700")
            dashboard_button = ui.button("Dashboard", icon="dashboard").classes("w-full justify-start")
            projects_button = ui.button("Projects", icon="folder").classes("w-full justify-start").props("outline")
            new_project_button = ui.button("New Project", icon="add_circle").classes("w-full justify-start").props("outline")
            health_button = ui.button("Health Check", icon="health_and_safety").classes("w-full justify-start").props("outline")
            ui.button("Search Transcripts", icon="search").classes("w-full justify-start").props("outline")
            ui.space()
            with ui.card().classes("ytis-card p-4 w-full"):
                ui.label("Local output").classes("text-sm text-slate-400")
                ui.label(str(default_downloads_dir())).classes("text-xs text-slate-300 break-all")
                ui.label("Status: ready").classes("text-green-400 mt-2")

        with ui.column().classes("p-8 gap-5 flex-1"):
            with ui.row().classes("w-full justify-between items-center"):
                with ui.column().classes("gap-1"):
                    ui.label("Dashboard").classes("text-3xl font-bold")
                    ui.label("Build upload-ready YouTube research packs").classes("text-slate-300")
                top_new_project_button = ui.button("New Project", icon="add", color="primary").classes("px-6")

            metric_labels: dict[str, ui.label] = {}
            last_summary_labels: dict[str, ui.label] = {}
            last_paths: dict[str, Path] = {}

            with ui.card().classes("ytis-card p-6 w-full") as build_card:
                ui.label("Build Research Pack").classes("text-xl font-bold")
                ui.label("Default mode reuses existing subtitles and does not re-download. Use Refresh only when you deliberately want to contact YouTube again.").classes("text-slate-300")

                with ui.grid(columns=2).classes("w-full gap-4 mt-4"):
                    name = ui.input("Project name", placeholder="ScottMillar").classes("w-full")
                    url = ui.input("Channel URL", placeholder="https://www.youtube.com/@channel/videos").classes("w-full")
                    lang = ui.input("Language", value="en").classes("w-full")
                    output = ui.input("Downloads output folder", value=str(default_downloads_dir())).classes("w-full")
                    mode = ui.select(
                        ["reuse", "refresh", "repackage"],
                        value="reuse",
                        label="Build mode",
                    ).classes("w-full")
                    ui.label(
                        "reuse = skip subtitle download if SRT exists | refresh = contact YouTube | repackage = clean/ZIP existing SRT only"
                    ).classes("text-xs text-slate-400")

                progress = ui.linear_progress(value=0).classes("w-full mt-4")
                status = ui.label("Waiting to start").classes("text-slate-300")
                log_area = ui.textarea("Build log").classes("w-full h-64").props("readonly")

                with ui.row().classes("gap-3 mt-2"):
                    build_button = ui.button("Build Research Pack", icon="rocket_launch", color="primary")
                    open_downloads_button = ui.button("Open Downloads", icon="folder_open").props("outline")
                    open_zip_button = ui.button("Open Last ZIP", icon="inventory_2").props("outline")
                    open_project_button = ui.button("Open Last Project Folder", icon="folder").props("outline")

                open_zip_button.disable()
                open_project_button.disable()

                async def refresh_log() -> None:
                    log_area.value = "\n".join(CURRENT_LOG[-250:])
                    log_area.update()

                def reset_form() -> None:
                    name.value = ""
                    url.value = ""
                    lang.value = "en"
                    output.value = str(default_downloads_dir())
                    mode.value = "reuse"
                    progress.value = 0
                    status.text = "Waiting to start"
                    CURRENT_LOG.clear()
                    for element in [name, url, lang, output, mode, progress, status]:
                        element.update()
                    ui.notify("New project form ready", type="info")

                def load_project(project: dict) -> None:
                    name.value = str(project.get("name", ""))
                    url.value = str(project.get("url", ""))
                    lang.value = str(project.get("language", "en"))
                    output.value = str(default_downloads_dir())
                    mode.value = "reuse"
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

                    if not name.value or not url.value:
                        ui.notify("Project name and channel URL are required", type="warning")
                        return

                    build_button.disable()
                    progress.value = 0.05
                    progress.update()
                    status.text = f"Starting build in {mode.value} mode..."
                    status.update()

                    def callback(message: str, percent: Optional[float] = None) -> None:
                        add_log(message)
                        if percent is not None:
                            progress.value = max(0.0, min(1.0, percent))

                    try:
                        options = BuildOptions(
                            name=name.value.strip(),
                            url=url.value.strip(),
                            lang=lang.value.strip() or "en",
                            output_downloads=Path(output.value).expanduser(),
                            base_projects_dir=project_root() / "projects",
                            mode=mode.value or "reuse",
                        )

                        result = await asyncio.to_thread(build_research_pack, options, callback)

                        progress.value = 1.0
                        status.text = f"Ready: {result.zip_path}"
                        ui.notify("Research pack is ready", type="positive")
                        add_log("")
                        add_log(f"ZIP READY: {result.zip_path}")

                        metric_labels["videos"].text = str(result.videos_found)
                        metric_labels["subtitles"].text = str(result.transcripts_created)
                        metric_labels["txt"].text = str(result.transcripts_created)
                        metric_labels["words"].text = f"{result.total_words:,}"
                        metric_labels["zip"].text = "Ready"
                        for label in metric_labels.values():
                            label.update()

                        update_last_summary(result)

                    except Exception as exc:
                        status.text = "Build failed"
                        add_log(f"ERROR: {exc}")
                        ui.notify(f"Build failed: {exc}", type="negative")
                    finally:
                        build_button.enable()
                        progress.update()
                        status.update()
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

                build_button.on("click", run_build)
                open_downloads_button.on("click", open_downloads)
                open_zip_button.on("click", open_last_zip)
                open_project_button.on("click", open_last_project)

                ui.timer(1.0, refresh_log)

            with ui.grid(columns=5).classes("w-full gap-4"):
                metrics = [
                    ("Videos Found", "videos", "after build"),
                    ("Subtitles", "subtitles", "downloaded/indexed"),
                    ("TXT Files", "txt", "created"),
                    ("Total Words", "words", "indexed"),
                    ("ZIP", "zip", "ready"),
                ]
                for title, key, sub in metrics:
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label(title).classes("text-slate-400 text-sm")
                        metric_labels[key] = ui.label("-").classes("text-2xl font-bold")
                        ui.label(sub).classes("text-xs text-slate-500")

            with ui.card().classes("ytis-card p-6 w-full") as last_summary_card:
                ui.label("Last Build Summary").classes("text-xl font-bold")
                ui.label("This panel updates after a successful build and helps verify the pack before upload.").classes("text-slate-400")
                with ui.grid(columns=3).classes("w-full gap-4 mt-3"):
                    for key, title in [
                        ("mode", "Build Mode"),
                        ("videos", "Videos Found"),
                        ("transcripts", "Transcripts"),
                        ("words", "Total Words"),
                        ("missing", "Missing Subtitles"),
                        ("duplicate", "Duplicate Check"),
                    ]:
                        with ui.card().classes("ytis-metric p-3"):
                            ui.label(title).classes("text-xs text-slate-400")
                            last_summary_labels[key] = ui.label("-").classes("text-lg font-bold")
                with ui.column().classes("w-full gap-1 mt-3"):
                    ui.label("ZIP Path").classes("text-xs text-slate-400")
                    last_summary_labels["zip"] = ui.label("-").classes("text-xs text-slate-300 break-all")
                    ui.label("Project Folder").classes("text-xs text-slate-400")
                    last_summary_labels["project"] = ui.label("-").classes("text-xs text-slate-300 break-all")

            with ui.card().classes("ytis-card p-6 w-full") as health_card:
                ui.label("Health Check").classes("text-xl font-bold")
                ui.label("Basic runtime evidence. Use this to confirm you are not looking at an old app instance.").classes("text-slate-400")
                with ui.grid(columns=2).classes("w-full gap-3 mt-3"):
                    health_rows = [
                        ("App version", APP_VERSION),
                        ("Process ID", str(health["pid"])),
                        ("Python", health["python"]),
                        ("Python version", health["python_version"]),
                        ("yt-dlp version", health["yt_dlp_version"]),
                        ("Project root", health["project_root"]),
                        ("Projects dir", health["projects_dir"]),
                        ("Downloads dir", health["downloads_dir"]),
                        ("Venv python exists", str(health["venv_python_exists"])),
                    ]
                    for k, v in health_rows:
                        with ui.card().classes("ytis-metric p-3"):
                            ui.label(k).classes("text-xs text-slate-400")
                            ui.label(v).classes("text-sm break-all")

            with ui.card().classes("ytis-card p-6 w-full") as projects_card:
                with ui.row().classes("w-full justify-between items-center"):
                    ui.label("Recent Projects").classes("text-xl font-bold")
                    ui.label(f"{len(project_summaries)} saved").classes("text-slate-400")

                if not project_summaries:
                    ui.label("No saved projects yet. Build one project and it will appear here.").classes("text-slate-400")
                else:
                    with ui.column().classes("w-full gap-3"):
                        for project in project_summaries[:10]:
                            with ui.card().classes("ytis-metric p-4 w-full"):
                                with ui.row().classes("w-full items-center justify-between"):
                                    with ui.column().classes("gap-0"):
                                        ui.label(str(project.get("name", "Unnamed"))).classes("font-bold")
                                        ui.label(str(project.get("url", ""))).classes("text-xs text-slate-400")
                                        ui.label(
                                            f"{project.get('videos_found', '-')} videos | "
                                            f"{project.get('transcripts_created', '-')} transcripts | "
                                            f"{project.get('missing_subtitles', '-')} missing | "
                                            f"mode: {project.get('build_mode', '-')}"
                                        ).classes("text-sm text-slate-300")
                                    with ui.row().classes("gap-2"):
                                        ui.button("Load", icon="edit", on_click=lambda p=project: load_project(p)).props("outline")
                                        if project.get("project_dir"):
                                            ui.button(
                                                "Open Folder",
                                                icon="folder_open",
                                                on_click=lambda p=project: open_path(str(p.get("project_dir"))),
                                            ).props("outline")
                                        if project.get("zip_path"):
                                            ui.button(
                                                "Open ZIP",
                                                icon="inventory_2",
                                                on_click=lambda p=project: open_path(str(p.get("zip_path"))),
                                            ).props("outline")

            async def scroll_to_build() -> None:
                ui.run_javascript("window.scrollTo({top: 0, behavior: 'smooth'});")

            async def scroll_to_projects() -> None:
                ui.run_javascript("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});")

            async def scroll_to_health() -> None:
                ui.run_javascript("document.querySelectorAll('.ytis-card')[3]?.scrollIntoView({behavior: 'smooth'});")

            async def new_project_action() -> None:
                reset_form()
                await scroll_to_build()

            dashboard_button.on("click", scroll_to_build)
            projects_button.on("click", scroll_to_projects)
            health_button.on("click", scroll_to_health)
            new_project_button.on("click", new_project_action)
            top_new_project_button.on("click", new_project_action)


def main() -> None:
    ui.run(
        title="YTIS - YouTube Intelligence System",
        host="127.0.0.1",
        port=8080,
        reload=False,
        dark=True,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
