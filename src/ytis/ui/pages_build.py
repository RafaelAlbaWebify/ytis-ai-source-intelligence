from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from nicegui import ui

from ytis.core.builder import BuildOptions, build_research_pack
from ytis.ui.components import page_title, source_preview
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState


def render_build(state: AppState) -> None:
    render_shell(state, "/build")

    with ui.column().classes("ytis-page gap-4"):
        page_title("Build Research Pack", "Create or refresh upload-ready transcript packages")

        with ui.grid(columns=2).classes("w-full gap-4"):
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

            with ui.column().classes("gap-4"):
                preview_container = ui.column().classes("w-full")
                log = ui.log(max_lines=400).classes("ytis-log w-full p-3").style("height: 360px;")

        def redraw_preview() -> None:
            preview_container.clear()
            with preview_container:
                source_preview(url.value or "", name.value or "")

        redraw_preview()

        def open_path(path: str) -> None:
            from ytis.ui.components import open_path as open_local_path
            open_local_path(path)

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
        open_downloads.on("click", lambda: open_path(str(state.downloads_dir)))
        open_zip.on("click", lambda: open_path(str(last_zip_path.get("path", ""))))
        open_project.on("click", lambda: open_path(str(last_project_path.get("path", ""))))
        url.on("update:model-value", lambda e: redraw_preview())
        name.on("update:model-value", lambda e: redraw_preview())
