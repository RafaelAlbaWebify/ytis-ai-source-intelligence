from __future__ import annotations

from nicegui import ui

from ytis.ui.components import open_path, page_title
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, fmt_int, val


def render_projects(state: AppState) -> None:
    render_shell(state, "/projects")
    projects = state.load_projects()

    with ui.column().classes("ytis-page gap-4"):
        page_title("Projects", "Saved YouTube research packs and local output folders")

        with ui.card().classes("ytis-card p-5 w-full"):
            if not projects:
                ui.label("No saved projects yet.").classes("text-slate-400")
                return

            columns = [
                {"name": "name", "label": "Project", "field": "name", "align": "left"},
                {"name": "mode", "label": "Mode", "field": "build_mode"},
                {"name": "videos", "label": "Videos", "field": "videos_found"},
                {"name": "transcripts", "label": "Transcripts", "field": "transcripts_created"},
                {"name": "words", "label": "Words", "field": "total_words"},
                {"name": "built", "label": "Built", "field": "built_at"},
            ]
            rows = []
            for p in projects:
                rows.append({
                    "name": val(p, "name", "Unnamed"),
                    "build_mode": val(p, "build_mode"),
                    "videos_found": val(p, "videos_found", "0"),
                    "transcripts_created": val(p, "transcripts_created", "0"),
                    "total_words": fmt_int(p.get("total_words")),
                    "built_at": val(p, "built_at", val(p, "last_updated_at", "-")),
                    "project_dir": val(p, "project_dir", ""),
                    "zip_path": val(p, "zip_path", ""),
                })

            table = ui.table(columns=columns, rows=rows, row_key="name").classes("w-full")
            table.props("flat bordered dark")

            with ui.row().classes("gap-2 mt-3"):
                ui.button("Open selected folder", icon="folder_open", on_click=lambda: open_path(table.selected[0]["project_dir"]) if table.selected else ui.notify("Select a row first", type="warning")).props("outline")
                ui.button("Open selected ZIP", icon="inventory_2", on_click=lambda: open_path(table.selected[0]["zip_path"]) if table.selected else ui.notify("Select a row first", type="warning")).props("outline")
