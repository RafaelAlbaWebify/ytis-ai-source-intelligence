from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from nicegui import ui

from ytis.core.analysis_inbox import (
    CHAIN_STEP_LABELS,
    CHAIN_STEP_OPTIONS,
    list_analyses,
    mission_analysis_records,
    mission_chain_progress,
)
from ytis.core.missions import (
    MISSION_FOCUS_OPTIONS,
    MISSION_TEMPLATES,
    MISSION_TOPIC_OPTIONS,
    create_mission,
    create_mission_bundle,
    create_prompt_chain_pack,
    generate_prompt_chain,
    list_missions,
    mission_stats,
    read_mission_prompt,
    save_mission,
    selected_project_records,
    update_mission_status,
)
from ytis.core.project_hygiene import audit_projects
from ytis.ui.components import open_path
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, val


def _project_root(state: AppState) -> Path:
    return Path(getattr(state, "project_root", "") or Path.cwd())


def _downloads_dir(state: AppState) -> Path:
    value = getattr(state, "downloads_dir", None)
    if value:
        return Path(value)
    return Path.home() / "Downloads"


def _metric(title: str, value: str, caption: str = ""):
    value_label = None
    with ui.card().classes("ytis-metric p-4"):
        ui.label(title).classes("text-sm text-slate-400")
        value_label = ui.label(value).classes("text-2xl font-bold whitespace-nowrap")
        if caption:
            ui.label(caption).classes("text-xs text-slate-500")
    return value_label


def _copy_to_clipboard(text: str) -> None:
    safe = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    ui.run_javascript(f"navigator.clipboard.writeText(`{safe}`)")


def _next_pending_step(progress: dict[str, int]) -> str:
    for step in CHAIN_STEP_OPTIONS:
        if step == "Unassigned":
            continue
        if progress.get(step, 0) <= 0:
            return step
    return ""


def _prompt_for_step(mission, projects: list[dict], step_key: str) -> str:
    prompts = generate_prompt_chain(mission, selected_project_records(mission, projects))
    # Keys from Analysis Inbox: STEP_01_extract_map, STEP_02_compare_patterns, etc.
    index_map = {
        "STEP_01_extract_map": 0,
        "STEP_02_compare_patterns": 1,
        "STEP_03_extract_workflows": 2,
        "STEP_04_apply_to_rafael_webify": 3,
        "STEP_05_validation_plan": 4,
    }
    idx = index_map.get(step_key, 0)
    if prompts and idx < len(prompts):
        return prompts[idx][1]
    return prompts[0][1] if prompts else ""


def _duplicate_names(missions) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for mission in missions:
        key = mission.name.strip().lower()
        if key in seen:
            duplicates.add(mission.name)
        seen.add(key)
    return sorted(duplicates)


def _name_exists(missions, name: str) -> bool:
    key = name.strip().lower()
    return any(m.name.strip().lower() == key for m in missions)


def _safe_delete_mission(project_root: Path, mission) -> Path:
    deleted_root = project_root / "missions_deleted"
    deleted_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = deleted_root / f"{stamp}__{mission.folder.name}"
    shutil.move(str(mission.folder), str(destination))
    return destination


