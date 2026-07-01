from __future__ import annotations

from nicegui import ui

from ytis.core.transcript_search import SearchResult, export_results, search_transcripts
from ytis.ui.components import open_path
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, val


def render_search(state: AppState) -> None:
    render_shell(state, "/search")

    projects = state.load_projects()
    project_names = ["All projects"] + [val(p, "name", "Unnamed") for p in projects]
    last_results: list[SearchResult] = []
    last_query: dict[str, str] = {"value": ""}

    def open_viewer_for_file(file_path: str) -> None:
        setattr(state, "viewer_file_path", file_path)
        ui.navigate.to("/viewer")

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("Search Transcripts").classes("text-3xl font-bold")
                ui.label("Search across clean TXT transcript files with snippets and exportable results").classes("text-sm text-slate-300")
            ui.button("Open Viewer", icon="article", on_click=lambda: ui.navigate.to("/viewer"), color="primary")

        with ui.grid(columns=3).classes("w-full gap-4"):
            with ui.card().classes("ytis-card p-5 w-full").style("grid-column: span 2;"):
                ui.label("Search Controls").classes("text-xl font-bold")
                with ui.row().classes("w-full gap-3"):
                    selected_project = ui.select(project_names, value=project_names[0] if project_names else "All projects", label="Scope").classes("flex-1")
                    max_results = ui.select([25, 50, 100, 200], value=100, label="Limit").classes("w-40")
                query = ui.input("Search text").classes("w-full")
                ui.label("Search is case-insensitive and scans local clean_txt files. It does not call YouTube.").classes("text-xs text-slate-400")
                with ui.row().classes("gap-2 mt-2"):
                    search_button = ui.button("Search", icon="search", color="primary")
                    export_button = ui.button("Export CSV", icon="download").props("outline")
                    export_button.disable()

            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Useful Searches").classes("text-xl font-bold")
                suggestions = ["pricing", "offer", "funnel", "agency", "cold email", "onboarding", "sales call", "niche"]
                with ui.row().classes("gap-2"):
                    for term in suggestions:
                        ui.button(term, on_click=lambda t=term: setattr(query, "value", t)).props("outline dense")
                ui.separator().classes("bg-slate-700 my-3")
                ui.label("Tip").classes("font-bold")
                ui.label("Use exact business terms first. Broad terms may return too much context.").classes("text-sm text-slate-400")

        results_panel = ui.column().classes("w-full gap-2")

        def render_empty() -> None:
            results_panel.clear()
            with results_panel:
                with ui.card().classes("ytis-card p-5 w-full"):
                    ui.label("Results").classes("text-xl font-bold")
                    ui.label("Run a search to show transcript snippets, source files, and match counts here.").classes("text-slate-400")

        def render_results(results: list[SearchResult], q: str) -> None:
            results_panel.clear()
            with results_panel:
                with ui.card().classes("ytis-card p-5 w-full"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label(f"{len(results)} results for: {q}").classes("text-xl font-bold")
                        ui.label(f"Scope: {selected_project.value}").classes("text-sm text-slate-400")
                    if not results:
                        ui.label("No matches found. Try a shorter or different term.").classes("text-slate-400")

                for result in results:
                    with ui.card().classes("ytis-mini-card p-4 w-full"):
                        with ui.row().classes("w-full justify-between items-start gap-4"):
                            with ui.column().classes("gap-1 flex-1"):
                                ui.label(result.file_name).classes("font-bold")
                                ui.label(f"{result.project} | video id: {result.video_id or '-'} | matches: {result.match_count}").classes("text-xs text-blue-300")
                                ui.label(result.snippet).classes("text-sm text-slate-300")
                            with ui.column().classes("gap-2"):
                                ui.button("Open in Viewer", icon="article", on_click=lambda p=result.file_path: open_viewer_for_file(p)).props("outline dense")
                                ui.button("Open TXT", icon="description", on_click=lambda p=result.file_path: open_path(p)).props("outline dense")

        def run_search() -> None:
            nonlocal last_results
            q = (query.value or "").strip()
            if not q:
                ui.notify("Enter search text", type="warning")
                return

            last_query["value"] = q
            last_results = search_transcripts(
                projects=projects,
                query=q,
                project_name=selected_project.value or "All projects",
                limit=int(max_results.value or 100),
            )
            render_results(last_results, q)
            if last_results:
                export_button.enable()
            else:
                export_button.disable()

        def run_export() -> None:
            if not last_results:
                ui.notify("No results to export", type="warning")
                return
            path = export_results(last_results, state.downloads_dir, last_query["value"])
            ui.notify(f"Exported: {path}", type="positive")
            open_path(path)

        search_button.on("click", run_search)
        export_button.on("click", run_export)
        query.on("keydown.enter", lambda e: run_search())

        render_empty()
