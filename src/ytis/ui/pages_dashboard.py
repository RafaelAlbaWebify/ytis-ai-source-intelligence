from __future__ import annotations

import json
import traceback
from datetime import datetime
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


def _state_dir(project_root: Path) -> Path:
    path = project_root / "ytis_state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _current_mission_state_path(project_root: Path) -> Path:
    return _state_dir(project_root) / "current_mission.json"


def _read_current_mission_id(project_root: Path) -> str:
    path = _current_mission_state_path(project_root)
    if not path.exists():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return str(data.get("mission_id") or "")
    except Exception:
        return ""


def _write_current_mission_id(project_root: Path, mission_id: str) -> None:
    path = _current_mission_state_path(project_root)
    data = {
        "mission_id": mission_id,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


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


def _mission_metadata_path(mission: Any) -> Path | None:
    path = _get_attr(mission, "metadata_path", None)
    if path:
        return Path(path)
    folder = _get_attr(mission, "folder", None)
    if folder:
        return Path(folder) / "mission.json"
    return None


def _read_mission_json(mission: Any) -> dict[str, Any]:
    path = _mission_metadata_path(mission)
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _write_mission_json(mission: Any, data: dict[str, Any]) -> None:
    path = _mission_metadata_path(mission)
    if not path:
        raise RuntimeError("Mission metadata path not found")
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _rename_mission(mission: Any, new_name: str) -> None:
    data = _read_mission_json(mission)
    if not data:
        raise RuntimeError("Could not read mission metadata")
    clean = (new_name or "").strip()
    if not clean:
        raise RuntimeError("Mission name cannot be empty")
    data["name"] = clean
    _write_mission_json(mission, data)


def _set_mission_status(mission: Any, status: str) -> None:
    data = _read_mission_json(mission)
    if not data:
        raise RuntimeError("Could not read mission metadata")
    data["status"] = status
    _write_mission_json(mission, data)


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


def _select_current_mission(project_root: Path, missions: list[Any]) -> Any | None:
    current_id = _read_current_mission_id(project_root)
    if current_id:
        for mission in missions:
            if str(_get_attr(mission, "mission_id", "")) == current_id and _get_attr(mission, "status", "") != "archived":
                return mission
    active = [m for m in missions if _get_attr(m, "status", "") == "active"]
    if active:
        return active[0]
    visible = [m for m in missions if _get_attr(m, "status", "") != "archived"]
    if visible:
        return visible[0]
    return missions[0] if missions else None


def _mission_select_options(missions: list[Any]) -> dict[str, str]:
    options: dict[str, str] = {}
    visible = [m for m in missions if _get_attr(m, "status", "") != "archived"]
    for mission in visible:
        created = str(_get_attr(mission, "created_at", ""))[:16]
        status = str(_get_attr(mission, "status", ""))
        name = str(_get_attr(mission, "name", "Untitled mission"))
        mission_id = str(_get_attr(mission, "mission_id", ""))
        label = f"{name} | {status} | {created}"
        options[label] = mission_id
    return options


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


def _duplicate_name_groups(missions: list[Any]) -> dict[str, list[Any]]:
    groups: dict[str, list[Any]] = {}
    for mission in missions:
        if _get_attr(mission, "status", "") == "archived":
            continue
        key = str(_get_attr(mission, "name", "")).strip().lower()
        if not key:
            continue
        groups.setdefault(key, []).append(mission)
    return {k: v for k, v in groups.items() if len(v) > 1}


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


def _archive_duplicate_missions(project_root: Path, missions: list[Any], keep_mission: Any) -> int:
    keep_id = str(_get_attr(keep_mission, "mission_id", ""))
    keep_name = str(_get_attr(keep_mission, "name", "")).strip().lower()
    count = 0
    for mission in missions:
        mission_id = str(_get_attr(mission, "mission_id", ""))
        name = str(_get_attr(mission, "name", "")).strip().lower()
        status = str(_get_attr(mission, "status", ""))
        if mission_id != keep_id and name == keep_name and status != "archived":
            _set_mission_status(mission, "archived")
            count += 1
    _write_current_mission_id(project_root, keep_id)
    return count


def _render_dashboard_body(state: AppState) -> None:
    project_root = _project_root(state)
    runtime = _load_runtime(project_root, state)

    missions = runtime["missions"]
    records = runtime["records"]
    projects = runtime["projects"]
    labels = runtime["step_labels"]
    stats = runtime["stats"]

    mission = _select_current_mission(project_root, missions)

    with ui.column().classes("ytis-page gap-2"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("YTIS Dashboard").classes("text-2xl font-bold")
                ui.label("The Dashboard guides the full ChatGPT loop: copy the YTIS prompt, paste it into ChatGPT, then save the ChatGPT answer here.").classes("text-xs text-slate-400")
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

        _write_current_mission_id(project_root, str(_get_attr(mission, "mission_id", "")))

        progress = _progress_for_mission(records, mission)
        next_step = _next_pending_step(progress)
        next_label = labels.get(next_step, STEP_LABELS_FALLBACK.get(next_step, "All steps complete")) if next_step else "All steps complete"
        selected_projects = _selected_project_records(mission, projects)
        prompt = _prompt_for_analysis_step(mission, selected_projects, next_step)
        linked = _mission_records(records, mission)
        duplicate_groups = _duplicate_name_groups(missions)
        has_current_duplicates = str(_get_attr(mission, "name", "")).strip().lower() in duplicate_groups
        done = _done_count(progress)
        options = _mission_select_options(missions)

        with ui.card().classes("ytis-card p-3 w-full"):
            with ui.row().classes("w-full items-center justify-between gap-3"):
                with ui.column().classes("gap-0 flex-1"):
                    ui.label(str(_get_attr(mission, "name", "Untitled mission"))).classes("text-xl font-bold")
                    ui.label(f"Next action: {next_label}").classes("text-base font-bold text-cyan-300")
                with ui.row().classes("gap-1 items-center"):
                    ui.badge(f"{done}/5 done").props("color=blue")
                    ui.button("Manager", icon="flag", on_click=lambda: ui.navigate.to("/missions")).props("outline dense")
            with ui.row().classes("w-full items-center gap-2 mt-1"):
                if options:
                    current_id = str(_get_attr(mission, "mission_id", ""))
                    current_label = next((label for label, mid in options.items() if mid == current_id), None)
                    selector = ui.select(options=list(options.keys()), value=current_label, label="Current mission").classes("flex-1")
                    selector.props("dense")
                    def _switch_current_mission(e) -> None:
                        selected_label = str(e.args or "")
                        selected_id = options.get(selected_label, "")
                        if selected_id:
                            _write_current_mission_id(project_root, selected_id)
                            ui.navigate.to("/")
                    selector.on("update:model-value", _switch_current_mission)
                ui.button("Set Current", icon="push_pin", on_click=lambda: (_write_current_mission_id(project_root, str(_get_attr(mission, "mission_id", ""))), ui.notify("Current mission saved", type="positive"))).props("outline dense")
            _progress_badges(progress, next_step)
            if has_current_duplicates:
                with ui.row().classes("gap-2 items-center"):
                    ui.label("Duplicate active mission name detected for this mission.").classes("text-xs text-orange-300")
                    ui.button(
                        "Archive duplicates",
                        icon="archive",
                        on_click=lambda: (
                            ui.notify(f"Archived {_archive_duplicate_missions(project_root, missions, mission)} duplicate mission(s)", type="positive"),
                            ui.timer(0.5, lambda: ui.navigate.to("/"), once=True),
                        ),
                    ).props("outline dense")

        with ui.card().classes("ytis-card p-3 w-full"):
            with ui.row().classes("items-center gap-2 flex-wrap"):
                ui.badge("1 Copy YTIS prompt").props("color=blue")
                ui.label("->").classes("text-slate-400")
                ui.badge("2 Paste into ChatGPT").props("color=blue")
                ui.label("->").classes("text-slate-400")
                ui.badge("3 Paste ChatGPT answer here").props("color=blue")
                ui.label("->").classes("text-slate-400")
                ui.badge("4 Save answer and advance").props("color=green")

        with ui.card().classes("ytis-card p-3 w-full"):
            with ui.row().classes("w-full items-center gap-3"):
                ui.icon("info").classes("text-2xl text-cyan-300")
                with ui.column().classes("gap-0 flex-1"):
                    ui.label("What to do now").classes("font-bold text-cyan-300")
                    if next_step:
                        ui.label("LEFT panel: YTIS prompt to send to ChatGPT. RIGHT panel: paste the ChatGPT answer you received, then click Save ChatGPT Answer and Advance.").classes("text-sm text-slate-300")
                    else:
                        ui.label("This mission has no pending prompt-chain steps. Review saved answers or create Knowledge Cards.").classes("text-sm text-green-300")

        with ui.grid(columns=2).classes("w-full gap-3"):
            with ui.card().classes("ytis-card p-4 w-full"):
                with ui.row().classes("w-full justify-between items-center"):
                    with ui.column().classes("gap-0"):
                        ui.label("YTIS prompt to send to ChatGPT").classes("text-xl font-bold")
                        ui.label("This is generated by YTIS for the current step. Copy it only when you need ChatGPT to produce the answer.").classes("text-xs text-slate-400")
                        ui.label(next_label).classes("text-xs text-cyan-300")
                    if next_step:
                        ui.button("Copy YTIS Prompt", icon="content_copy", on_click=lambda: (_copy_to_clipboard(prompt), ui.notify("YTIS prompt copied", type="positive")), color="primary").props("dense")
                if next_step:
                    prompt_box = ui.textarea(value=prompt).classes("w-full").props("rows=13")
                    prompt_box.style("font-family: Consolas, monospace; font-size: 12px; line-height: 1.3;")
                    with ui.row().classes("gap-1"):
                        ui.button("Copy YTIS Prompt", icon="content_copy", on_click=lambda: (_copy_to_clipboard(prompt_box.value or ""), ui.notify("YTIS prompt copied", type="positive"))).props("outline dense")
                        ui.button("Open ChatGPT", icon="open_in_new", on_click=_open_chatgpt).props("outline dense")
                else:
                    ui.label("All mission steps have saved answers.").classes("text-green-300")

            with ui.card().classes("ytis-card p-4 w-full"):
                with ui.row().classes("w-full justify-between items-center"):
                    with ui.column().classes("gap-0"):
                        ui.label("Paste ChatGPT answer here").classes("text-xl font-bold")
                        ui.label("Do not paste the left prompt here. Paste the answer generated by ChatGPT for this step.").classes("text-xs text-slate-400")
                if next_step:
                    title_default = f"{_get_attr(mission, 'name', 'Mission')} - {next_label}"
                    title_input = ui.input("Title", value=title_default).classes("w-full").props("dense")
                    answer_box = ui.textarea("Paste the full ChatGPT answer for this step here").classes("w-full").props("rows=11")
                    notes_box = ui.textarea("Notes optional").classes("w-full").props("rows=1")
                    status_label = ui.label("Waiting for the ChatGPT answer. Paste it above, then save.").classes("text-xs text-slate-400")

                    def do_save() -> None:
                        text = answer_box.value or ""
                        if not text.strip():
                            ui.notify("Paste the ChatGPT answer in the right panel first", type="warning")
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
                        ui.button("Save ChatGPT Answer and Advance", icon="save", on_click=do_save, color="primary").classes("flex-1")
                        ui.button("Clear", icon="backspace", on_click=lambda: (setattr(answer_box, "value", ""), answer_box.update())).props("outline")
                else:
                    ui.label("No pending step to save.").classes("text-green-300")

        with ui.expansion("Details: lifecycle, sources, saved answers, system", icon="tune", value=False).classes("ytis-card w-full text-white").props("dense"):
            with ui.grid(columns=4).classes("w-full gap-3 p-3"):
                with ui.card().classes("ytis-mini-card p-3 w-full"):
                    ui.label("Mission lifecycle").classes("font-bold")
                    rename_input = ui.input("Rename current mission", value=str(_get_attr(mission, "name", ""))).classes("w-full").props("dense")
                    with ui.row().classes("gap-1"):
                        ui.button(
                            "Rename",
                            icon="edit",
                            on_click=lambda: (
                                _rename_mission(mission, rename_input.value or ""),
                                ui.notify("Mission renamed", type="positive"),
                                ui.timer(0.5, lambda: ui.navigate.to("/"), once=True),
                            ),
                        ).props("outline dense")
                        ui.button(
                            "Archive current",
                            icon="archive",
                            on_click=lambda: (
                                _set_mission_status(mission, "archived"),
                                ui.notify("Mission archived", type="positive"),
                                ui.timer(0.5, lambda: ui.navigate.to("/"), once=True),
                            ),
                        ).props("outline dense")
                    if has_current_duplicates:
                        ui.button(
                            "Archive duplicate missions",
                            icon="cleaning_services",
                            on_click=lambda: (
                                ui.notify(f"Archived {_archive_duplicate_missions(project_root, missions, mission)} duplicate mission(s)", type="positive"),
                                ui.timer(0.5, lambda: ui.navigate.to("/"), once=True),
                            ),
                        ).props("outline dense")
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
                    for record in linked[:5]:
                        title = str(_get_attr(record, "title", "Untitled"))
                        step = str(_get_attr(record, "chain_step", ""))
                        ui.label(title).classes("text-sm font-bold")
                        ui.label(step).classes("text-xs text-slate-400")
                with ui.card().classes("ytis-mini-card p-3 w-full"):
                    ui.label("System").classes("font-bold")
                    ui.label(f"Missions: {stats.get('missions', len(missions))} | Active: {stats.get('active', 0)} | Archived: {stats.get('archived', 0)}").classes("text-sm")
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
