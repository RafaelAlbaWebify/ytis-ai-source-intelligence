from __future__ import annotations

from pathlib import Path

from nicegui import ui

from ytis.core.transcript_viewer import list_transcripts, read_transcript, search_inside_text
from ytis.ui.components import open_path
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, val


def _file_label(path: Path) -> str:
    name = path.name
    if len(name) <= 95:
        return name
    return name[:46] + "..." + name[-46:]


def render_viewer(state: AppState) -> None:
    render_shell(state, "/viewer")

    projects = state.load_projects()
    project_names = [val(p, "name", "Unnamed") for p in projects]
    latest = state.current_project or state.load_latest_project()
    default_project = val(latest, "name", project_names[0] if project_names else "")

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("Transcript Viewer").classes("text-3xl font-bold")
                ui.label("Read and search transcript TXT files inside YTIS").classes("text-sm text-slate-300")
            ui.button("Search All", icon="search", on_click=lambda: ui.navigate.to("/search"), color="primary")

        selected_project = ui.select(
            project_names,
            value=default_project if default_project in project_names else (project_names[0] if project_names else None),
            label="Project",
        ).classes("w-full max-w-3xl")

        transcript_select_container = ui.column().classes("w-full")
        details_container = ui.column().classes("w-full gap-4")

        state_holder: dict[str, object] = {"files": [], "selected": None, "info": None}

        def selected_project_data() -> dict:
            name = selected_project.value
            return next((p for p in projects if val(p, "name") == name), {}) if projects else {}

        def render_details() -> None:
            details_container.clear()
            selected = state_holder.get("selected")
            with details_container:
                if not selected:
                    with ui.card().classes("ytis-card p-5 w-full"):
                        ui.label("No transcript selected").classes("text-xl font-bold")
                    return

                path = Path(str(selected))
                try:
                    info = read_transcript(path)
                    state_holder["info"] = info
                except Exception as exc:
                    with ui.card().classes("ytis-card p-5 w-full"):
                        ui.label("Could not read transcript").classes("text-xl font-bold")
                        ui.label(str(exc)).classes("text-red-400")
                    return

                with ui.grid(columns=4).classes("w-full gap-3"):
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label("Words").classes("text-sm text-slate-400")
                        ui.label(f"{info.word_count:,}").classes("text-2xl font-bold")
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label("Characters").classes("text-sm text-slate-400")
                        ui.label(f"{info.char_count:,}").classes("text-2xl font-bold")
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label("Lines").classes("text-sm text-slate-400")
                        ui.label(f"{info.line_count:,}").classes("text-2xl font-bold")
                    with ui.card().classes("ytis-metric p-4"):
                        ui.label("Size").classes("text-sm text-slate-400")
                        ui.label(f"{info.size_kb} KB").classes("text-2xl font-bold")

                with ui.card().classes("ytis-card p-5 w-full"):
                    with ui.row().classes("w-full justify-between items-start gap-4"):
                        with ui.column().classes("gap-1 flex-1"):
                            ui.label(info.file_name).classes("text-xl font-bold")
                            ui.label(f"Video ID: {info.video_id or '-'}").classes("text-sm text-blue-300")
                            ui.label(str(info.path)).classes("text-xs text-slate-500 break-all")
                        with ui.row().classes("gap-2"):
                            ui.button("Open TXT", icon="description", on_click=lambda p=info.path: open_path(p)).props("outline")
                            ui.button("Copy Text", icon="content_copy", on_click=lambda: ui.run_javascript("navigator.clipboard.writeText(document.getElementById('ytis-transcript-textarea').value)")).props("outline")

                    search_term = ui.input("Search inside this transcript").classes("w-full")
                    snippets_container = ui.column().classes("w-full gap-2")

                    def run_inner_search() -> None:
                        snippets_container.clear()
                        snippets = search_inside_text(info.text, search_term.value or "")
                        with snippets_container:
                            ui.label(f"{len(snippets)} matches").classes("font-bold")
                            for snippet in snippets[:20]:
                                with ui.card().classes("ytis-mini-card p-3 w-full"):
                                    ui.label(snippet).classes("text-sm text-slate-300")

                    ui.button("Search inside transcript", icon="search", on_click=run_inner_search, color="primary").classes("mt-2")
                    snippets_container

                with ui.card().classes("ytis-card p-5 w-full"):
                    ui.label("Transcript Text").classes("text-xl font-bold")
                    ui.textarea(value=info.text).classes("w-full").props("readonly rows=28 id=ytis-transcript-textarea").style(
                        "font-family: Consolas, monospace; font-size: 12px; line-height: 1.45;"
                    )

        def render_transcript_select() -> None:
            transcript_select_container.clear()
            project = selected_project_data()
            files = list_transcripts(project)
            state_holder["files"] = files
            options = {_file_label(path): str(path) for path in files}

            with transcript_select_container:
                with ui.card().classes("ytis-card p-5 w-full"):
                    ui.label("Transcript Selection").classes("text-xl font-bold")
                    if not files:
                        ui.label("No clean_txt transcript files found for this project.").classes("text-slate-400")
                        state_holder["selected"] = None
                        render_details()
                        return

                    selected_label = list(options.keys())[0]
                    transcript_select = ui.select(
                        list(options.keys()),
                        value=selected_label,
                        label=f"Transcript file ({len(files)} available)",
                    ).classes("w-full")
                    state_holder["selected"] = options[selected_label]

                    def on_change() -> None:
                        state_holder["selected"] = options.get(transcript_select.value)
                        render_details()

                    transcript_select.on("update:model-value", lambda e: on_change())
                    with ui.row().classes("gap-2 mt-2"):
                        ui.button("Open Selected", icon="article", on_click=render_details, color="primary")
                        ui.button("Open Project Folder", icon="folder_open", on_click=lambda p=project: open_path(str(p.get("project_dir", "")))).props("outline")

            render_details()

        selected_project.on("update:model-value", lambda e: render_transcript_select())
        render_transcript_select()
