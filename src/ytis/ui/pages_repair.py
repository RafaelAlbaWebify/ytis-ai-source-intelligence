from __future__ import annotations

from nicegui import ui

from ytis.core.transcript_repair import ProjectRepairReport, analyze_project, repair_project
from ytis.ui.components import open_path
from ytis.ui.context import preferred_project_name
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, val


def _fmt(value: int) -> str:
    return f"{value:,}"


def render_repair(state: AppState) -> None:
    render_shell(state, "/repair")

    projects = state.load_projects()
    project_names = [val(p, "name", "Unnamed") for p in projects]
    default_project = preferred_project_name(state, project_names)

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center ytis-toolbar-row"):
            with ui.column().classes("gap-0"):
                ui.label("Transcript Repair").classes("text-3xl font-bold")
                ui.label("Detect and repair repeated adjacent transcript text in clean_txt files").classes("text-sm text-slate-300")
            ui.button("Open Viewer", icon="article", on_click=lambda: ui.navigate.to("/viewer"), color="primary")

        with ui.card().classes("ytis-card p-5 w-full"):
            ui.label("Repair Controls").classes("text-xl font-bold")
            selected_project = ui.select(
                project_names,
                value=default_project if default_project in project_names else (project_names[0] if project_names else None),
                label="Project",
            ).classes("w-full")
            ui.label("This repair is local-only. It backs up clean_txt before rewriting. After repair, use Build Pack with repackage mode to regenerate the ZIP and combined MD.").classes("text-sm text-yellow-300")
            with ui.row().classes("gap-2 mt-2"):
                analyze_button = ui.button("Analyze Duplicates", icon="search", color="primary")
                repair_button = ui.button("Repair clean_txt", icon="construction").props("outline")
                ui.button("Go to Repackage", icon="rocket_launch", on_click=lambda: ui.navigate.to("/build")).props("outline")

        output = ui.column().classes("w-full gap-4")

        def selected_project_data() -> dict:
            name = selected_project.value
            return next((p for p in projects if val(p, "name") == name), {}) if projects else {}

        def render_report(report: ProjectRepairReport, repaired: bool = False) -> None:
            output.clear()
            with output:
                with ui.grid().classes("ytis-grid-4"):
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label("Files checked").classes("text-sm text-slate-400")
                        ui.label(str(report.files_checked)).classes("text-2xl font-bold")
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label("Files changed").classes("text-sm text-slate-400")
                        ui.label(str(report.files_changed)).classes("text-2xl font-bold")
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label("Words removed").classes("text-sm text-slate-400")
                        ui.label(_fmt(report.removed_words)).classes("text-2xl font-bold")
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label("Reduction").classes("text-sm text-slate-400")
                        ui.label(f"{report.removed_percent}%").classes("text-2xl font-bold")

                with ui.card().classes("ytis-card p-5 w-full"):
                    ui.label("Repair Summary").classes("text-xl font-bold")
                    ui.label(f"Original words: {_fmt(report.original_words)}").classes("text-sm text-slate-400")
                    ui.label(f"Repaired words: {_fmt(report.repaired_words)}").classes("text-sm text-slate-400")
                    ui.label(f"clean_txt folder: {report.clean_txt_dir}").classes("text-xs text-slate-500 break-all")
                    if repaired:
                        ui.label(f"Backup created: {report.backup_dir}").classes("text-xs text-green-400 break-all")
                        ui.label("Next: use Build Pack -> repackage to rebuild combined MD and ZIP from repaired TXT files.").classes("text-sm text-yellow-300")
                        with ui.row().classes("gap-2"):
                            ui.button("Open Backup", icon="folder_open", on_click=lambda p=report.backup_dir: open_path(p)).props("outline")
                            ui.button("Go to Build Pack", icon="rocket_launch", on_click=lambda: ui.navigate.to("/build"), color="primary")

                with ui.card().classes("ytis-card p-5 w-full"):
                    ui.label("Most affected files").classes("text-xl font-bold")
                    rows = sorted(report.file_reports, key=lambda item: item.removed_words, reverse=True)[:20]
                    if not rows:
                        ui.label("No TXT files found.").classes("text-slate-400")
                    for item in rows:
                        with ui.row().classes("w-full justify-between gap-3 border-b border-slate-800 py-1"):
                            ui.label(item.file_name).classes("text-xs text-slate-300 break-all")
                            ui.label(f"-{item.removed_words:,} words ({item.removed_percent}%)").classes("text-xs text-blue-300")

        def run_analyze() -> None:
            project = selected_project_data()
            if not project:
                ui.notify("Select a project", type="warning")
                return
            report = analyze_project(project)
            render_report(report, repaired=False)

        def run_repair() -> None:
            project = selected_project_data()
            if not project:
                ui.notify("Select a project", type="warning")
                return
            report = repair_project(project)
            render_report(report, repaired=True)
            ui.notify("Transcript repair complete. clean_txt was backed up first.", type="positive")

        analyze_button.on("click", run_analyze)
        repair_button.on("click", run_repair)
        selected_project.on("update:model-value", lambda e: run_analyze())

        if projects:
            run_analyze()
