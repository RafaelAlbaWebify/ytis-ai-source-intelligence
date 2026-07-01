from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from nicegui import ui

from ytis.core.builder import BuildOptions, build_research_pack
from ytis.core.paths import default_downloads_dir, project_root


CURRENT_LOG: list[str] = []


def add_log(message: str) -> None:
    CURRENT_LOG.append(message)


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
    </style>
    """)

    with ui.row().classes("w-full min-h-screen text-white"):
        with ui.column().classes("ytis-sidebar p-5 gap-4 w-72"):
            with ui.row().classes("items-center gap-3"):
                ui.label("▶").classes("text-3xl text-red-500")
                with ui.column().classes("gap-0"):
                    ui.label("YTIS").classes("text-3xl font-bold text-blue-300")
                    ui.label("YouTube Intelligence System").classes("text-sm text-slate-300")
                    ui.label("v0.1.1").classes("text-xs text-slate-500")
            ui.separator().classes("bg-slate-700")
            ui.button("Dashboard", icon="dashboard").classes("w-full justify-start")
            ui.button("Projects", icon="folder").classes("w-full justify-start").props("outline")
            ui.button("New Project", icon="add_circle").classes("w-full justify-start").props("outline")
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
                ui.button("New Project", icon="add", color="primary").classes("px-6")

            # Metric labels updated after a build.
            metric_labels: dict[str, ui.label] = {}

            with ui.card().classes("ytis-card p-6 w-full"):
                ui.label("Build Research Pack").classes("text-xl font-bold")
                ui.label("Enter a YouTube channel /videos URL and create a clean ZIP for analysis.").classes("text-slate-300")

                with ui.grid(columns=2).classes("w-full gap-4 mt-4"):
                    name = ui.input("Project name", placeholder="ScottMillar").classes("w-full")
                    url = ui.input("Channel URL", placeholder="https://www.youtube.com/@channel/videos").classes("w-full")
                    lang = ui.input("Language", value="en").classes("w-full")
                    output = ui.input("Downloads output folder", value=str(default_downloads_dir())).classes("w-full")

                progress = ui.linear_progress(value=0).classes("w-full mt-4")
                status = ui.label("Waiting to start").classes("text-slate-300")
                log_area = ui.textarea("Build log").classes("w-full h-64").props("readonly")

                with ui.row().classes("gap-3 mt-2"):
                    build_button = ui.button("Build Research Pack", icon="rocket_launch", color="primary")
                    open_downloads_button = ui.button("Open Downloads", icon="folder_open").props("outline")

                async def refresh_log() -> None:
                    log_area.value = "\n".join(CURRENT_LOG[-250:])
                    log_area.update()

                async def run_build() -> None:
                    CURRENT_LOG.clear()

                    if not name.value or not url.value:
                        ui.notify("Project name and channel URL are required", type="warning")
                        return

                    build_button.disable()
                    progress.value = 0.05
                    progress.update()
                    status.text = "Starting build..."
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

                    except Exception as exc:
                        status.text = "Build failed"
                        add_log(f"ERROR: {exc}")
                        ui.notify(f"Build failed: {exc}", type="negative")
                    finally:
                        build_button.enable()
                        progress.update()
                        status.update()
                        await refresh_log()

                async def open_downloads() -> None:
                    import os
                    os.startfile(str(default_downloads_dir()))

                build_button.on("click", run_build)
                open_downloads_button.on("click", open_downloads)

                ui.timer(1.0, refresh_log)

            with ui.grid(columns=5).classes("w-full gap-4"):
                metrics = [
                    ("Videos Found", "videos", "after build"),
                    ("Subtitles", "subtitles", "downloaded"),
                    ("TXT Files", "txt", "created"),
                    ("Total Words", "words", "indexed"),
                    ("ZIP", "zip", "ready"),
                ]
                for title, key, sub in metrics:
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label(title).classes("text-slate-400 text-sm")
                        metric_labels[key] = ui.label("-").classes("text-2xl font-bold")
                        ui.label(sub).classes("text-xs text-slate-500")


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
