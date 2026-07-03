from __future__ import annotations

from pathlib import Path
from nicegui import ui

from ytis.core.analysis_inbox import (
    CHAIN_STEP_LABELS,
    CHAIN_STEP_OPTIONS,
    FOCUS_OPTIONS,
    TOPIC_OPTIONS,
    analysis_stats,
    coverage_rows,
    export_analyses_zip,
    filter_analyses,
    generate_continue_prompt,
    list_analyses,
    read_analysis,
    save_analysis,
)
from ytis.core.missions import list_missions
from ytis.core.project_hygiene import audit_projects
from ytis.ui.components import open_path
from ytis.ui.context import preferred_project_name
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, val


def _metric(title: str, value: str, caption: str = "") -> None:
    with ui.card().classes("ytis-metric p-4"):
        ui.label(title).classes("text-sm text-slate-400")
        ui.label(value).classes("text-2xl font-bold whitespace-nowrap")
        if caption:
            ui.label(caption).classes("text-xs text-slate-500")


def _project_root(state: AppState) -> Path:
    return Path(getattr(state, "project_root_path", None) or getattr(state, "project_root", "") or Path.cwd())


def _downloads_dir(state: AppState) -> Path:
    value = getattr(state, "downloads_dir", None)
    if value:
        return Path(value)
    return Path.home() / "Downloads"


def _copy_to_clipboard(text: str) -> None:
    safe = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    ui.run_javascript(f"navigator.clipboard.writeText(`{safe}`)")


