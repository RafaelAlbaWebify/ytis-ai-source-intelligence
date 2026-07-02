from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

from nicegui import ui

from ytis.ui.layout import render_shell
from ytis.ui.state import AppState


CHAIN_ORDER = [
    "STEP_01_extract_map",
    "STEP_02_compare_patterns",
    "STEP_03_extract_workflows",
    "STEP_04_apply_to_rafael_webify",
    "STEP_05_validation_plan",
]

STEP_LABELS_FALLBACK = {
    "STEP_01_extract_map": "Step 1 - Extract and map",
    "STEP_02_compare_patterns": "Step 2 - Compare patterns",
    "STEP_03_extract_workflows": "Step 3 - Extract workflows",
    "STEP_04_apply_to_rafael_webify": "Step 4 - Apply to Rafael/Webify",
    "STEP_05_validation_plan": "Step 5 - Validation plan",
}

STEP_SHORT_LABELS = {
    "STEP_01_extract_map": "1 Map",
    "STEP_02_compare_patterns": "2 Compare",
    "STEP_03_extract_workflows": "3 Workflows",
    "STEP_04_apply_to_rafael_webify": "4 Apply",
    "STEP_05_validation_plan": "5 Validate",
}

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
    ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(text or '')})")


def _open_chatgpt() -> None:
    ui.run_javascript("window.open('https://chatgpt.com', '_blank')")


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


def _get_attr(obj: Any, name: str, default: Any = "") -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _load_runtime(project_root: Path, state: AppState) -> dict[str, Any]:
    data: dict[str, Any] = {
        "errors": [],
        "missions": [],
        "records": [],
        "projects": [],
        "stats": {},
        "step_labels": STEP_LABELS_FALLBACK,
    }

    try:
        from ytis.core.missions import list_missions, mission_stats
        data["missions"] = list_missions(project_root)
        data["stats"] = mission_stats(data["missions"])
    except Exception as exc:
        data["errors"].append("Mission load failed: " + str(exc))

    try:
        from ytis.core.analysis_inbox import CHAIN_STEP_LABELS, list_analyses
        data["step_labels"] = CHAIN_STEP_LABELS
        data["records"] = list_analyses(project_root)
    except Exception as exc:
        data["errors"].append("Analysis load failed: " + str(exc))

    try:
        from ytis.core.project_hygiene import audit_projects
        data["projects"] = audit_projects(state.load_projects())
    except Exception as exc:
        data["errors"].append("Project load failed: " + str(exc))

    return data


def _select_current_mission(missions: list[Any]) -> Any | None:
    active = [m for m in missions if _get_attr(m, "status", "") == "active"]
    if active:
        return active[0]
    visible = [m for m in missions if _get_attr(m, "status", "") != "archived"]
    if visible:
        return visible[0]
    return missions[0] if missions else None


def _progress_for_mission(records: list[Any], mission: Any) -> dict[str, int]:
    try:
        from ytis.core.analysis_inbox import mission_chain_progress
        return mission_chain_progress(records, _get_attr(mission, "mission_id", ""))
    except Exception:
        progress = {step: 0 for step in CHAIN_ORDER}
        mission_id = _get_attr(mission, "mission_id", "")
        for record in records:
            if _get_attr(record, "mission_id", "") == mission_id:
                step = _get_attr(record, "chain_step", "Unassigned")
                progress[step] = progress.get(step, 0) + 1
        progress["Total"] = sum(progress.get(step, 0) for step in CHAIN_ORDER)
        return progress


def _next_pending_step(progress: dict[str, int]) -> str:
    for step in CHAIN_ORDER:
        if progress.get(step, 0) <= 0:
            return step
    return ""


