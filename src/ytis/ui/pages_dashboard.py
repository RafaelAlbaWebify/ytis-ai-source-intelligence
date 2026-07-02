from __future__ import annotations

from pathlib import Path
from nicegui import ui

from ytis.core.analysis_inbox import (
    CHAIN_STEP_LABELS,
    list_analyses,
    mission_analysis_records,
    mission_chain_progress,
    save_analysis,
)
from ytis.core.missions import (
    duplicate_mission_names,
    list_missions,
    mission_stats,
    prompt_for_analysis_step,
    selected_project_records,
)
from ytis.core.project_hygiene import audit_projects
from ytis.ui.components import open_path
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, val


STEP_TO_TOPIC = {
    "STEP_01_extract_map": "All topics",
    "STEP_02_compare_patterns": "Offer",
    "STEP_03_extract_workflows": "Workflow",
    "STEP_04_apply_to_rafael_webify": "Webify service ideas",
    "STEP_05_validation_plan": "Webify service ideas",
}

CHAIN_ORDER = [
    "STEP_01_extract_map",
    "STEP_02_compare_patterns",
    "STEP_03_extract_workflows",
    "STEP_04_apply_to_rafael_webify",
    "STEP_05_validation_plan",
]


def _project_root(state: AppState) -> Path:
    return Path(getattr(state, "project_root", "") or Path.cwd())


def _downloads_dir(state: AppState) -> Path:
    value = getattr(state, "downloads_dir", None)
    if value:
        return Path(value)
    return Path.home() / "Downloads"


def _copy_to_clipboard(text: str) -> None:
    safe = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    ui.run_javascript(f"navigator.clipboard.writeText(`{safe}`)")


def _metric(title: str, value: str, caption: str = "") -> None:
    with ui.card().classes("ytis-metric p-4"):
        ui.label(title).classes("text-sm text-slate-400")
        ui.label(value).classes("text-2xl font-bold whitespace-nowrap")
        if caption:
            ui.label(caption).classes("text-xs text-slate-500")


def _next_pending_step(progress: dict[str, int]) -> str:
    for step in CHAIN_ORDER:
        if progress.get(step, 0) <= 0:
            return step
    return ""


def _safe_int(value) -> int:
    try:
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return 0


def _compact(value) -> str:
    n = _safe_int(value)
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if abs(n) >= 1_000:
        return f"{n / 1_000:.1f}k".replace(".0k", "k")
    return f"{n:,}"


def _select_active_mission(project_root: Path):
    missions = list_missions(project_root)
    active = [m for m in missions if m.status == "active"]
    if active:
        return active[0]
    non_archived = [m for m in missions if m.status != "archived"]
    if non_archived:
        return non_archived[0]
    return missions[0] if missions else None


def _progress_badges(progress: dict[str, int]) -> None:
    with ui.row().classes("gap-2 flex-wrap"):
        for step in CHAIN_ORDER:
            done = progress.get(step, 0) > 0
            label = CHAIN_STEP_LABELS.get(step, step)
            ui.badge(("Done: " if done else "Pending: ") + label).props("color=green" if done else "color=grey")
        if progress.get("Unassigned", 0):
            ui.badge(f"Unassigned: {progress['Unassigned']}").props("color=orange")


