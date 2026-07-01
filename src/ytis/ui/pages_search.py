from __future__ import annotations

from pathlib import Path

from nicegui import ui

from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, val


def render_search(state: AppState) -> None:
    render_shell(state, "/search")

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("Search Transcripts").classes("text-3xl font-bold")
                ui.label("Search clean TXT files inside saved projects").classes("text-sm text-slate-300")

        projects = state.load_projects()
        project_names = [val(p, "name", "Unnamed") for p in projects]
        selected_project = ui.select(project_names, value=project_names[0] if project_names else None, label="Project").classes("w-full")
        query = ui.input("Search text").classes("w-full")
        results = ui.column().classes("w-full gap-2")

        def run_search() -> None:
            results.clear()
            q = (query.value or "").strip().lower()
            if not q:
                ui.notify("Enter search text", type="warning")
                return

            project = next((p for p in projects if val(p, "name") == selected_project.value), None)
            if not project:
                ui.notify("Select a project", type="warning")
                return

            clean_dir = Path(val(project, "project_dir", "")) / "clean_txt"
            if not clean_dir.exists():
                ui.notify("clean_txt folder not found for this project", type="negative")
                return

            matches = []
            for txt in sorted(clean_dir.glob("*.txt")):
                try:
                    content = txt.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                idx = content.lower().find(q)
                if idx >= 0:
                    start = max(0, idx - 140)
                    end = min(len(content), idx + 260)
                    matches.append((txt.name, content[start:end].replace("\n", " ")))

            with results:
                ui.label(f"{len(matches)} matches").classes("text-lg font-bold")
                for name, snippet in matches[:50]:
                    with ui.card().classes("ytis-mini-card p-3 w-full"):
                        ui.label(name).classes("font-bold")
                        ui.label(snippet).classes("text-sm text-slate-300")

        ui.button("Search", icon="search", on_click=run_search, color="primary")
        results
