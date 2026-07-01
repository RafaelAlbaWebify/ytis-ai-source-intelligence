from __future__ import annotations

from pathlib import Path
from nicegui import ui

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
                ui.label("Goal-based research with bundles, prompt chains, and saved ChatGPT analysis").classes("text-sm text-slate-300")
            with ui.row().classes("gap-2"):
                ui.button("Intelligence", icon="hub", on_click=lambda: ui.navigate.to("/intelligence")).props("outline")
                ui.button("Analysis Inbox", icon="move_to_inbox", on_click=lambda: ui.navigate.to("/analysis-inbox")).props("outline")
                ui.button("Open Missions Folder", icon="folder_open", on_click=lambda: open_path(project_root / "missions"), color="primary")

        with ui.grid(columns=4).classes("w-full gap-3"):
            missions_metric = _metric("Missions", str(initial_stats["missions"]), "total")
            active_metric = _metric("Active", str(initial_stats["active"]), "in progress")
            paused_metric = _metric("Paused", str(initial_stats["paused"]), "waiting")
            completed_metric = _metric("Completed", str(initial_stats["completed"]), "finished")

        def refresh_metrics() -> None:
            current = mission_stats(list_missions(project_root))
            missions_metric.text = str(current["missions"])
            active_metric.text = str(current["active"])
            paused_metric.text = str(current["paused"])
            completed_metric.text = str(current["completed"])
            for metric in [missions_metric, active_metric, paused_metric, completed_metric]:
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
            ui.label("Mission Library").classes("text-xl font-bold")
            ui.label("Create mission bundles, staged prompt chains, and track mission status.").classes("text-sm text-slate-400")
            missions_container = ui.column().classes("w-full gap-2")

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
                combined = "\n\n---\n\n".join(prompt for _, prompt in prompts)
                with ui.dialog() as dialog, ui.card().classes("bg-slate-900 text-white").style("width: 950px; max-width: 95vw;"):
                    ui.label("Mission Prompt Chain").classes("text-xl font-bold")
                    ui.label(f"{mission.name} | {len(prompts)} steps").classes("text-sm text-slate-400")
                    prompt_box = ui.textarea(value=combined).classes("w-full").props("rows=26")
                    prompt_box.style("font-family: Consolas, monospace; font-size: 12px;")
                    with ui.row().classes("justify-end w-full"):
                        ui.button("Close", on_click=dialog.close).props("outline")
                        ui.button("Copy All Steps", icon="content_copy", on_click=lambda: (_copy_to_clipboard(prompt_box.value or ""), ui.notify("Prompt chain copied", type="positive")), color="primary")
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
                render_missions_list()

            def render_missions_list() -> None:
                missions_container.clear()
                current_missions = list_missions(project_root)
                with missions_container:
                    if not current_missions:
                        ui.label("No missions yet. Create one above.").classes("text-slate-400")
                        return
                    for mission in current_missions:
                        selected_projects = selected_project_records(mission, projects)
                        with ui.card().classes("ytis-mini-card p-4 w-full"):
                            with ui.row().classes("w-full justify-between items-start gap-3"):
                                with ui.column().classes("gap-1 flex-1"):
                                    ui.label(mission.name).classes("font-bold text-lg")
                                    ui.label(f"{mission.status.upper()} | {mission.focus_preset} | {mission.created_at}").classes("text-xs text-slate-400")
                                    ui.label("Projects: " + (", ".join(mission.projects) if mission.projects else "-")).classes("text-xs text-blue-300")
                                    ui.label("Topics: " + (", ".join(mission.topics) if mission.topics else "-")).classes("text-xs text-green-300")
                                    ui.label(mission.goal or "(no goal)").classes("text-sm text-slate-300")
                                    ui.label(f"Selected project records available: {len(selected_projects)}").classes("text-xs text-slate-500")
                                with ui.column().classes("gap-1"):
                                    ui.button("Create Bundle", icon="archive", on_click=lambda m=mission: do_bundle(m)).props("outline dense")
                                    ui.button("Create Chain ZIP", icon="account_tree", on_click=lambda m=mission: do_chain_pack(m)).props("outline dense")
                                    ui.button("View Chain", icon="schema", on_click=lambda m=mission: show_chain(m)).props("outline dense")
                                    ui.button("One-Pass Prompt", icon="article", on_click=lambda m=mission: show_prompt(m)).props("outline dense")
                                    ui.button("Open Folder", icon="folder", on_click=lambda p=mission.folder: open_path(p)).props("outline dense")
                                    ui.button("Mark Completed", icon="check_circle", on_click=lambda m=mission: do_status(m, "completed")).props("outline dense")
                                    ui.button("Pause", icon="pause_circle", on_click=lambda m=mission: do_status(m, "paused")).props("outline dense")
                                    ui.button("Reactivate", icon="play_circle", on_click=lambda m=mission: do_status(m, "active")).props("outline dense")

            render_missions_list_ref["fn"] = render_missions_list
            render_missions_list()