def render_dashboard(state: AppState) -> None:
    render_shell(state, "/")

    project_root = _project_root(state)
    downloads_dir = _downloads_dir(state)
    projects = audit_projects(state.load_projects())
    records = list_analyses(project_root)
    missions = list_missions(project_root)
    mission_stats_data = mission_stats(missions)
    active_mission = _select_active_mission(project_root)

    total_projects = len(projects)
    total_words = sum(_safe_int(p.get("total_words")) for p in projects)
    zip_ready = sum(1 for p in projects if p.get("zip_path") and Path(str(p.get("zip_path"))).exists())

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("YTIS Workflow Dashboard").classes("text-3xl font-bold")
                ui.label("Mission-centered YouTube to ChatGPT research cockpit").classes("text-sm text-slate-300")
            with ui.row().classes("gap-2"):
                ui.button("Missions", icon="flag", on_click=lambda: ui.navigate.to("/missions")).props("outline")
                ui.button("Build Pack", icon="construction", on_click=lambda: ui.navigate.to("/build")).props("outline")
                ui.button("Search", icon="search", on_click=lambda: ui.navigate.to("/search"), color="primary")

        with ui.grid(columns=5).classes("w-full gap-3"):
            _metric("Active missions", str(mission_stats_data.get("active", 0)), "research goals")
            _metric("Saved analyses", str(len(records)), "ChatGPT answers")
            _metric("Projects", str(total_projects), "source packs")
            _metric("Words", _compact(total_words), "source corpus")
            _metric("ZIP-ready", str(zip_ready), "upload packs")

        if not active_mission:
            with ui.card().classes("ytis-card p-6 w-full"):
                ui.label("No mission yet").classes("text-2xl font-bold")
                ui.label("Create a mission to start the guided YouTube-to-ChatGPT research loop.").classes("text-slate-400")
                with ui.row().classes("gap-2 mt-3"):
                    ui.button("Create Mission", icon="flag", on_click=lambda: ui.navigate.to("/missions"), color="primary")
                    ui.button("Build First Pack", icon="construction", on_click=lambda: ui.navigate.to("/build")).props("outline")
            return

        progress = mission_chain_progress(records, active_mission.mission_id)
        next_step = _next_pending_step(progress)
        next_label = CHAIN_STEP_LABELS.get(next_step, "All steps complete") if next_step else "All steps complete"
        selected_projects = selected_project_records(active_mission, projects)
        current_prompt = prompt_for_analysis_step(active_mission, selected_projects, next_step) if next_step else ""
        linked_records = mission_analysis_records(records, active_mission.mission_id)

        with ui.card().classes("ytis-card p-5 w-full"):
            with ui.row().classes("w-full justify-between items-start gap-4"):
                with ui.column().classes("gap-1 flex-1"):
                    ui.label("Current Mission").classes("text-sm text-slate-400")
                    ui.label(active_mission.name).classes("text-2xl font-bold")
                    ui.label(active_mission.goal or "(no mission goal)").classes("text-sm text-slate-300")
                    ui.label("Projects: " + (", ".join(active_mission.projects) if active_mission.projects else "-")).classes("text-xs text-blue-300")
                    ui.label("Topics: " + (", ".join(active_mission.topics) if active_mission.topics else "-")).classes("text-xs text-green-300")
                with ui.column().classes("gap-2"):
                    ui.button("Open Mission Manager", icon="flag", on_click=lambda: ui.navigate.to("/missions")).props("outline")
                    ui.button("Open Mission Folder", icon="folder_open", on_click=lambda: open_path(active_mission.folder)).props("outline")
            ui.separator().classes("my-3")
            ui.label("Progress").classes("font-bold")
            _progress_badges(progress)

        with ui.grid(columns=3).classes("w-full gap-4"):
            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Sources").classes("text-xl font-bold")
                ui.label("Source packs attached to the active mission.").classes("text-sm text-slate-400")
                if not active_mission.projects:
                    ui.label("No projects attached to this mission.").classes("text-orange-300")
                else:
                    for project in selected_projects:
                        name = val(project, "name", "Unnamed")
                        words = _compact(project.get("total_words"))
                        transcripts = _compact(project.get("transcripts_created"))
                        zip_path = project.get("zip_path")
                        ready = bool(zip_path and Path(str(zip_path)).exists())
                        with ui.card().classes("ytis-mini-card p-3 w-full"):
                            with ui.row().classes("w-full justify-between items-center gap-2"):
                                with ui.column().classes("gap-0"):
                                    ui.label(name).classes("font-bold")
                                    ui.label(f"{transcripts} transcripts | {words} words").classes("text-xs text-slate-400")
                                ui.badge("Ready" if ready else "Missing ZIP").props("color=green" if ready else "color=red")
                            if ready:
                                ui.button("Open ZIP", icon="inventory_2", on_click=lambda p=zip_path: open_path(p)).props("outline dense")
                with ui.row().classes("gap-2 mt-2"):
                    ui.button("Build Pack", icon="construction", on_click=lambda: ui.navigate.to("/build")).props("outline")
                    ui.button("Library", icon="folder", on_click=lambda: ui.navigate.to("/projects")).props("outline")

            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Current ChatGPT Step").classes("text-xl font-bold")
                ui.label(next_label).classes("text-lg font-bold text-cyan-300")
                if next_step:
                    ui.label("Copy this prompt, run it in ChatGPT, then paste the answer in the answer box below.").classes("text-sm text-slate-400")
                    prompt_box = ui.textarea("Current prompt", value=current_prompt).classes("w-full").props("rows=18")
                    prompt_box.style("font-family: Consolas, monospace; font-size: 12px; line-height: 1.45;")
                    with ui.row().classes("gap-2 mt-2"):
                        ui.button("Copy Prompt", icon="content_copy", on_click=lambda: (_copy_to_clipboard(prompt_box.value or ""), ui.notify("Prompt copied", type="positive")), color="primary")
                        ui.button("Open ChatGPT", icon="open_in_new", on_click=lambda: open_path("https://chat.openai.com")).props("outline")
                else:
                    ui.label("All mission steps have saved analyses. You can review linked answers or create a new mission.").classes("text-green-300")
                    ui.button("Linked Analyses", icon="link", on_click=lambda: ui.navigate.to("/missions"), color="primary")

            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Progress and Results").classes("text-xl font-bold")
                ui.label(f"Linked analyses: {len(linked_records)}").classes("text-sm text-slate-400")
                if linked_records:
                    for record in linked_records[:5]:
                        with ui.card().classes("ytis-mini-card p-3 w-full"):
                            ui.label(record.title).classes("font-bold text-sm")
                            step = CHAIN_STEP_LABELS.get(record.chain_step, record.chain_step)
                            ui.label(f"{step} | {record.word_count:,} words").classes("text-xs text-slate-400")
                            ui.button("Open", icon="article", on_click=lambda p=record.analysis_path: open_path(p)).props("outline dense")
                else:
                    ui.label("No saved answers linked to this mission yet.").classes("text-slate-400")

        if next_step:
            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Paste ChatGPT Answer and Save Step").classes("text-xl font-bold")
                ui.label("This saves directly to Analysis Library and links it to the active mission/step. No Analysis Inbox navigation needed.").classes("text-sm text-slate-400")

                with ui.grid(columns=3).classes("w-full gap-3"):
                    title_default = f"{active_mission.name} - {next_label}"
                    title_input = ui.input("Analysis title", value=title_default).classes("w-full")
                    topic_value = STEP_TO_TOPIC.get(next_step, "All topics")
                    topic_input = ui.input("Topic", value=topic_value).classes("w-full")
                    step_input = ui.input("Step", value=next_step).classes("w-full").props("readonly")

                notes_input = ui.textarea("Optional notes").classes("w-full").props("rows=2")
                answer_box = ui.textarea("Paste ChatGPT answer here").classes("w-full").props("rows=14")
                save_status = ui.label("Ready to save answer for: " + next_label).classes("text-xs text-slate-400")

                with ui.row().classes("gap-2"):
                    save_btn = ui.button("Save Answer and Advance", icon="save", color="primary")
                    clear_btn = ui.button("Clear Answer", icon="backspace").props("outline")
                    ui.button("Open Analysis Library", icon="move_to_inbox", on_click=lambda: ui.navigate.to("/analysis-inbox")).props("outline")

                def do_clear() -> None:
                    answer_box.value = ""
                    notes_input.value = ""
                    answer_box.update()
                    notes_input.update()
                    save_status.text = "Answer box cleared"
                    save_status.update()

                def do_save() -> None:
                    answer = answer_box.value or ""
                    if not answer.strip():
                        ui.notify("Paste the ChatGPT answer first", type="warning")
                        return

                    record = save_analysis(
                        project_root=project_root,
                        title=title_input.value or title_default,
                        analysis_text=answer,
                        projects=list(active_mission.projects),
                        topic=topic_input.value or topic_value,
                        focus_preset=active_mission.focus_preset,
                        source_bundle="",
                        source_evidence_pack="",
                        notes=notes_input.value or "",
                        mission_id=active_mission.mission_id,
                        mission_name=active_mission.name,
                        chain_step=next_step,
                    )
                    save_status.text = f"Saved: {record.record_id}. Refreshing dashboard..."
                    save_status.classes(remove="text-slate-400")
                    save_status.classes(add="text-green-400")
                    save_status.update()
                    ui.notify("Answer saved and linked to mission step", type="positive")
                    ui.timer(0.8, lambda: ui.navigate.to("/"), once=True)

                save_btn.on("click", do_save)
                clear_btn.on("click", do_clear)

        with ui.grid(columns=2).classes("w-full gap-4"):
            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Quick Research Actions").classes("text-xl font-bold")
                with ui.grid(columns=2).classes("w-full gap-2"):
                    ui.button("Mission Manager", icon="flag", on_click=lambda: ui.navigate.to("/missions")).props("outline")
                    ui.button("Intelligence", icon="hub", on_click=lambda: ui.navigate.to("/intelligence")).props("outline")
                    ui.button("Search Sources", icon="search", on_click=lambda: ui.navigate.to("/search")).props("outline")
                    ui.button("Transcript Viewer", icon="article", on_click=lambda: ui.navigate.to("/viewer")).props("outline")
                    ui.button("Analysis Library", icon="move_to_inbox", on_click=lambda: ui.navigate.to("/analysis-inbox")).props("outline")
                    ui.button("Inspector", icon="fact_check", on_click=lambda: ui.navigate.to("/inspector")).props("outline")

            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Warnings / Cleanup").classes("text-xl font-bold")
                warnings = []
                duplicates = duplicate_mission_names(missions)
                if duplicates:
                    warnings.append("Duplicate mission names: " + ", ".join(sorted(duplicates)))
                if mission_stats_data.get("archived", 0):
                    warnings.append(f"{mission_stats_data.get('archived', 0)} archived mission(s)")
                missing_zips = [val(p, "name", "Unnamed") for p in projects if p.get("zip_path") and not Path(str(p.get("zip_path"))).exists()]
                if missing_zips:
                    warnings.append("Missing ZIPs: " + ", ".join(missing_zips[:5]))
                if not warnings:
                    ui.label("No major workflow warnings.").classes("text-green-300")
                else:
                    for warning in warnings:
                        ui.label("- " + warning).classes("text-sm text-orange-300")
                with ui.row().classes("gap-2 mt-2"):
                    ui.button("Manage Missions", icon="settings", on_click=lambda: ui.navigate.to("/missions")).props("outline")
                    ui.button("Health", icon="monitor_heart", on_click=lambda: ui.navigate.to("/health")).props("outline")
