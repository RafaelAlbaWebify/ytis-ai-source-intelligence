from __future__ import annotations

from nicegui import ui

from ytis.core.project_hygiene import audit_projects
from ytis.ui.components import open_path, page_title
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, fmt_int, val


def _status_label(status: str) -> str:
    if status == "clean":
        return "Clean"
    if status == "review":
        return "Review"
    return "Broken"


def render_projects(state: AppState) -> None:
    render_shell(state, "/projects")
    projects = audit_projects(state.load_projects())

    with ui.column().classes("ytis-page gap-4"):
        page_title("Projects", "Saved packs, hygiene status, and local output folders")

        clean_count = sum(1 for p in projects if p.get("_hygiene_status") == "clean")
        review_count = sum(1 for p in projects if p.get("_hygiene_status") == "review")
        broken_count = sum(1 for p in projects if p.get("_hygiene_status") == "broken")

        with ui.grid(columns=4).classes("w-full gap-3"):
            with ui.card().classes("ytis-metric p-4"):
                ui.label("Projects").classes("text-sm text-slate-400")
                ui.label(str(len(projects))).classes("text-2xl font-bold")
            with ui.card().classes("ytis-metric p-4"):
                ui.label("Clean").classes("text-sm text-slate-400")
                ui.label(str(clean_count)).classes("text-2xl font-bold text-green-400")
            with ui.card().classes("ytis-metric p-4"):
                ui.label("Review").classes("text-sm text-slate-400")
                ui.label(str(review_count)).classes("text-2xl font-bold text-yellow-400")
            with ui.card().classes("ytis-metric p-4"):
                ui.label("Broken").classes("text-sm text-slate-400")
                ui.label(str(broken_count)).classes("text-2xl font-bold text-red-400")

        with ui.card().classes("ytis-card ytis-table-card p-5 w-full"):
            if not projects:
                ui.label("No saved projects yet.").classes("text-slate-400")
                return

            columns = [
                {"name": "status", "label": "Status", "field": "status", "sortable": True},
                {"name": "name", "label": "Project", "field": "name", "align": "left", "sortable": True},
                {"name": "mode", "label": "Mode", "field": "build_mode", "sortable": True},
                {"name": "videos", "label": "Videos", "field": "videos_found", "sortable": True},
                {"name": "transcripts", "label": "Transcripts", "field": "transcripts_created", "sortable": True},
                {"name": "files", "label": "Files", "field": "file_counts"},
                {"name": "words", "label": "Words", "field": "total_words", "sortable": True},
                {"name": "issues", "label": "Issues", "field": "issues", "align": "left"},
                {"name": "zip", "label": "ZIP", "field": "zip_status"},
            ]
            rows = []
            for p in projects:
                rows.append({
                    "status": _status_label(str(p.get("_hygiene_status", "broken"))),
                    "name": val(p, "name", "Unnamed"),
                    "build_mode": val(p, "build_mode"),
                    "videos_found": val(p, "videos_found", "0"),
                    "transcripts_created": val(p, "transcripts_created", "0"),
                    "file_counts": f"{p.get('_srt_files', 0)} SRT / {p.get('_txt_files', 0)} TXT",
                    "total_words": fmt_int(p.get("total_words")),
                    "issues": str(p.get("_hygiene_issues", "OK")),
                    "zip_status": "Ready" if p.get("zip_path") else "Missing",
                    "project_dir": val(p, "project_dir", ""),
                    "zip_path": val(p, "zip_path", ""),
                })

            table = ui.table(columns=columns, rows=rows, row_key="name", selection="single").classes("w-full")
            table.props("flat bordered dark dense")

            with ui.row().classes("gap-2 mt-3"):
                ui.button("Open selected folder", icon="folder_open", on_click=lambda: open_path(table.selected[0]["project_dir"]) if table.selected else ui.notify("Select a row first", type="warning")).props("outline")
                ui.button("Open selected ZIP", icon="inventory_2", on_click=lambda: open_path(table.selected[0]["zip_path"]) if table.selected else ui.notify("Select a row first", type="warning")).props("outline")
                ui.button("Build new pack", icon="rocket_launch", on_click=lambda: ui.navigate.to("/build"), color="primary")

        with ui.card().classes("ytis-card p-5 w-full"):
            ui.label("Hygiene Rules").classes("text-xl font-bold")
            ui.label("Clean: project folder, summary, ZIP, SRT/TXT files, and video IDs are consistent.").classes("text-sm text-slate-400")
            ui.label("Review: usable but missing non-critical files such as index, missing report, or combined MD.").classes("text-sm text-slate-400")
            ui.label("Broken: missing folder/ZIP/summary, no transcript files, count mismatch, or duplicate video IDs.").classes("text-sm text-slate-400")