def render_analysis_inbox(state: AppState) -> None:
    render_shell(state, "/analysis-library")

    project_root = _project_root(state)
    downloads_dir = _downloads_dir(state)
    projects = audit_projects(state.load_projects())
    project_names = [val(p, "name", "Unnamed") for p in projects]
    missions = list_missions(project_root)
    mission_options = {"No mission": ""}
    for mission in missions:
        mission_options[f"{mission.name} ({mission.mission_id[:15]})"] = mission.mission_id

    records = list_analyses(project_root)
    stats = analysis_stats(records)

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("Analysis Library").classes("text-3xl font-bold")
                ui.label("Save, browse, export, and continue ChatGPT results inside YTIS").classes("text-sm text-slate-300")
            with ui.row().classes("gap-2 flex-wrap justify-end"):
                ui.button("Missions", icon="flag", on_click=lambda: ui.navigate.to("/missions")).props("outline")
                ui.button("Intelligence", icon="hub", on_click=lambda: ui.navigate.to("/intelligence")).props("outline")
                ui.button("Open Results Folder", icon="folder_open", on_click=lambda: open_path(project_root / "analysis_results"), color="primary")

        with ui.grid().classes("ytis-grid-5"):
            _metric("Saved analyses", str(stats["records"]), "ChatGPT results")
            _metric("Missions", str(stats["missions"]), "linked")
            _metric("Projects", str(stats["projects"]), "covered")
            _metric("Topics", str(stats["topics"]), "covered")
            _metric("Words", f'{stats["words"]:,}', "saved analysis")

        with ui.expansion("Save New ChatGPT Analysis", icon="save", value=True).classes("ytis-card w-full text-white").props("expand-separator dense"):
            with ui.column().classes("p-4 gap-3"):
                ui.label("After ChatGPT analyzes a mission bundle or prompt-chain step, paste the answer here and link it to the mission/step.").classes("text-sm text-slate-400")

                with ui.grid().classes("ytis-grid-2"):
                    title_input = ui.input("Analysis title", value="").classes("w-full")
                    focus_select = ui.select(FOCUS_OPTIONS, value="Business lessons", label="Focus preset").classes("w-full")
                with ui.grid().classes("ytis-grid-2"):
                    topic_select = ui.select(TOPIC_OPTIONS, value="All topics", label="Topic").classes("w-full")
                    default_project = preferred_project_name(state, project_names)
                    default_projects = [default_project] if default_project in project_names else (project_names[:1] if project_names else [])
                    project_select = ui.select(project_names, value=default_projects, multiple=True, label="Related projects").classes("w-full")
                with ui.grid().classes("ytis-grid-2"):
                    mission_select = ui.select(list(mission_options.keys()), value="No mission", label="Related mission").classes("w-full")
                    chain_step_select = ui.select(CHAIN_STEP_OPTIONS, value="Unassigned", label="Prompt-chain step").classes("w-full")
                with ui.grid().classes("ytis-grid-2"):
                    source_bundle = ui.input("Source bundle filename/path", value="").classes("w-full")
                    source_evidence = ui.input("Source evidence pack filename/path", value="").classes("w-full")

                notes = ui.textarea("Optional notes / why this analysis matters").classes("w-full").props("rows=2")
                analysis_text = ui.textarea("Paste ChatGPT response here").classes("w-full").props("rows=12")
                save_status = ui.label("Ready").classes("text-xs text-slate-400")

                with ui.row().classes("gap-2"):
                    save_btn = ui.button("Save Analysis", icon="save", color="primary")
                    clear_btn = ui.button("Clear Form", icon="backspace").props("outline")

                def selected_mission_name() -> str:
                    label = mission_select.value or "No mission"
                    mission_id = mission_options.get(label, "")
                    for mission in missions:
                        if mission.mission_id == mission_id:
                            return mission.name
                    return ""

                def do_clear() -> None:
                    for element in [title_input, source_bundle, source_evidence, notes, analysis_text]:
                        element.value = ""
                        element.update()
                    mission_select.value = "No mission"
                    chain_step_select.value = "Unassigned"
                    mission_select.update()
                    chain_step_select.update()
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
                    mission_label = mission_select.value or "No mission"
                    mission_id = mission_options.get(mission_label, "")
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
                        mission_id=mission_id,
                        mission_name=selected_mission_name(),
                        chain_step=chain_step_select.value or "Unassigned",
                    )
                    save_status.text = f"Saved: {record.record_id}"
                    save_status.update()
                    ui.notify("Analysis saved and linked", type="positive")
                    open_path(record.analysis_path)

                save_btn.on("click", do_save)
                clear_btn.on("click", do_clear)

        with ui.expansion("Analysis Coverage", icon="checklist", value=False).classes("ytis-card w-full text-white").props("expand-separator dense"):
            with ui.column().classes("p-4 gap-3"):
                ui.label("Shows which project/topic combinations already have saved ChatGPT analysis. Counts are based on saved metadata.").classes("text-sm text-slate-400")
                rows = coverage_rows(records, project_names)
                if rows:
                    columns = [{"name": k, "label": k, "field": k} for k in rows[0].keys()]
                    display_rows = []
                    for row in rows:
                        item = dict(row)
                        for key, value in list(item.items()):
                            if key != "Project":
                                item[key] = "Done" if int(value or 0) > 0 else "Pending"
                        item["Total"] = row.get("Total", 0)
                        display_rows.append(item)
                    ui.table(columns=columns, rows=display_rows, row_key="Project").classes("w-full")
                else:
                    ui.label("No projects available for coverage view.").classes("text-slate-400")

        with ui.card().classes("ytis-card p-5 w-full"):
            ui.label("Saved Analysis Library").classes("text-xl font-bold")
            with ui.row().classes("w-full gap-3 ytis-card-row"):
                default_filter_project = preferred_project_name(state, project_names)
                filter_project = ui.select(["All projects"] + project_names, value=default_filter_project if default_filter_project in project_names else "All projects", label="Project").classes("flex-1 min-w-[180px]")
                filter_topic = ui.select(["All topics"] + [t for t in TOPIC_OPTIONS if t != "All topics"], value="All topics", label="Topic").classes("flex-1 min-w-[180px]")
                filter_focus = ui.select(["All focus presets"] + FOCUS_OPTIONS, value="All focus presets", label="Focus").classes("flex-1 min-w-[180px]")
                filter_mission = ui.select(["All missions"] + list(mission_options.keys())[1:], value="All missions", label="Mission").classes("flex-1 min-w-[180px]")
                filter_step = ui.select(["All steps"] + CHAIN_STEP_OPTIONS, value="All steps", label="Step").classes("flex-1 min-w-[180px]")
            search_text = ui.input("Search saved analyses").classes("w-full")

            with ui.row().classes("gap-2"):
                export_filtered_btn = ui.button("Export Filtered Analyses ZIP", icon="archive", color="primary")
                refresh_btn = ui.button("Refresh Library", icon="refresh").props("outline")

            results_status = ui.label("").classes("text-xs text-slate-400")
            results_container = ui.column().classes("w-full gap-2")

            def current_filtered_records():
                current_records = list_analyses(project_root)
                mission_value = "All missions"
                if filter_mission.value and filter_mission.value != "All missions":
                    mission_value = mission_options.get(filter_mission.value, "")
                return filter_analyses(
                    current_records,
                    project=filter_project.value or "All projects",
                    topic=filter_topic.value or "All topics",
                    focus=filter_focus.value or "All focus presets",
                    text=search_text.value or "",
                    mission_id=mission_value,
                    chain_step=filter_step.value or "All steps",
                )

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

            def show_continue_prompt(record) -> None:
                prompt = generate_continue_prompt(record)
                with ui.dialog() as dialog, ui.card().classes("bg-slate-900 text-white").style("width: 900px; max-width: 95vw;"):
                    ui.label("Continue Analysis Prompt").classes("text-xl font-bold")
                    ui.label(record.title).classes("text-sm text-slate-400")
                    prompt_box = ui.textarea(value=prompt).classes("w-full").props("rows=24")
                    prompt_box.style("font-family: Consolas, monospace; font-size: 12px;")
                    with ui.row().classes("justify-end w-full"):
                        ui.button("Close", on_click=dialog.close).props("outline")
                        ui.button("Copy Prompt", icon="content_copy", on_click=lambda: (_copy_to_clipboard(prompt_box.value or ""), ui.notify("Prompt copied", type="positive")), color="primary")
                dialog.open()

            def render_results() -> None:
                filtered = current_filtered_records()
                results_container.clear()
                results_status.text = f"{len(filtered)} saved analyses shown"
                results_status.update()
                with results_container:
                    if not filtered:
                        ui.label("No saved analyses match this filter.").classes("text-slate-400")
                        return
                    for record in filtered:
                        with ui.card().classes("ytis-mini-card p-4 w-full"):
                            with ui.row().classes("w-full justify-between items-start gap-3 ytis-card-row"):
                                with ui.column().classes("gap-1 flex-1 min-w-0"):
                                    ui.label(record.title).classes("font-bold text-lg")
                                    step_label = CHAIN_STEP_LABELS.get(record.chain_step, record.chain_step)
                                    ui.label(f"{record.created_at} | {record.topic} | {record.focus_preset} | {record.word_count:,} words").classes("text-xs text-slate-400")
                                    if record.mission_name:
                                        ui.label(f"Mission: {record.mission_name} | {step_label}").classes("text-xs text-green-300")
                                    ui.label("Projects: " + (", ".join(record.projects) if record.projects else "-")).classes("text-xs text-blue-300")
                                    ui.label(record.summary or "(no summary)").classes("text-sm text-slate-300")
                                with ui.column().classes("gap-1"):
                                    ui.button("Continue Prompt", icon="play_arrow", on_click=lambda r=record: show_continue_prompt(r)).props("outline dense")
                                    ui.button("Preview", icon="visibility", on_click=lambda r=record: show_preview(r)).props("outline dense")
                                    ui.button("Open MD", icon="article", on_click=lambda p=record.analysis_path: open_path(p)).props("outline dense")
                                    ui.button("Open Folder", icon="folder", on_click=lambda p=record.folder: open_path(p)).props("outline dense")

            def do_export_filtered() -> None:
                filtered = current_filtered_records()
                if not filtered:
                    ui.notify("No analyses to export with current filters", type="warning")
                    return
                path = export_analyses_zip(filtered, downloads_dir)
                ui.notify(f"Exported {len(filtered)} analyses", type="positive")
                open_path(path)

            for element in [filter_project, filter_topic, filter_focus, filter_mission, filter_step, search_text]:
                element.on("update:model-value", lambda e: render_results())
            refresh_btn.on("click", lambda: render_results())
            export_filtered_btn.on("click", do_export_filtered)

            render_results()
