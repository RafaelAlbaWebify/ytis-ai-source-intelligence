from __future__ import annotations

from nicegui import ui

from ytis.core.pack_inspector import inspect_pack
from ytis.ui.components import open_path
from ytis.ui.context import preferred_project_name
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, val


def _status_color(status: str) -> str:
    if status == "upload-ready":
        return "text-green-400"
    if status == "review":
        return "text-yellow-400"
    return "text-red-400"


def _preview_color(status: str) -> str:
    if status == "included":
        return "text-green-400"
    if status in {"project-only", "zip-only"}:
        return "text-yellow-400"
    return "text-red-400"


def render_inspect(state: AppState) -> None:
    render_shell(state, "/inspector")

    projects = state.load_projects()
    project_names = [val(p, "name", "Unnamed") for p in projects]
    default_project = preferred_project_name(state, project_names)

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center ytis-toolbar-row"):
            with ui.column().classes("gap-0"):
                ui.label("Inspect Pack").classes("text-3xl font-bold")
                ui.label("Verify the actual ZIP contents before upload").classes("text-sm text-slate-300")
            ui.button("Build New Pack", icon="add", on_click=lambda: ui.navigate.to("/build"), color="primary")

        selected_project = ui.select(
            project_names,
            value=default_project if default_project in project_names else (project_names[0] if project_names else None),
            label="Project",
        ).classes("w-full max-w-2xl")

        content = ui.column().classes("w-full gap-4")

        def selected_project_data() -> dict:
            name = selected_project.value
            return next((p for p in projects if val(p, "name") == name), {}) if projects else {}

        def render_report() -> None:
            content.clear()
            project = selected_project_data()

            with content:
                if not project:
                    with ui.card().classes("ytis-card p-5 w-full"):
                        ui.label("No project selected").classes("text-xl font-bold")
                    return

                report = inspect_pack(project)

                with ui.grid().classes("ytis-grid-5"):
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label("Status").classes("text-sm text-slate-400")
                        ui.label(report.status.upper()).classes(f"text-2xl font-bold {_status_color(report.status)}")
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label("ZIP Size").classes("text-sm text-slate-400")
                        ui.label(f"{report.zip_size_mb} MB").classes("text-2xl font-bold")
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label("Files").classes("text-sm text-slate-400")
                        ui.label(str(report.total_files)).classes("text-2xl font-bold")
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label("TXT / SRT").classes("text-sm text-slate-400")
                        ui.label(f"{report.clean_txt_count} / {report.raw_srt_count}").classes("text-2xl font-bold")
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label("Preview").classes("text-sm text-slate-400")
                        ui.label(report.preview_status.upper()).classes(f"text-2xl font-bold {_preview_color(report.preview_status)}")

                with ui.grid().classes("ytis-grid-2"):
                    with ui.card().classes("ytis-card p-5 w-full"):
                        ui.label("Upload Readiness").classes("text-xl font-bold")
                        ui.label(report.issue_text()).classes("text-sm text-slate-300")
                        ui.separator().classes("bg-slate-700 my-3")
                        with ui.row().classes("gap-2"):
                            if report.zip_exists:
                                ui.button("Open ZIP", icon="inventory_2", on_click=lambda p=report.zip_path: open_path(p), color="primary")
                            else:
                                ui.button("Open ZIP", icon="inventory_2").props("disable")
                            if project.get("project_dir"):
                                ui.button("Open Project Folder", icon="folder_open", on_click=lambda p=project: open_path(str(p["project_dir"]))).props("outline")
                            ui.button("Go to Analyze", icon="psychology", on_click=lambda: ui.navigate.to("/analyze")).props("outline")

                    with ui.card().classes("ytis-card p-5 w-full"):
                        ui.label("Source Preview Validation").classes("text-xl font-bold")
                        rows = [
                            ("Project image", "Present" if report.preview_project_image_exists else "Missing"),
                            ("Project metadata", "Present" if report.preview_project_metadata_exists else "Missing"),
                            ("ZIP image", "Present" if report.preview_zip_image_exists else "Missing"),
                            ("ZIP metadata", "Present" if report.preview_zip_metadata_exists else "Missing"),
                            ("Project image size", f"{report.preview_project_image_size_kb} KB"),
                            ("ZIP image size", f"{report.preview_zip_image_size_kb} KB"),
                        ]
                        for key, value in rows:
                            good = value not in {"Missing", "0.0 KB"}
                            with ui.row().classes("w-full justify-between border-b border-slate-800 py-1"):
                                ui.label(key).classes("text-sm text-slate-300")
                                ui.label(value).classes("text-sm " + ("text-green-400" if good else "text-red-400"))
                        if report.preview_title or report.preview_subtitle:
                            ui.separator().classes("bg-slate-700 my-2")
                            ui.label(report.preview_title or "-").classes("text-sm font-bold")
                            ui.label(report.preview_subtitle or "-").classes("text-xs text-slate-400")
                        if report.preview_project_image_path:
                            ui.label(report.preview_project_image_path).classes("text-xs text-slate-500 break-all")

                with ui.grid().classes("ytis-grid-2"):
                    with ui.card().classes("ytis-card p-5 w-full"):
                        ui.label("Expected Files").classes("text-xl font-bold")
                        for expected, present in report.expected_present.items():
                            with ui.row().classes("w-full justify-between border-b border-slate-800 py-1"):
                                ui.label(expected).classes("text-sm text-slate-300")
                                ui.label("Present" if present else "Missing").classes("text-sm " + ("text-green-400" if present else "text-red-400"))

                    with ui.card().classes("ytis-card p-5 w-full"):
                        ui.label("File Type Counts").classes("text-xl font-bold")
                        rows = [
                            ("raw_srt .srt", report.raw_srt_count),
                            ("clean_txt .txt", report.clean_txt_count),
                            ("Markdown .md", report.md_count),
                            ("CSV .csv", report.csv_count),
                            ("JSON .json", report.json_count),
                        ]
                        for key, value in rows:
                            with ui.row().classes("w-full justify-between border-b border-slate-800 py-1"):
                                ui.label(key).classes("text-sm text-slate-400")
                                ui.label(str(value)).classes("text-sm font-bold")

                with ui.card().classes("ytis-card p-5 w-full"):
                    ui.label("Largest Files").classes("text-xl font-bold")
                    if not report.largest_files:
                        ui.label("No files found.").classes("text-slate-400")
                    for item in report.largest_files:
                        with ui.row().classes("w-full justify-between gap-3 border-b border-slate-800 py-1 ytis-card-row"):
                            ui.label(str(item["name"])).classes("text-xs text-slate-300 break-all")
                            ui.label(f'{item["size_mb"]} MB').classes("text-xs text-blue-300")

        selected_project.on("update:model-value", lambda e: render_report())
        render_report()