def render_missions(state: AppState) -> None:
    render_shell(state, "/missions")

    project_root = _project_root(state)
    downloads_dir = _downloads_dir(state)
    projects = audit_projects(state.load_projects())
    project_names = [val(p, "name", "Unnamed") for p in projects]
    initial_missions = list_missions(project_root)
    initial_stats = mission_stats(initial_missions)

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("Study Missions").classes("text-3xl font-bold")
                ui.label("Run the next pending step, manage missions, and track linked ChatGPT analyses").classes("text-sm text-slate-300")
            with ui.row().classes("gap-2"):
                ui.button("Intelligence", icon="hub", on_click=lambda: ui.navigate.to("/intelligence")).props("outline")
                ui.button("Analysis Inbox", icon="move_to_inbox", on_click=lambda: ui.navigate.to("/analysis-inbox")).props("outline")
                ui.button("Open Missions Folder", icon="folder_open", on_click=lambda: open_path(project_root / "missions"), color="primary")

        with ui.grid(columns=5).classes("w-full gap-3"):
            missions_metric = _metric("Missions", str(initial_stats.get("missions", 0)), "total")
            active_metric = _metric("Active", str(initial_stats.get("active", 0)), "in progress")
            paused_metric = _metric("Paused", str(initial_stats.get("paused", 0)), "waiting")
            completed_metric = _metric("Completed", str(initial_stats.get("completed", 0)), "finished")
            archived_metric = _metric("Archived", str(initial_stats.get("archived", 0)), "hidden optional")

        def refresh_metrics() -> None:
            current = mission_stats(list_missions(project_root))
            missions_metric.text = str(current.get("missions", 0))
            active_metric.text = str(current.get("active", 0))
            paused_metric.text = str(current.get("paused", 0))
            completed_metric.text = str(current.get("completed", 0))
            archived_metric.text = str(current.get("archived", 0))
            for metric in [missions_metric, active_metric, paused_metric, completed_metric, archived_metric]:
                metric.update()

        render_missions_list_ref = {"fn": None}

        with ui.expansion("Create New Mission", icon="add_task", value=False).classes("ytis-card w-full text-white").props("expand-separator dense"):
            with ui.column().classes("p-4 gap-3"):
                with ui.grid(columns=2).classes("w-full gap-3"):
                    name_input = ui.input("Mission name", value="Webify service ideas").classes("w-full")
                    focus_select = ui.select(MISSION_FOCUS_OPTIONS, value="Webify service ideas", label="Focus preset").classes("w-full")
                goal_input = ui.textarea("Mission goal", value=MISSION_TEMPLATES["Webify service ideas"]).classes("w-full").props("rows=4")
                with ui.grid(columns=2).classes("w-full gap-3"):
                    project_select = ui.select(project_names, value=project_names, multiple=True, label="Source projects").classes("w-full")
                    topic_select = ui.select(MISSION_TOPIC_OPTIONS, value=["Offer", "Pricing", "Lead generation", "Workflow"], multiple=True, label="Topics").classes("w-full")
                status_label = ui.label("Ready").classes("text-xs text-slate-400")

                with ui.row().classes("gap-2"):
                    create_btn = ui.button("Create Mission", icon="flag", color="primary")
                    reset_btn = ui.button("Reset from Preset", icon="restart_alt").props("outline")

                def apply_preset() -> None:
                    preset = focus_select.value or "Custom"
                    if not name_input.value or name_input.value in MISSION_TEMPLATES:
                        name_input.value = preset
                    goal_input.value = MISSION_TEMPLATES.get(preset, goal_input.value or "")
                    name_input.update()
                    goal_input.update()

                def do_create() -> None:
                    selected_projects = project_select.value or []
                    selected_topics = topic_select.value or []
                    if isinstance(selected_projects, str):
                        selected_projects = [selected_projects]
                    if isinstance(selected_topics, str):
                        selected_topics = [selected_topics]

                    if _name_exists(list_missions(project_root), name_input.value or ""):
                        ui.notify("Mission name already exists. Creating anyway, but archive or rename duplicates.", type="warning")

                    mission = create_mission(
                        project_root=project_root,
                        name=name_input.value or "Untitled mission",
                        goal=goal_input.value or "",
                        focus_preset=focus_select.value or "Custom",
                        projects=list(selected_projects),
                        topics=list(selected_topics),
                    )
                    status_label.text = f"Created: {mission.mission_id}"
                    status_label.classes(remove="text-slate-400")
                    status_label.classes(add="text-green-400")
                    status_label.update()
                    refresh_metrics()
                    if render_missions_list_ref["fn"]:
                        render_missions_list_ref["fn"]()
                    ui.notify("Mission created and library refreshed", type="positive")

                focus_select.on("update:model-value", lambda e: apply_preset())
                reset_btn.on("click", apply_preset)
                create_btn.on("click", do_create)

        with ui.card().classes("ytis-card p-5 w-full"):
            with ui.row().classes("w-full justify-between items-center"):
                with ui.column().classes("gap-0"):
                    ui.label("Mission Library").classes("text-xl font-bold")
                    ui.label("Normal workflow: Copy Next Step, paste in ChatGPT, save answer in Analysis Inbox.").classes("text-sm text-slate-400")
                hide_archived = ui.checkbox("Hide archived", value=True).classes("text-sm")
            duplicate_warning = ui.label("").classes("text-xs text-orange-300")
            missions_container = ui.column().classes("w-full gap-2")

            def refresh_duplicate_warning() -> None:
                duplicates = _duplicate_names(list_missions(project_root))
                duplicate_warning.text = "Duplicate mission names detected: " + ", ".join(duplicates) if duplicates else ""
                duplicate_warning.update()

            def show_prompt(mission) -> None:
                prompt = read_mission_prompt(mission)
                with ui.dialog() as dialog, ui.card().classes("bg-slate-900 text-white").style("width: 900px; max-width: 95vw;"):
                    ui.label("Mission Prompt").classes("text-xl font-bold")
                    ui.label(mission.name).classes("text-sm text-slate-400")
                    prompt_box = ui.textarea(value=prompt).classes("w-full").props("rows=24")
                    prompt_box.style("font-family: Consolas, monospace; font-size: 12px;")
                    with ui.row().classes("justify-end w-full"):
                        ui.button("Close", on_click=dialog.close).props("outline")
                        ui.button("Copy Prompt", icon="content_copy", on_click=lambda: (_copy_to_clipboard(prompt_box.value or ""), ui.notify("Prompt copied", type="positive")), color="primary")
                dialog.open()

            def show_chain(mission) -> None:
                selected = selected_project_records(mission, projects)
                prompts = generate_prompt_chain(mission, selected)
                step_options = [f"Step {index}: {name}" for index, (name, _) in enumerate(prompts, start=1)]
                prompt_map = {label: prompt for label, (_, prompt) in zip(step_options, prompts)}
                combined = "\n\n---\n\n".join(prompt for _, prompt in prompts)

                with ui.dialog() as dialog, ui.card().classes("bg-slate-900 text-white").style("width: 950px; max-width: 95vw;"):
                    ui.label("Mission Prompt Chain").classes("text-xl font-bold")
                    ui.label(f"{mission.name} | {len(prompts)} steps").classes("text-sm text-slate-400")
                    step_select = ui.select(step_options, value=step_options[0] if step_options else None, label="Select prompt-chain step").classes("w-full")
                    prompt_box = ui.textarea(value=prompt_map.get(step_select.value, "")).classes("w-full").props("rows=24")
                    prompt_box.style("font-family: Consolas, monospace; font-size: 12px;")

                    def update_selected_step() -> None:
                        prompt_box.value = prompt_map.get(step_select.value, "")
                        prompt_box.update()

                    step_select.on("update:model-value", lambda e: update_selected_step())

                    with ui.row().classes("justify-end w-full"):
                        ui.button("Close", on_click=dialog.close).props("outline")
                        ui.button("Copy Selected Step", icon="content_copy", on_click=lambda: (_copy_to_clipboard(prompt_box.value or ""), ui.notify("Selected step copied", type="positive")), color="primary")
                        ui.button("Copy All Steps", icon="select_all", on_click=lambda: (_copy_to_clipboard(combined), ui.notify("All steps copied", type="positive"))).props("outline")
                dialog.open()

            def show_next_step(mission, step: str) -> None:
                prompt = _prompt_for_step(mission, projects, step)
                label = CHAIN_STEP_LABELS.get(step, step)
                with ui.dialog() as dialog, ui.card().classes("bg-slate-900 text-white").style("width: 950px; max-width: 95vw;"):
                    ui.label("Next Pending Mission Step").classes("text-xl font-bold")
                    ui.label(f"{mission.name} | {label}").classes("text-sm text-slate-400")
                    prompt_box = ui.textarea(value=prompt).classes("w-full").props("rows=24")
                    prompt_box.style("font-family: Consolas, monospace; font-size: 12px;")
                    with ui.row().classes("justify-end w-full"):
                        ui.button("Close", on_click=dialog.close).props("outline")
                        ui.button("Copy Next Step", icon="content_copy", on_click=lambda: (_copy_to_clipboard(prompt_box.value or ""), ui.notify("Next step copied", type="positive")), color="primary")
                        ui.button("Go to Analysis Inbox", icon="move_to_inbox", on_click=lambda: ui.navigate.to("/analysis-inbox")).props("outline")
                dialog.open()

            def show_linked_analyses(mission) -> None:
                records = mission_analysis_records(list_analyses(project_root), mission.mission_id)
                with ui.dialog() as dialog, ui.card().classes("bg-slate-900 text-white").style("width: 950px; max-width: 95vw;"):
                    ui.label("Linked Mission Analyses").classes("text-xl font-bold")
                    ui.label(mission.name).classes("text-sm text-slate-400")
                    if not records:
                        ui.label("No analyses linked to this mission yet. Save one from Analysis Inbox.").classes("text-slate-400")
                    else:
                        for record in records:
                            with ui.card().classes("ytis-mini-card p-3 w-full"):
                                ui.label(record.title).classes("font-bold")
                                ui.label(f"{record.created_at} | {CHAIN_STEP_LABELS.get(record.chain_step, record.chain_step)} | {record.word_count:,} words").classes("text-xs text-slate-400")
                                ui.label(record.summary).classes("text-sm text-slate-300")
                                with ui.row().classes("gap-2"):
                                    ui.button("Open MD", icon="article", on_click=lambda p=record.analysis_path: open_path(p)).props("outline dense")
                                    ui.button("Open Folder", icon="folder", on_click=lambda p=record.folder: open_path(p)).props("outline dense")
                    with ui.row().classes("justify-end w-full"):
                        ui.button("Close", on_click=dialog.close).props("outline")
                        ui.button("Analysis Inbox", icon="move_to_inbox", on_click=lambda: ui.navigate.to("/analysis-inbox"), color="primary")
                dialog.open()

            def show_edit_mission(mission) -> None:
                with ui.dialog() as dialog, ui.card().classes("bg-slate-900 text-white").style("width: 900px; max-width: 95vw;"):
                    ui.label("Edit Mission").classes("text-xl font-bold")
                    name_edit = ui.input("Mission name", value=mission.name).classes("w-full")
                    focus_edit = ui.select(MISSION_FOCUS_OPTIONS, value=mission.focus_preset, label="Focus preset").classes("w-full")
                    goal_edit = ui.textarea("Mission goal", value=mission.goal).classes("w-full").props("rows=4")
                    project_edit = ui.select(project_names, value=mission.projects, multiple=True, label="Source projects").classes("w-full")
                    topic_edit = ui.select(MISSION_TOPIC_OPTIONS, value=mission.topics, multiple=True, label="Topics").classes("w-full")

                    def do_save_edit() -> None:
                        selected_projects = project_edit.value or []
                        selected_topics = topic_edit.value or []
                        if isinstance(selected_projects, str):
                            selected_projects = [selected_projects]
                        if isinstance(selected_topics, str):
                            selected_topics = [selected_topics]
                        mission.name = name_edit.value or mission.name
                        mission.goal = goal_edit.value or ""
                        mission.focus_preset = focus_edit.value or mission.focus_preset
                        mission.projects = list(selected_projects)
                        mission.topics = list(selected_topics)
                        save_mission(mission)
                        ui.notify("Mission updated", type="positive")
                        dialog.close()
                        refresh_metrics()
                        refresh_duplicate_warning()
                        render_missions_list()

                    with ui.row().classes("justify-end w-full"):
                        ui.button("Cancel", on_click=dialog.close).props("outline")
                        ui.button("Save Changes", icon="save", on_click=do_save_edit, color="primary")
                dialog.open()

            def confirm_delete(mission) -> None:
                with ui.dialog() as dialog, ui.card().classes("bg-slate-900 text-white").style("width: 640px; max-width: 95vw;"):
                    ui.label("Safe Delete Mission").classes("text-xl font-bold text-red-300")
                    ui.label(f"This moves the mission folder to missions_deleted, not permanent delete: {mission.name}").classes("text-sm text-slate-300")
                    confirm_text = ui.input("Type DELETE to confirm").classes("w-full")

                    def do_delete() -> None:
                        if (confirm_text.value or "").strip() != "DELETE":
                            ui.notify("Type DELETE to confirm", type="warning")
                            return
                        destination = _safe_delete_mission(project_root, mission)
                        ui.notify("Mission moved to missions_deleted", type="positive")
                        dialog.close()
                        refresh_metrics()
                        refresh_duplicate_warning()
                        render_missions_list()
                        open_path(destination)

                    with ui.row().classes("justify-end w-full"):
                        ui.button("Cancel", on_click=dialog.close).props("outline")
                        ui.button("Move to Deleted", icon="delete", on_click=do_delete, color="negative")
                dialog.open()

            def do_bundle(mission) -> None:
                result = create_mission_bundle(mission, projects, downloads_dir)
                ui.notify(f"Mission bundle created with {len(result.included_zips)} packs", type="positive")
                open_path(result.bundle_path)

            def do_chain_pack(mission) -> None:
                result = create_prompt_chain_pack(mission, projects, downloads_dir)
                ui.notify(f"Prompt chain ZIP created with {len(result.step_paths)} steps", type="positive")
                open_path(result.chain_zip)

            def do_status(mission, status: str) -> None:
                update_mission_status(mission, status)
                ui.notify(f"Mission status updated: {status}", type="positive")
                refresh_metrics()
                refresh_duplicate_warning()
                render_missions_list()

            def render_progress(progress: dict[str, int]) -> None:
                with ui.row().classes("gap-2 flex-wrap"):
                    for step in CHAIN_STEP_OPTIONS:
                        if step == "Unassigned":
                            continue
                        done = progress.get(step, 0) > 0
                        label = CHAIN_STEP_LABELS.get(step, step)
                        ui.badge(("Done: " if done else "Pending: ") + label).props("color=green" if done else "color=grey")
                    if progress.get("Unassigned", 0):
                        ui.badge(f"Unassigned: {progress['Unassigned']}").props("color=orange")

            def render_missions_list() -> None:
                missions_container.clear()
                current_missions = list_missions(project_root)
                all_records = list_analyses(project_root)
                if hide_archived.value:
                    current_missions = [m for m in current_missions if m.status != "archived"]
                with missions_container:
                    if not current_missions:
                        ui.label("No missions match the current filter.").classes("text-slate-400")
                        return
                    for mission in current_missions:
                        selected_projects = selected_project_records(mission, projects)
                        progress = mission_chain_progress(all_records, mission.mission_id)
                        next_step = _next_pending_step(progress)
                        next_label = CHAIN_STEP_LABELS.get(next_step, "All steps complete") if next_step else "All steps complete"
                        with ui.card().classes("ytis-mini-card p-4 w-full"):
                            with ui.row().classes("w-full justify-between items-start gap-3"):
                                with ui.column().classes("gap-2 flex-1"):
                                    ui.label(mission.name).classes("font-bold text-lg")
                                    ui.label(f"{mission.status.upper()} | {mission.focus_preset} | {mission.created_at}").classes("text-xs text-slate-400")
                                    ui.label("Projects: " + (", ".join(mission.projects) if mission.projects else "-")).classes("text-xs text-blue-300")
                                    ui.label("Topics: " + (", ".join(mission.topics) if mission.topics else "-")).classes("text-xs text-green-300")
                                    ui.label(mission.goal or "(no goal)").classes("text-sm text-slate-300")
                                    ui.label(f"Linked analyses: {progress.get('Total', 0)} | Selected project records available: {len(selected_projects)}").classes("text-xs text-slate-500")
                                    ui.label("Next: " + next_label).classes("text-sm font-bold text-cyan-300")
                                    render_progress(progress)
                                with ui.column().classes("gap-2"):
                                    if next_step:
                                        ui.button("Copy Next Step", icon="content_copy", on_click=lambda m=mission, s=next_step: (_copy_to_clipboard(_prompt_for_step(m, projects, s)), ui.notify("Next pending step copied", type="positive")), color="primary").props("dense")
                                        ui.button("View Next Step", icon="visibility", on_click=lambda m=mission, s=next_step: show_next_step(m, s)).props("outline dense")
                                    else:
                                        ui.button("Mission Complete", icon="check_circle").props("outline dense disable")
                                    ui.button("Linked Analyses", icon="link", on_click=lambda m=mission: show_linked_analyses(m)).props("outline dense")
                                    with ui.expansion("Manage", icon="settings", value=False).classes("w-full text-white").props("dense"):
                                        with ui.column().classes("gap-1 p-2"):
                                            ui.button("Create Bundle", icon="archive", on_click=lambda m=mission: do_bundle(m)).props("outline dense")
                                            ui.button("Create Chain ZIP", icon="account_tree", on_click=lambda m=mission: do_chain_pack(m)).props("outline dense")
                                            ui.button("View Chain", icon="schema", on_click=lambda m=mission: show_chain(m)).props("outline dense")
                                            ui.button("One-Pass Prompt", icon="article", on_click=lambda m=mission: show_prompt(m)).props("outline dense")
                                            ui.button("Edit Mission", icon="edit", on_click=lambda m=mission: show_edit_mission(m)).props("outline dense")
                                            ui.button("Open Folder", icon="folder", on_click=lambda p=mission.folder: open_path(p)).props("outline dense")
                                            ui.button("Mark Completed", icon="check_circle", on_click=lambda m=mission: do_status(m, "completed")).props("outline dense")
                                            ui.button("Pause", icon="pause_circle", on_click=lambda m=mission: do_status(m, "paused")).props("outline dense")
                                            ui.button("Reactivate", icon="play_circle", on_click=lambda m=mission: do_status(m, "active")).props("outline dense")
                                            ui.button("Archive", icon="archive", on_click=lambda m=mission: do_status(m, "archived")).props("outline dense")
                                            ui.button("Safe Delete", icon="delete", on_click=lambda m=mission: confirm_delete(m)).props("outline dense color=negative")

            hide_archived.on("update:model-value", lambda e: render_missions_list())
            render_missions_list_ref["fn"] = render_missions_list
            refresh_duplicate_warning()
            render_missions_list()
