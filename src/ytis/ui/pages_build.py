from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from nicegui import ui

from ytis.core.builder import BuildOptions, build_research_pack
from ytis.core.source_preview import SourcePreview, capture_source_preview, preview_from_url_only
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState


def render_build(state: AppState) -> None:
    render_shell(state, "/build")

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("Build Research Pack").classes("text-3xl font-bold")
                ui.label("Create or refresh upload-ready transcript packages").classes("text-sm text-slate-300")
            ui.button("Inspect Pack", icon="inventory_2", on_click=lambda: ui.navigate.to("/inspect"), color="primary")

        with ui.row().classes("w-full gap-4 items-start"):
            with ui.column().classes("gap-4").style("flex: 1.35; min-width: 520px;"):
                with ui.card().classes("ytis-card p-5 w-full"):
                    ui.label("Build Settings").classes("text-xl font-bold")

                    name = ui.input("Project name", value=state.current_project.get("name", "") if state.current_project else "").classes("w-full")
                    url = ui.input("Channel/Video URL", value=state.current_project.get("url", "") if state.current_project else "").classes("w-full")
                    with ui.row().classes("w-full gap-3"):
                        lang = ui.select(["en", "es"], value=state.current_project.get("language", "en") if state.current_project else "en", label="Language").classes("flex-1")
                        output = ui.input("Downloads output folder", value=str(state.downloads_dir)).classes("flex-[2]")
                    mode = ui.select(["reuse", "refresh", "repackage"], value="reuse", label="Build mode").classes("w-full")
                    ui.label("reuse = existing subtitles | refresh = YouTube | repackage = ZIP from existing files").classes("text-xs text-slate-400")

                    progress = ui.linear_progress(value=0).classes("w-full mt-3")
                    status = ui.label("Ready").classes("text-sm text-slate-300")

                    with ui.row().classes("gap-2 mt-2"):
                        build_button = ui.button("Build Research Pack", icon="rocket_launch", color="primary")
                        open_downloads = ui.button("Open Downloads", icon="folder_open").props("outline")
                        open_zip = ui.button("Open ZIP", icon="inventory_2").props("outline")
                        open_project = ui.button("Open Project", icon="folder").props("outline")

                    open_zip.disable()
                    open_project.disable()

                with ui.card().classes("ytis-card p-5 w-full"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Process Log").classes("text-xl font-bold")
                        ui.label("Build and preview capture output").classes("text-xs text-slate-400")
                    log = ui.log(max_lines=500).classes("ytis-log w-full p-3").style("height: 330px;")

            with ui.column().classes("gap-4").style("flex: 0.9; min-width: 360px;"):
                preview_container = ui.column().classes("w-full")
                with ui.card().classes("ytis-card p-5 w-full"):
                    ui.label("Source Preview Capture").classes("text-xl font-bold")
                    ui.label("Capture saves a real source preview into the project folder under source_preview. Video URLs use YouTube thumbnails. Channel URLs use yt-dlp metadata when available.").classes("text-sm text-slate-400")
                    capture_button = ui.button("Capture Preview", icon="photo_camera", color="primary").classes("w-full mt-2")
                    ui.button("Open Source Preview Folder", icon="folder_open", on_click=lambda: open_preview_folder()).props("outline").classes("w-full mt-2")
                    preview_status = ui.label("No local preview captured yet.").classes("text-xs text-slate-400 mt-2")

        preview_state: dict[str, SourcePreview | None] = {"preview": None}

        def image_source(preview: SourcePreview) -> str:
            return preview.image_data_uri or preview.image_url or "https://www.youtube.com/img/desktop/yt_1200.png"

        def render_preview(preview: SourcePreview | None = None) -> None:
            preview_container.clear()
            current = preview or preview_from_url_only(url.value or "", name.value or "")
            preview_state["preview"] = current
            with preview_container:
                with ui.card().classes("ytis-card p-5 w-full"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Source Preview").classes("text-xl font-bold")
                        ui.label(current.source_type).classes("text-xs text-red-400")
                    ui.image(image_source(current)).classes("w-full rounded-xl").style("height: 170px; object-fit: cover; background: #0f172a;")
                    ui.label(current.title or name.value or "YouTube Source").classes("text-lg font-bold")
                    ui.label(current.subtitle).classes("text-sm text-slate-400")
                    ui.label(url.value or "-").classes("text-xs text-blue-300 break-all")
                    ui.label(current.status).classes("text-xs text-green-400" if "Captured" in current.status else "text-xs text-slate-500")
                    if current.image_path:
                        ui.label(current.image_path).classes("text-xs text-slate-500 break-all")
                    if current.error:
                        ui.label(current.error).classes("text-xs text-red-400 break-all")

        def open_preview_folder() -> None:
            from ytis.ui.components import open_path
            project_name = name.value or "YTIS_Source"
            folder = state.projects_dir() / project_name / "source_preview"
            open_path(folder)

        async def run_capture() -> None:
            if not url.value or not name.value:
                ui.notify("Project name and URL are required for capture", type="warning")
                return
            capture_button.disable()
            preview_status.text = "Capturing preview..."
            preview_status.update()
            log.push("Capturing source preview...")
            try:
                captured = await asyncio.to_thread(capture_source_preview, url.value, name.value, state.projects_dir())
                render_preview(captured)
                preview_status.text = captured.status
                log.push(captured.status)
                if captured.image_path:
                    log.push(f"Preview saved: {captured.image_path}")
                    ui.notify("Source preview captured", type="positive")
                else:
                    log.push(f"Preview capture did not save an image: {captured.error}")
                    ui.notify("Preview capture failed. See log.", type="warning")
            except Exception as exc:
                preview_status.text = "Preview capture failed"
                log.push(f"ERROR capturing preview: {exc}")
                ui.notify(f"Preview capture failed: {exc}", type="negative")
            finally:
                capture_button.enable()
                preview_status.update()

        render_preview()

        def open_local_path(path: str) -> None:
            from ytis.ui.components import open_path
            open_path(path)

        last_zip_path: dict[str, Path] = {}
        last_project_path: dict[str, Path] = {}

        async def run_build() -> None:
            if not name.value or not url.value:
                ui.notify("Project name and URL are required", type="warning")
                return

            build_button.disable()
            log.clear()
            progress.value = 0.05
            status.text = "Starting..."
            progress.update()
            status.update()

            def callback(message: str, percent: Optional[float] = None) -> None:
                log.push(message)
                if percent is not None:
                    progress.value = max(0.0, min(1.0, percent))

            try:
                options = BuildOptions(
                    name=name.value.strip(),
                    url=url.value.strip(),
                    lang=lang.value or "en",
                    output_downloads=Path(output.value).expanduser(),
                    base_projects_dir=state.projects_dir(),
                    mode=mode.value or "reuse",
                )
                result = await asyncio.to_thread(build_research_pack, options, callback)
                progress.value = 1.0
                status.text = f"Ready: {result.zip_path}"
                log.push(f"ZIP READY: {result.zip_path}")

                project = {
                    "name": name.value.strip(),
                    "url": url.value.strip(),
                    "language": lang.value or "en",
                    "build_mode": result.mode,
                    "videos_found": result.videos_found,
                    "transcripts_created": result.transcripts_created,
                    "missing_subtitles": result.missing_subtitles,
                    "total_words": result.total_words,
                    "zip_path": str(result.zip_path),
                    "project_dir": str(result.project_dir),
                }
                state.set_current_project(project)

                last_zip_path["path"] = result.zip_path
                last_project_path["path"] = result.project_dir
                open_zip.enable()
                open_project.enable()
                ui.notify("Research pack is ready", type="positive")
            except Exception as exc:
                status.text = "Build failed"
                log.push(f"ERROR: {exc}")
                ui.notify(f"Build failed: {exc}", type="negative")
            finally:
                build_button.enable()
                progress.update()
                status.update()

        build_button.on("click", run_build)
        capture_button.on("click", run_capture)
        open_downloads.on("click", lambda: open_local_path(str(state.downloads_dir)))
        open_zip.on("click", lambda: open_local_path(str(last_zip_path.get("path", ""))))
        open_project.on("click", lambda: open_local_path(str(last_project_path.get("path", ""))))
        url.on("update:model-value", lambda e: render_preview())
        name.on("update:model-value", lambda e: render_preview())