def _selected_project_records(mission: Any, projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    names = list(_get_attr(mission, "projects", []) or [])
    lookup = {str(p.get("name", "Unnamed")): p for p in projects if isinstance(p, dict)}
    return [lookup[name] for name in names if name in lookup]


def _prompt_for_analysis_step(mission: Any, projects: list[dict[str, Any]], analysis_step: str) -> str:
    if not analysis_step:
        return ""
    try:
        from ytis.core.missions import generate_prompt_chain
        chain = generate_prompt_chain(mission, projects)
        for step_id, (_, prompt) in zip(CHAIN_ORDER, chain):
            if step_id == analysis_step:
                return prompt
        return chain[0][1] if chain else ""
    except Exception as exc:
        return (
            "# YTIS prompt generation fallback\n\n"
            f"Mission: {_get_attr(mission, 'name', 'Untitled mission')}\n"
            f"Step: {STEP_LABELS_FALLBACK.get(analysis_step, analysis_step)}\n\n"
            "Could not generate the full mission prompt automatically.\n\n"
            f"Error: {exc}\n\n"
            "Go to Missions if you need the full prompt chain."
        )


def _duplicate_mission_names(missions: list[Any]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for mission in missions:
        key = str(_get_attr(mission, "name", "")).strip().lower()
        if not key:
            continue
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates


def _mission_records(records: list[Any], mission: Any) -> list[Any]:
    mission_id = _get_attr(mission, "mission_id", "")
    return [r for r in records if _get_attr(r, "mission_id", "") == mission_id]


def _done_count(progress: dict[str, int]) -> int:
    return sum(1 for step in CHAIN_ORDER if progress.get(step, 0) > 0)


def _progress_badges(progress: dict[str, int], current_step: str) -> None:
    with ui.row().classes("gap-1 flex-wrap"):
        for step in CHAIN_ORDER:
            done = progress.get(step, 0) > 0
            current = step == current_step
            text = STEP_SHORT_LABELS.get(step, step)
            if done:
                ui.badge("OK " + text).props("color=green")
            elif current:
                ui.badge("NOW " + text).props("color=cyan")
            else:
                ui.badge("-- " + text).props("color=grey")


def _render_dashboard_body(state: AppState) -> None:
    project_root = _project_root(state)
    runtime = _load_runtime(project_root, state)

    missions = runtime["missions"]
    records = runtime["records"]
    projects = runtime["projects"]
    labels = runtime["step_labels"]
    stats = runtime["stats"]

    mission = _select_current_mission(missions)

    with ui.column().classes("ytis-page gap-2"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("YTIS Dashboard").classes("text-2xl font-bold")
                ui.label("Copy -> ChatGPT -> Paste -> Save").classes("text-xs text-slate-400")
            with ui.row().classes("gap-1"):
                ui.button("Missions", icon="flag", on_click=lambda: ui.navigate.to("/missions")).props("outline dense")
                ui.button("Build", icon="construction", on_click=lambda: ui.navigate.to("/build")).props("outline dense")
                ui.button("Search", icon="search", on_click=lambda: ui.navigate.to("/search")).props("outline dense")

        if runtime["errors"]:
            with ui.expansion("Dashboard warnings", icon="warning", value=False).classes("ytis-card w-full text-white").props("dense"):
                with ui.column().classes("p-2 gap-1"):
                    for error in runtime["errors"]:
                        ui.label(error).classes("text-sm text-orange-300")

        if not mission:
            with ui.card().classes("ytis-card p-4 w-full"):
                ui.label("No mission available").classes("text-xl font-bold")
                ui.label("Create a mission first. Then the dashboard becomes the normal working screen.").classes("text-slate-400")
                ui.button("Create Mission", icon="flag", on_click=lambda: ui.navigate.to("/missions"), color="primary")
            return

        progress = _progress_for_mission(records, mission)
        next_step = _next_pending_step(progress)
        next_label = labels.get(next_step, STEP_LABELS_FALLBACK.get(next_step, "All steps complete")) if next_step else "All steps complete"
        selected_projects = _selected_project_records(mission, projects)
        prompt = _prompt_for_analysis_step(mission, selected_projects, next_step)
        linked = _mission_records(records, mission)
        duplicates = _duplicate_mission_names(missions)
        done = _done_count(progress)

        with ui.card().classes("ytis-card p-3 w-full"):
            with ui.row().classes("w-full items-center justify-between gap-3"):
                with ui.column().classes("gap-0 flex-1"):
                    ui.label(str(_get_attr(mission, "name", "Untitled mission"))).classes("text-xl font-bold")
                    ui.label(f"Next action: {next_label}").classes("text-base font-bold text-cyan-300")
                with ui.row().classes("gap-1 items-center"):
                    ui.badge(f"{done}/5 done").props("color=blue")
                    ui.button("Manager", icon="flag", on_click=lambda: ui.navigate.to("/missions")).props("outline dense")
            _progress_badges(progress, next_step)
            if duplicates:
                ui.label("Duplicate mission names detected: " + ", ".join(sorted(duplicates))).classes("text-xs text-orange-300")

        with ui.card().classes("ytis-card p-3 w-full"):
            with ui.row().classes("items-center gap-2 flex-wrap"):
                ui.badge("1 Copy prompt").props("color=blue")
                ui.label("->").classes("text-slate-400")
                ui.badge("2 Run in ChatGPT").props("color=blue")
                ui.label("->").classes("text-slate-400")
                ui.badge("3 Paste answer").props("color=blue")
                ui.label("->").classes("text-slate-400")
                ui.badge("4 Save and advance").props("color=green")

        with ui.grid(columns=2).classes("w-full gap-3"):
            with ui.card().classes("ytis-card p-4 w-full"):
                with ui.row().classes("w-full justify-between items-center"):
                    with ui.column().classes("gap-0"):
                        ui.label("Prompt").classes("text-xl font-bold")
                        ui.label(next_label).classes("text-xs text-cyan-300")
                    if next_step:
                        ui.button("Copy Prompt", icon="content_copy", on_click=lambda: (_copy_to_clipboard(prompt), ui.notify("Prompt copied", type="positive")), color="primary").props("dense")
                if next_step:
                    prompt_box = ui.textarea(value=prompt).classes("w-full").props("rows=13")
                    prompt_box.style("font-family: Consolas, monospace; font-size: 12px; line-height: 1.3;")
                    with ui.row().classes("gap-1"):
                        ui.button("Copy Prompt", icon="content_copy", on_click=lambda: (_copy_to_clipboard(prompt_box.value or ""), ui.notify("Prompt copied", type="positive"))).props("outline dense")
                        ui.button("Open ChatGPT", icon="open_in_new", on_click=_open_chatgpt).props("outline dense")
                else:
                    ui.label("All mission steps have saved answers.").classes("text-green-300")

            with ui.card().classes("ytis-card p-4 w-full"):
                with ui.row().classes("w-full justify-between items-center"):
                    with ui.column().classes("gap-0"):
                        ui.label("Answer").classes("text-xl font-bold")
                        ui.label("Paste ChatGPT result here").classes("text-xs text-slate-400")
                if next_step:
                    title_default = f"{_get_attr(mission, 'name', 'Mission')} - {next_label}"
                    title_input = ui.input("Title", value=title_default).classes("w-full").props("dense")
                    answer_box = ui.textarea("Paste answer here").classes("w-full").props("rows=11")
                    notes_box = ui.textarea("Notes optional").classes("w-full").props("rows=1")
                    status_label = ui.label("Ready to save.").classes("text-xs text-slate-400")

                    def do_save() -> None:
                        text = answer_box.value or ""
                        if not text.strip():
                            ui.notify("Paste the ChatGPT answer first", type="warning")
                            return
                        try:
                            from ytis.core.analysis_inbox import save_analysis
                            record = save_analysis(
                                project_root=project_root,
                                title=title_input.value or title_default,
                                analysis_text=text,
                                projects=list(_get_attr(mission, "projects", []) or []),
                                topic=STEP_TO_TOPIC.get(next_step, "All topics"),
                                focus_preset=str(_get_attr(mission, "focus_preset", "Custom") or "Custom"),
                                source_bundle="",
                                source_evidence_pack="",
                                notes=notes_box.value or "",
                                mission_id=str(_get_attr(mission, "mission_id", "")),
                                mission_name=str(_get_attr(mission, "name", "")),
                                chain_step=next_step,
                            )
                            status_label.text = f"Saved: {_get_attr(record, 'record_id', 'analysis')}"
                            status_label.classes(remove="text-slate-400")
                            status_label.classes(add="text-green-400")
                            status_label.update()
                            ui.notify("Saved and linked. Dashboard will advance.", type="positive")
                            ui.timer(0.7, lambda: ui.navigate.to("/"), once=True)
                        except Exception as exc:
                            ui.notify("Save failed: " + str(exc), type="negative")
                            status_label.text = "Save failed: " + str(exc)
                            status_label.classes(remove="text-slate-400")
                            status_label.classes(add="text-red-300")
                            status_label.update()

                    with ui.row().classes("gap-2 w-full"):
                        ui.button("Save and Advance", icon="save", on_click=do_save, color="primary").classes("flex-1")
                        ui.button("Clear", icon="backspace", on_click=lambda: (setattr(answer_box, "value", ""), answer_box.update())).props("outline")
                else:
                    ui.label("No pending step to save.").classes("text-green-300")

        with ui.expansion("Details: sources, saved answers, system", icon="tune", value=False).classes("ytis-card w-full text-white").props("dense"):
            with ui.grid(columns=3).classes("w-full gap-3 p-3"):
                with ui.card().classes("ytis-mini-card p-3 w-full"):
                    ui.label("Sources").classes("font-bold")
                    if not selected_projects:
                        ui.label("No attached project records.").classes("text-sm text-orange-300")
                    for project in selected_projects:
                        name = project.get("name", "Unnamed") if isinstance(project, dict) else "Unnamed"
                        words = _compact(project.get("total_words", 0)) if isinstance(project, dict) else "0"
                        transcripts = _compact(project.get("transcripts_created", 0)) if isinstance(project, dict) else "0"
                        ui.label(f"{name}: {transcripts} transcripts, {words} words").classes("text-sm")
                with ui.card().classes("ytis-mini-card p-3 w-full"):
                    ui.label("Saved answers").classes("font-bold")
                    if not linked:
                        ui.label("No saved answers for this mission.").classes("text-sm text-slate-400")
                    for record in linked[:6]:
                        title = str(_get_attr(record, "title", "Untitled"))
                        step = str(_get_attr(record, "chain_step", ""))
                        ui.label(title).classes("text-sm font-bold")
                        ui.label(step).classes("text-xs text-slate-400")
                with ui.card().classes("ytis-mini-card p-3 w-full"):
                    ui.label("System").classes("font-bold")
                    ui.label(f"Missions: {stats.get('missions', len(missions))} | Active: {stats.get('active', 0)}").classes("text-sm")
                    ui.label(f"Projects: {len(projects)} | Analyses: {len(records)}").classes("text-sm")
                    with ui.row().classes("gap-1 mt-1"):
                        ui.button("Analysis", icon="move_to_inbox", on_click=lambda: ui.navigate.to("/analysis-inbox")).props("outline dense")
                        ui.button("Health", icon="monitor_heart", on_click=lambda: ui.navigate.to("/health")).props("outline dense")


def _render_error_page(state: AppState, exc: Exception) -> None:
    with ui.column().classes("ytis-page gap-3"):
        ui.label("YTIS Dashboard safe mode").classes("text-3xl font-bold")
        ui.label("Dashboard rendering failed, but the app is still usable. Use the links below while we inspect the error.").classes("text-orange-300")
        with ui.row().classes("gap-2"):
            ui.button("Missions", icon="flag", on_click=lambda: ui.navigate.to("/missions"), color="primary")
            ui.button("Build", icon="construction", on_click=lambda: ui.navigate.to("/build")).props("outline")
            ui.button("Search", icon="search", on_click=lambda: ui.navigate.to("/search")).props("outline")
            ui.button("Health", icon="monitor_heart", on_click=lambda: ui.navigate.to("/health")).props("outline")
        ui.label("Error").classes("text-xl font-bold")
        ui.code(str(exc)).classes("w-full")
        ui.label("Traceback").classes("text-xl font-bold")
        ui.code(traceback.format_exc()).classes("w-full")


def render_dashboard(state: AppState) -> None:
    render_shell(state, "/")
    try:
        _render_dashboard_body(state)
    except Exception as exc:
        _render_error_page(state, exc)
