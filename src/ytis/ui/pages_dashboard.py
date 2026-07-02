from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nicegui import ui

from ytis.core.analysis_inbox import (
    CHAIN_STEP_LABELS,
    list_analyses,
    mission_analysis_records,
    mission_chain_progress,
    save_analysis,
)
from ytis.core.missions import (
    generate_prompt_chain,
    list_missions,
    mission_stats,
    selected_project_records,
)
from ytis.core.project_hygiene import audit_projects
from ytis.ui.components import open_path
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, val


CHAIN_ORDER = [
    "STEP_01_extract_map",
    "STEP_02_compare_patterns",
    "STEP_03_extract_workflows",
    "STEP_04_apply_to_rafael_webify",
    "STEP_05_validation_plan",
]

STEP_TO_TOPIC = {
    "STEP_01_extract_map": "All topics",
    "STEP_02_compare_patterns": "Offer",
    "STEP_03_extract_workflows": "Workflow",
    "STEP_04_apply_to_rafael_webify": "Webify service ideas",
    "STEP_05_validation_plan": "Webify service ideas",
}


def _project_root(state: AppState) -> Path:
    return Path(getattr(state, "project_root", "") or Path.cwd())


def _copy_to_clipboard(text: str) -> None:
    ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(text)})")


def _safe_int(value: Any) -> int:
    try:
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return 0


def _compact(value: Any) -> str:
    n = _safe_int(value)
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if abs(n) >= 1_000:
        return f"{n / 1_000:.1f}k".replace(".0k", "k")
    return f"{n:,}"


def _select_current_mission(project_root: Path, requested_id: str = ""):
    missions = list_missions(project_root)
    if requested_id:
        for mission in missions:
            if mission.mission_id == requested_id:
                return mission
    active = [m for m in missions if m.status == "active"]
    if active:
        return active[0]
    visible = [m for m in missions if m.status != "archived"]
    if visible:
        return visible[0]
    return missions[0] if missions else None


def _next_pending_step(progress: dict[str, int]) -> str:
    for step in CHAIN_ORDER:
        if progress.get(step, 0) <= 0:
            return step
    return ""


def _prompt_for_analysis_step(mission, projects: list[dict[str, Any]], analysis_step: str) -> str:
    if not analysis_step:
        return ""
    try:
        chain = generate_prompt_chain(mission, projects)
        for step_id, (_, prompt) in zip(CHAIN_ORDER, chain):
            if step_id == analysis_step:
                return prompt
        return chain[0][1] if chain else ""
    except Exception as exc:
        return f"Could not generate prompt for {analysis_step}: {exc}"


def _duplicate_mission_names(missions) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for mission in missions:
        key = (mission.name or "").strip().lower()
        if not key:
            continue
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates


def _mission_options(missions) -> dict[str, str]:
    options: dict[str, str] = {}
    for mission in missions:
        label = f"{mission.name} [{mission.status}]"
        options[label] = mission.mission_id
    return options


def _step_progress_row(progress: dict[str, int]) -> None:
    with ui.row().classes("gap-1 flex-wrap"):
        for step in CHAIN_ORDER:
            done = progress.get(step, 0) > 0
            short = CHAIN_STEP_LABELS.get(step, step).replace("Step ", "")
            ui.badge(("OK " if done else "-- ") + short).props("color=green" if done else "color=grey")


def _open_chatgpt() -> None:
    ui.run_javascript("window.open('https://chatgpt.com', '_blank')")


