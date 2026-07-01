from __future__ import annotations

from pathlib import Path
from nicegui import ui

from ytis.core.analysis_inbox import (
    FOCUS_OPTIONS, TOPIC_OPTIONS, analysis_stats, filter_analyses,
    list_analyses, read_analysis, save_analysis,
)
from ytis.core.project_hygiene import audit_projects
from ytis.ui.components import open_path
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, val

def _metric(title: str, value: str, caption: str = "") -> None:
    with ui.card().classes("ytis-metric p-4"):
        ui.label(title).classes("text-sm text-slate-400")
        ui.label(value).classes("text-2xl font-bold whitespace-nowrap")
        if caption:
            ui.label(caption).classes("text-xs text-slate-500")

def _project_root(state: AppState) -> Path:
    return Path(getattr(state, "project_root", "") or Path.cwd())

def render_analysis_inbox(state: AppState) -> None:
    render_shell(state, "/analysis-inbox")

    project_root = _project_root(state)
    projects = audit_projects(state.load_projects())
    project_names = [val(p, "name", "Unnamed") for p in projects]
    records = list_analyses(project_root)
    stats = analysis_stats(records)

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("Analysis Inbox").classes("text-3xl font-bold")
                ui.label("Paste ChatGPT results back into YTIS and keep the research loop alive").classes("text-sm text-slate-300")
            with ui.row().classes("gap-2"):
                ui.button("Intelligence", icon="hub", on_click=lambda: ui.navigate.to("/intelligence")).props("outline")
                ui.button("Open Results Folder", icon="folder_open", on_click=lambda: open_path(project_root / "analysis_results"), color="primary")

        with ui.grid(columns=5).classes("w-full gap-3"):
            _metric("Saved analyses", str(stats["records"]), "ChatGPT results")
            _metric("Projects", str(stats["projects"]), "covered")
            _metric("Topics", str(stats["topics"]), "covered")
            _metric("Focus presets", str(stats["focus_presets"]), "used")
            _metric("Words", f'{stats["words"]:,}', "saved analysis")

        with ui.card().classes("ytis-card p-5 w-full"):
            ui.label("Save New ChatGPT Analysis").classes("text-xl font-bold")
            ui.label("After ChatGPT analyzes a YTIS bundle or evidence pack, paste the answer here and save it into the local research library.").classes("text-sm text-slate-400")

            with ui.grid(columns=2).classes("w-full gap-3"):
                title_input = ui.input("Analysis title", value="").classes("w-full")
                focus_select = ui.select(FOCUS_OPTIONS, value="Business lessons", label="Focus preset").classes("w-full")
            with ui.grid(columns=2).classes("w-full gap-3"):
                topic_select = ui.select(TOPIC_OPTIONS, value="All topics", label="Topic").classes("w-full")
                project_select = ui.select(project_names, value=project_names[:1] if project_names else [], multiple=True, label="Related projects").classes("w-full")
            with ui.grid(columns=2).classes("w-full gap-3"):
                source_bundle = ui.input("Source bundle filename/path", value="").classes("w-full")
                source_evidence = ui.input("Source evidence pack filename/path", value="").classes("w-full")

            notes = ui.textarea("Optional notes / why this analysis matters").classes("w-full").props("rows=3")
            analysis_text = ui.textarea("Paste ChatGPT response here").classes("w-full").props("rows=16")
            save_status = ui.label("Ready").classes("text-xs text-slate-400")

            with ui.row().classes("gap-2"):
                save_btn = ui.button("Save Analysis", icon="save", color="primary")
                clear_btn = ui.button("Clear Form", icon="backspace").props("outline")

            def do_clear() -> None:
                for element in [title_input, source_bundle, source_evidence, notes, analysis_text]:
                    element.value = ""
                    element.update()
                save_status.text = "Form cleared"
                save_status.update()

            def do_save() -> None:
                text = analysis_text.value or ""
                if not text.strip():
                    ui.notify("Paste a ChatGPT response first", type="warning")
                    return
                selected_projects = project_select.value or []
                if isinstance(selected_projects, str):
                    selected_projects = [selected_projects]
                title = title_input.value or f"{focus_select.value} - {topic_select.value}"
                record = save_analysis(
                    project_root=project_root,
                    title=title,
                    analysis_text=text,
                    projects=list(selected_projects),
                    topic=topic_select.value or "All topics",
                    focus_preset=focus_select.value or "Custom",
                    source_bundle=source_bundle.value or "",
                    source_evidence_pack=source_evidence.value or "",
                    notes=notes.value or "",
                )
                save_status.text = f"Saved: {record.record_id}"
                save_status.update()
                ui.notify("Analysis saved", type="positive")
                open_path(record.analysis_path)

            save_btn.on("click", do_save)
            clear_btn.on("click", do_clear)

        with ui.card().classes("ytis-card p-5 w-full"):
            ui.label("Saved Analysis Library").classes("text-xl font-bold")
            with ui.row().classes("w-full gap-3"):
                filter_project = ui.select(["All projects"] + project_names, value="All projects", label="Project").classes("flex-1")
                filter_topic = ui.select(["All topics"] + [t for t in TOPIC_OPTIONS if t != "All topics"], value="All topics", label="Topic").classes("flex-1")
                filter_focus = ui.select(["All focus presets"] + FOCUS_OPTIONS, value="All focus presets", label="Focus").classes("flex-1")
                search_text = ui.input("Search saved analyses").classes("flex-1")

            results_status = ui.label("").classes("text-xs text-slate-400")
            results_container = ui.column().classes("w-full gap-2")

            def show_preview(record) -> None:
                content = read_analysis(record)
                with ui.dialog() as dialog, ui.card().classes("bg-slate-900 text-white").style("width: 900px; max-width: 95vw;"):
                    ui.label(record.title).classes("text-xl font-bold")
                    preview = ui.textarea(value=content).classes("w-full").props("rows=24 readonly")
                    preview.style("font-family: Consolas, monospace; font-size: 12px;")
                    with ui.row().classes("justify-end w-full"):
                        ui.button("Close", on_click=dialog.close).props("outline")
                        ui.button("Open File", icon="article", on_click=lambda: open_path(record.analysis_path), color="primary")
                dialog.open()

            def render_results() -> None:
                current_records = list_analyses(project_root)
                filtered = filter_analyses(
                    current_records,
                    project=filter_project.value or "All projects",
                    topic=filter_topic.value or "All topics",
                    focus=filter_focus.value or "All focus presets",
                    text=search_text.value or "",
                )
                results_container.clear()
                results_status.text = f"{len(filtered)} saved analyses shown"
                results_status.update()
                with results_container:
                    if not filtered:
                        ui.label("No saved analyses match this filter.").classes("text-slate-400")
                        return
                    for record in filtered:
                        with ui.card().classes("ytis-mini-card p-4 w-full"):
                            with ui.row().classes("w-full justify-between items-start gap-3"):
                                with ui.column().classes("gap-1 flex-1"):
                                    ui.label(record.title).classes("font-bold text-lg")
                                    ui.label(f"{record.created_at} | {record.topic} | {record.focus_preset} | {record.word_count:,} words").classes("text-xs text-slate-400")
                                    ui.label("Projects: " + (", ".join(record.projects) if record.projects else "-")).classes("text-xs text-blue-300")
                                    ui.label(record.summary or "(no summary)").classes("text-sm text-slate-300")
                                with ui.column().classes("gap-1"):
                                    ui.button("Open MD", icon="article", on_click=lambda p=record.analysis_path: open_path(p)).props("outline dense")
                                    ui.button("Open Folder", icon="folder", on_click=lambda p=record.folder: open_path(p)).props("outline dense")
                                    ui.button("Preview", icon="visibility", on_click=lambda r=record: show_preview(r)).props("outline dense")

            for element in [filter_project, filter_topic, filter_focus, search_text]:
                element.on("update:model-value", lambda e: render_results())
            render_results()