def render_dashboard(state: AppState) -> None:
    render_shell(state, "/")

    project_root = _project_root(state)
    projects = audit_projects(state.load_projects())
    records = list_analyses(project_root)
    missions = list_missions(project_root)
    stats = mission_stats(missions)

    requested_id = ""
    try:
        requested_id = str(ui.context.client.request.query_params.get("mission_id", ""))
    except Exception:
        requested_id = ""

    mission = _select_current_mission(project_root, requested_id)

    with ui.column().classes("ytis-page gap-3"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("YTIS Dashboard").classes("text-3xl font-bold")
                ui.label("Compact workflow: copy prompt, run ChatGPT, save answer, advance.").classes("text-sm text-slate-400")
            with ui.row().classes("gap-2"):
                ui.button("Missions", icon="flag", on_click=lambda: ui.navigate.to("/missions")).props("outline dense")
                ui.button("Build", icon="construction", on_click=lambda: ui.navigate.to("/build")).props("outline dense")
                ui.button("Search", icon="search", on_click=lambda: ui.navigate.to("/search")).props("outline dense")

        if not mission:
            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("No mission available").classes("text-2xl font-bold")
                ui.label("Create a mission first. Then this dashboard becomes the normal working screen.").classes("text-slate-400")
                ui.button("Create Mission", icon="flag", on_click=lambda: ui.navigate.to("/missions"), color="primary")
            return

        progress = mission_chain_progress(records, mission.mission_id)
        next_step = _next_pending_step(progress)
        next_label = CHAIN_STEP_LABELS.get(next_step, "All steps complete") if next_step else "All steps complete"
        selected_projects = selected_project_records(mission, projects)
        current_prompt = _prompt_for_analysis_step(mission, selected_projects, next_step)
        linked_records = mission_analysis_records(records, mission.mission_id)

        mission_select_options = _mission_options(missions)
        selected_label = next((label for label, mid in mission_select_options.items() if mid == mission.mission_id), "")
        duplicates = _duplicate_mission_names(missions)

        with ui.card().classes("ytis-card p-4 w-full"):
            with ui.row().classes("w-full items-center justify-between gap-3"):
                with ui.column().classes("gap-1 flex-1"):
                    ui.label("Current mission").classes("text-xs text-slate-400")
                    ui.label(mission.name).classes("text-2xl font-bold")
                    ui.label("Next: " + next_label).classes("text-lg font-bold text-cyan-300")
                with ui.column().classes("gap-1").style("min-width: 340px;"):
                    mission_selector = ui.select(
                        options=mission_select_options,
                        value=mission.mission_id,
                        label="Switch mission",
                    ).classes("w-full")
                    mission_selector.on("update:model-value", lambda e: ui.navigate.to(f"/?mission_id={e.args}"))
            ui.label(mission.goal or "(no goal)").classes("text-sm text-slate-300")
            _step_progress_row(progress)
            if duplicates:
                ui.label("Warning: duplicate mission names: " + ", ".join(sorted(duplicates))).classes("text-xs text-orange-300")

        with ui.grid(columns=2).classes("w-full gap-3"):
            with ui.card().classes("ytis-card p-4 w-full"):
                ui.label("1. Prompt to send to ChatGPT").classes("text-xl font-bold")
                ui.label(next_label).classes("text-sm text-cyan-300")
                if next_step:
                    prompt_box = ui.textarea(value=current_prompt).classes("w-full").props("rows=18")
                    prompt_box.style("font-family: Consolas, monospace; font-size: 12px; line-height: 1.35;")
                    with ui.row().classes("gap-2"):
                        ui.button("Copy Prompt", icon="content_copy", on_click=lambda: (_copy_to_clipboard(prompt_box.value or ""), ui.notify("Prompt copied", type="positive")), color="primary")
                        ui.button("Open ChatGPT", icon="open_in_new", on_click=_open_chatgpt).props("outline")
                else:
                    ui.label("All prompt-chain steps have saved answers.").classes("text-green-300")
                    ui.button("Open linked analyses", icon="link", on_click=lambda: ui.navigate.to("/analysis-inbox"), color="primary")

            with ui.card().classes("ytis-card p-4 w-full"):
                ui.label("2. Paste ChatGPT answer").classes("text-xl font-bold")
                if next_step:
                    title_default = f"{mission.name} - {next_label}"
                    title_input = ui.input("Title", value=title_default).classes("w-full")
                    answer_box = ui.textarea("Paste answer here").classes("w-full").props("rows=18")
                    notes_box = ui.textarea("Notes optional").classes("w-full").props("rows=2")
                    status_label = ui.label("Ready to save this answer to the current mission step.").classes("text-xs text-slate-400")

                    def do_save() -> None:
                        text = answer_box.value or ""
                        if not text.strip():
                            ui.notify("Paste the ChatGPT answer first", type="warning")
                            return
                        record = save_analysis(
                            project_root=project_root,
                            title=title_input.value or title_default,
                            analysis_text=text,
                            projects=list(mission.projects),
                            topic=STEP_TO_TOPIC.get(next_step, "All topics"),
                            focus_preset=mission.focus_preset,
                            source_bundle="",
                            source_evidence_pack="",
                            notes=notes_box.value or "",
                            mission_id=mission.mission_id,
                            mission_name=mission.name,
                            chain_step=next_step,
                        )
                        status_label.text = f"Saved: {record.record_id}"
                        status_label.classes(remove="text-slate-400")
                        status_label.classes(add="text-green-400")
                        status_label.update()
                        ui.notify("Saved and linked. Dashboard will advance.", type="positive")
                        ui.timer(0.7, lambda: ui.navigate.to(f"/?mission_id={mission.mission_id}"), once=True)

                    with ui.row().classes("gap-2"):
                        ui.button("Save and Advance", icon="save", on_click=do_save, color="primary")
                        ui.button("Clear", icon="backspace", on_click=lambda: (setattr(answer_box, "value", ""), answer_box.update())).props("outline")
                else:
                    ui.label("No pending step to save.").classes("text-green-300")

        with ui.expansion("Details: sources, saved analyses, warnings", icon="tune", value=False).classes("ytis-card w-full text-white").props("dense expand-separator"):
            with ui.grid(columns=3).classes("w-full gap-3 p-3"):
                with ui.card().classes("ytis-mini-card p-3 w-full"):
                    ui.label("Sources").classes("font-bold")
                    if not selected_projects:
                        ui.label("No attached project records.").classes("text-orange-300 text-sm")
                    for project in selected_projects:
                        name = val(project, "name", "Unnamed")
                        words = _compact(project.get("total_words"))
                        transcripts = _compact(project.get("transcripts_created"))
                        zip_path = project.get("zip_path")
                        ready = bool(zip_path and Path(str(zip_path)).exists())
                        ui.label(f"{name}: {transcripts} transcripts, {words} words").classes("text-sm")
                        if ready:
                            ui.button("Open ZIP", icon="inventory_2", on_click=lambda p=zip_path: open_path(p)).props("outline dense")

                with ui.card().classes("ytis-mini-card p-3 w-full"):
                    ui.label("Saved for this mission").classes("font-bold")
                    if not linked_records:
                        ui.label("No saved answers yet.").classes("text-sm text-slate-400")
                    for record in linked_records[:6]:
                        step = CHAIN_STEP_LABELS.get(record.chain_step, record.chain_step)
                        ui.label(record.title).classes("text-sm font-bold")
                        ui.label(f"{step} | {record.word_count:,} words").classes("text-xs text-slate-400")

                with ui.card().classes("ytis-mini-card p-3 w-full"):
                    ui.label("System summary").classes("font-bold")
                    ui.label(f"Missions: {stats.get('missions', 0)} | Active: {stats.get('active', 0)} | Archived: {stats.get('archived', 0)}").classes("text-sm")
                    ui.label(f"Projects: {len(projects)} | Analyses: {len(records)}").classes("text-sm")
                    with ui.row().classes("gap-2 mt-2"):
                        ui.button("Analysis Library", icon="move_to_inbox", on_click=lambda: ui.navigate.to("/analysis-inbox")).props("outline dense")
                        ui.button("Health", icon="monitor_heart", on_click=lambda: ui.navigate.to("/health")).props("outline dense")
