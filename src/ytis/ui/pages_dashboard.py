from __future__ import annotations

import asyncio
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
    "STEP_01_extract_map": "Step 1 - Source credibility and topic map",
    "STEP_02_compare_patterns": "Step 2 - Career and business value extraction",
    "STEP_03_extract_workflows": "Step 3 - Workflows, labs, and operating systems",
    "STEP_04_apply_to_rafael_webify": "Step 4 - Rafael fit, risks, and positioning",
    "STEP_05_validation_plan": "Step 5 - Action roadmap, cards, and next searches",
}

STEP_SHORT_LABELS = {
    "STEP_01_extract_map": "1 Source",
    "STEP_02_compare_patterns": "2 Extract",
    "STEP_03_extract_workflows": "3 Build",
    "STEP_04_apply_to_rafael_webify": "4 Fit",
    "STEP_05_validation_plan": "5 Roadmap",
}

STEP_TO_TOPIC = {
    "STEP_01_extract_map": "Expert/source credibility",
    "STEP_02_compare_patterns": "Career + business",
    "STEP_03_extract_workflows": "Build projects",
    "STEP_04_apply_to_rafael_webify": "Rafael fit",
    "STEP_05_validation_plan": "Study/build roadmap",
}


def _project_root(state: AppState) -> Path:
    return Path(getattr(state, "project_root_path", None) or getattr(state, "project_root", "") or Path.cwd())


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


def _copy_path_and_notify(path: Path, label: str) -> None:
    _copy_to_clipboard(str(path))
    ui.notify(f"{label} created. Path copied to clipboard.", type="positive")


def _export_step_handoff_ui(project_root: Path, mission: Any, downloads_dir: Path, step_id: str | None = None) -> None:
    try:
        from ytis.core.chatgpt_handoff import export_step_handoff
        result = export_step_handoff(
            project_root=project_root,
            mission_id=str(_get_attr(mission, "mission_id", "")),
            downloads_dir=downloads_dir,
            step_id=step_id,
        )
        _copy_path_and_notify(result.zip_path, "ChatGPT step handoff ZIP")
    except Exception as exc:
        ui.notify("Handoff export failed: " + str(exc), type="negative")


def _export_final_pack_ui(project_root: Path, mission: Any, downloads_dir: Path) -> None:
    try:
        from ytis.core.chatgpt_handoff import export_final_action_pack
        result = export_final_action_pack(
            project_root=project_root,
            mission_id=str(_get_attr(mission, "mission_id", "")),
            downloads_dir=downloads_dir,
        )
        _copy_path_and_notify(result.zip_path, "Final action pack ZIP")
    except Exception as exc:
        ui.notify("Final action pack export failed: " + str(exc), type="negative")


def _switch_cockpit_tab(tabs_obj: Any, panels_obj: Any, tab_obj: Any) -> None:
    """Switch dashboard mode tabs from action buttons.

    The Cockpit next-action button should move the user into the in-dashboard
    Mission tab, not only show a toast. This helper is deliberately defensive
    because NiceGUI/Quasar tab objects expose value updates differently across
    versions.
    """
    for obj in (tabs_obj, panels_obj):
        if obj is None:
            continue
        try:
            obj.set_value(tab_obj)
            continue
        except Exception:
            pass
        try:
            obj.value = tab_obj
            obj.update()
        except Exception:
            pass


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


def _latest_project(projects: list[dict[str, Any]]) -> dict[str, Any]:
    return projects[0] if projects else {}


def _project_lookup(projects: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(p.get("name", "")): p for p in projects if isinstance(p, dict) and p.get("name")}


def _knowledge_card_count(project_root: Path, mission: Any | None = None) -> int:
    root = project_root / "knowledge_cards"
    if not root.exists():
        return 0
    metadata_files = list(root.glob("*/metadata.json"))
    if mission is None:
        return len(metadata_files)
    mission_id = str(_get_attr(mission, "mission_id", ""))
    mission_name = str(_get_attr(mission, "name", ""))
    count = 0
    for path in metadata_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if str(data.get("mission_id") or "") == mission_id or str(data.get("mission") or "") == mission_name:
                count += 1
        except Exception:
            pass
    return count


def _research_queue_count(project_root: Path) -> int:
    path = project_root / "ytis_state" / "expert_intelligence" / "research_queue.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else []
        return len(data) if isinstance(data, list) else 0
    except Exception:
        return 0


def _short_goal(text: str, max_chars: int = 170) -> str:
    clean = " ".join((text or "").split())
    return clean if len(clean) <= max_chars else clean[:max_chars].rstrip() + "..."


def _mission_type_config(kind: str) -> dict[str, Any]:
    configs: dict[str, dict[str, Any]] = {
        "Career learning": {
            "icon": "school",
            "focus": "Career learning",
            "name_suffix": "career learning mission",
            "topics": ["Application Support", "Production support", "Troubleshooting", "Logs", "Monitoring", "RCA", "Build projects", "Interview preparation"],
            "goal": "Extract practical career lessons from this YouTube expert/source for Rafael's Application Support Engineer growth. Identify what to study, what to build or document, what workflows matter, what interview talking points can be created, and what should be avoided as overreach.",
        },
        "Business model extraction": {
            "icon": "paid",
            "focus": "Business model extraction",
            "name_suffix": "business model mission",
            "topics": ["Business model", "Monetization", "Offer", "Pricing", "Lead generation", "Workflow", "Niche"],
            "goal": "Analyze how this YouTube expert/source appears to make money. Extract the business model, offer, customer, pricing clues, delivery workflow, acquisition path, proof requirements, risks, and what Rafael could or should not adapt.",
        },
        "Career + business": {
            "icon": "hub",
            "focus": "Career + business",
            "name_suffix": "expert intelligence mission",
            "topics": ["Application Support", "Business model", "Monetization", "Troubleshooting", "Build projects", "Offer", "Rafael fit"],
            "goal": "Extract both career-learning value and business-model value from this YouTube expert/source. Identify skills, workflows, study/build actions, monetization patterns, acquisition clues, credibility signals, hype risks, and Rafael-fit conclusions.",
        },
        "Find better sources": {
            "icon": "radar",
            "focus": "Search discovery",
            "name_suffix": "source discovery mission",
            "topics": ["Search discovery", "Expert/source credibility", "Application Support", "Business model", "Niche"],
            "goal": "Use this source or research goal to generate better YouTube searches, stronger expert-discovery criteria, anti-hype filters, and next-source recommendations for Rafael's career and business learning.",
        },
    }
    return configs.get(kind) or configs["Career learning"]


def _source_ready_text(project: dict[str, Any]) -> str:
    if not project:
        return "No source selected"
    transcripts = _safe_int(project.get("transcripts_created", project.get("_txt_files", 0)))
    words = _safe_int(project.get("total_words", 0))
    status = str(project.get("_hygiene_status") or "").lower()
    zip_value = str(project.get("zip_path") or "").strip()
    zip_ok = bool(zip_value and Path(zip_value).exists())
    if transcripts > 0 and words > 0 and status != "broken" and zip_ok:
        return "Source pack ready"
    if transcripts > 0 and words > 0 and not zip_ok:
        return "Source built but ZIP missing"
    if transcripts > 0:
        return "Source partly ready"
    return "Source needs build"


def _journey_stage(next_step: str, mission: Any | None, project: dict[str, Any], card_count: int) -> int:
    if not project:
        return 1
    if not mission:
        return 2
    if next_step:
        return 3
    if card_count <= 0:
        return 5
    return 6



def _render_cockpit_css() -> None:
    ui.add_head_html("""
    <style>
    :root {
        --ytis-bg: #07111f;
        --ytis-bg-deep: #040a14;
        --ytis-surface: #0d1829;
        --ytis-surface-raised: #111f33;
        --ytis-surface-soft: #16263d;
        --ytis-border: rgba(148, 163, 184, 0.14);
        --ytis-border-strong: rgba(59, 130, 246, 0.36);
        --ytis-text: #e5eef9;
        --ytis-text-secondary: #aab8cc;
        --ytis-text-muted: #71829a;
        --ytis-blue: #3b82f6;
        --ytis-blue-hover: #60a5fa;
        --ytis-blue-soft: rgba(59, 130, 246, 0.15);
        --ytis-green: #22c55e;
        --ytis-green-soft: rgba(34, 197, 94, 0.14);
        --ytis-amber: #f59e0b;
        --ytis-amber-soft: rgba(245, 158, 11, 0.15);
    }
    .ytis-cockpit-page {
        height: calc(100dvh - 88px);
        max-height: calc(100dvh - 88px);
        overflow: hidden;
        padding: 10px 14px 8px 14px;
        box-sizing: border-box;
        color: var(--ytis-text);
        background:
            radial-gradient(circle at 12% 0%, rgba(59, 130, 246, 0.14), transparent 32%),
            linear-gradient(180deg, #07111f 0%, #081322 54%, #050b16 100%);
    }
    .ytis-cockpit-shell {
        height: 100%;
        display: grid;
        grid-template-rows: auto 1fr;
        gap: 8px;
        min-height: 0;
    }
    .ytis-cockpit-header {
        display: grid;
        grid-template-columns: minmax(230px, 300px) minmax(500px, 1fr) minmax(210px, 250px);
        gap: 10px;
        align-items: stretch;
        min-height: 72px;
        max-height: 86px;
    }
    .ytis-cockpit-card {
        background: linear-gradient(180deg, rgba(17,31,51,0.94), rgba(13,24,41,0.96));
        border: 1px solid var(--ytis-border);
        border-radius: 16px;
        min-width: 0;
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.18);
        overflow: hidden;
    }
    .ytis-cockpit-title-card {
        background: linear-gradient(135deg, rgba(29,78,216,0.18), rgba(13,24,41,0.97));
        padding: 12px 14px !important;
    }
    .ytis-cockpit-title-card .ytis-title-main {
        font-size: 20px;
        font-weight: 850;
        line-height: 1;
        color: #f5f9ff;
        letter-spacing: -0.02em;
    }
    .ytis-cockpit-title-card .ytis-title-sub {
        font-size: 10px;
        color: var(--ytis-text-secondary);
        margin-top: 2px;
    }
    .ytis-cockpit-title-card .ytis-title-question {
        font-size: 12px;
        font-weight: 800;
        margin-top: 7px;
        color: var(--ytis-text);
    }

    .ytis-mode-tabs {
        align-self: stretch;
        background: rgba(7,17,31,0.58);
        border: 1px solid var(--ytis-border);
        border-radius: 16px;
        padding: 6px 8px !important;
        min-height: 72px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
    }
    .ytis-mode-tabs .q-tabs__content {
        gap: 8px;
        align-items: center;
        justify-content: center;
    }
    .ytis-mode-tabs .q-tab {
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 12px;
        min-height: 36px;
        height: 36px;
        padding: 0 12px;
        background: rgba(13,24,41,0.78);
        color: var(--ytis-text-secondary);
        text-transform: none;
        min-width: 98px;
        transition: background 150ms ease, border-color 150ms ease, color 150ms ease;
    }
    .ytis-mode-tabs .q-tab:hover {
        border-color: rgba(96,165,250,0.42);
        background: rgba(22,38,61,0.92);
        color: var(--ytis-text);
    }
    .ytis-mode-tabs .q-tab .q-icon { font-size: 16px; margin-right: 5px; color: #93c5fd; }
    .ytis-mode-tabs .q-tab__label { font-size: 11px; font-weight: 800; letter-spacing: .01em; }
    .ytis-mode-tabs .q-tab--active {
        background: linear-gradient(180deg, rgba(59,130,246,0.24), rgba(17,31,51,0.96));
        border-color: rgba(96,165,250,0.58);
        box-shadow: inset 0 -2px 0 var(--ytis-blue-hover), 0 8px 22px rgba(15,23,42,0.28);
        color: #f8fbff;
    }

    .ytis-current-source-card { padding: 11px 13px !important; }
    .ytis-current-source-card .ytis-current-name {
        font-size: 15px;
        font-weight: 800;
        color: #f5f9ff;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .ytis-cockpit-panels { height: 100%; min-height: 0; background: transparent !important; }
    .ytis-cockpit-panels .q-panel { height: 100%; min-height: 0; overflow: hidden; }
    .ytis-cockpit-panels .q-tab-panel { padding: 0; height: 100%; min-height: 0; overflow: hidden; }

    .ytis-focus-grid {
        display: grid;
        grid-template-columns: minmax(330px, 0.95fr) minmax(500px, 1.35fr) minmax(250px, 0.72fr);
        gap: 10px;
        height: 100%;
        min-height: 0;
    }
    .ytis-mode-grid-2 {
        display: grid;
        grid-template-columns: minmax(420px, .95fr) minmax(500px, 1.05fr);
        gap: 10px;
        height: 100%;
        min-height: 0;
    }
    .ytis-mode-column { display: flex; flex-direction: column; gap: 10px; min-height: 0; }
    .ytis-card-fill { flex: 1 1 0; min-height: 0; }
    .ytis-panel-scroll { overflow: auto; min-height: 0; }
    .ytis-compact-card { padding: 12px 14px !important; }
    .ytis-primary-card {
        background: linear-gradient(135deg, rgba(59,130,246,0.20), rgba(17,31,51,0.96));
        border: 1px solid rgba(96,165,250,0.36);
        box-shadow: 0 18px 42px rgba(0,0,0,0.22), inset 0 1px 0 rgba(255,255,255,0.03);
    }
    .ytis-warning-card {
        background: linear-gradient(135deg, rgba(245,158,11,0.14), rgba(17,31,51,0.96));
        border: 1px solid rgba(245,158,11,0.30);
    }

    .ytis-journey-line {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 8px;
        align-items: start;
    }
    .ytis-journey-step { text-align: center; color: var(--ytis-text-muted); font-size: 11px; }
    .ytis-journey-dot {
        margin: 0 auto 5px auto;
        width: 28px;
        height: 28px;
        border-radius: 999px;
        border: 1px solid rgba(148,163,184,0.32);
        background: rgba(7,17,31,0.72);
        display:flex;
        align-items:center;
        justify-content:center;
        font-weight: 800;
        color: var(--ytis-text-secondary);
    }
    .ytis-journey-done .ytis-journey-dot {
        background: rgba(34,197,94,0.22);
        border-color: rgba(34,197,94,0.70);
        color: #dcfce7;
    }
    .ytis-journey-now .ytis-journey-dot {
        background: rgba(59,130,246,0.30);
        border-color: rgba(96,165,250,0.82);
        color: #eff6ff;
    }
    .ytis-journey-title { color: var(--ytis-text); font-weight: 800; font-size: 11px; }

    .ytis-glance-row {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:8px;
        padding: 5px 0;
        border-bottom: 1px solid rgba(148,163,184,0.07);
    }
    .ytis-glance-row:last-child { border-bottom: 0; }
    .ytis-prompt-box textarea,
    .ytis-answer-box textarea {
        font-family: Consolas, monospace;
        font-size: 12px;
        line-height: 1.45;
        color: var(--ytis-text) !important;
        background: rgba(7,17,31,0.94) !important;
    }
    .ytis-compact-description { display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
    .ytis-cockpit-page .q-card { box-sizing: border-box; }
    .ytis-mode-help { color: var(--ytis-text-secondary); font-size:12px; }
    .ytis-small-action-row { display:flex; flex-wrap:wrap; gap:8px; }
    .ytis-small-action-row .q-btn { min-height: 36px; }
    .ytis-mode-headline { font-size: 18px; font-weight: 850; color: #f5f9ff; }
    .ytis-tab-hint { font-size: 12px; color: var(--ytis-text-secondary); }
    .ytis-cockpit-page .q-btn.bg-primary,
    .ytis-cockpit-page .q-btn.bg-blue,
    .ytis-cockpit-page .q-btn.bg-green {
        box-shadow: 0 10px 24px rgba(37,99,235,0.18) !important;
    }
    .ytis-cockpit-page .q-btn[outline],
    .ytis-cockpit-page .q-btn.q-btn--outline {
        color: #bfdbfe !important;
    }


    .ytis-guided-card {
        width: min(1120px, 94vw) !important;
        height: min(760px, calc(100dvh - 118px)) !important;
        max-height: calc(100dvh - 118px) !important;
        display: flex !important;
        flex-direction: column !important;
        overflow: hidden !important;
        background: linear-gradient(180deg, rgba(17,31,51,0.98), rgba(13,24,41,0.99)) !important;
        border: 1px solid rgba(96,165,250,0.22) !important;
        border-radius: 16px !important;
        color: var(--ytis-text) !important;
    }
    .ytis-guided-header {
        flex: 0 0 auto;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(148,163,184,0.12);
    }
    .ytis-guided-body {
        flex: 1 1 auto;
        min-height: 0;
        overflow-y: auto;
        overflow-x: hidden;
        padding-right: 4px;
        scrollbar-gutter: stable;
    }
    .ytis-guided-footer {
        flex: 0 0 auto;
        position: sticky;
        bottom: 0;
        z-index: 4;
        margin-top: 8px;
        padding-top: 10px;
        border-top: 1px solid rgba(148,163,184,0.14);
        background: linear-gradient(180deg, rgba(13,24,41,0.94), rgba(13,24,41,1));
    }
    .ytis-guided-section-title {
        color: #93c5fd;
        font-size: 12px;
        font-weight: 850;
        text-transform: uppercase;
        letter-spacing: .035em;
    }
    .ytis-guided-source-card {
        background: rgba(7,17,31,0.54) !important;
        border: 1px solid rgba(148,163,184,0.14) !important;
        border-radius: 12px !important;
        padding: 12px 14px !important;
        min-height: 160px;
    }
    .ytis-guided-source-card-active {
        border-color: rgba(96,165,250,0.62) !important;
        box-shadow: inset 0 0 0 1px rgba(59,130,246,0.18);
    }
    .ytis-guided-preview {
        background: rgba(7,17,31,0.72) !important;
        border: 1px solid rgba(148,163,184,0.12) !important;
        border-radius: 12px !important;
        padding: 12px 14px !important;
    }

    @media (max-width: 1380px) {
        .ytis-cockpit-header { grid-template-columns: minmax(220px, 280px) 1fr minmax(200px, 230px); }
        .ytis-mode-tabs .q-tab { min-width: 96px; padding: 0 11px; }
        .ytis-mode-tabs .q-tab__label { font-size: 11px; }
        .ytis-focus-grid { grid-template-columns: minmax(300px, .9fr) minmax(430px, 1.25fr) minmax(240px, .75fr); }
    }
    @media (max-width: 1100px) {
        .ytis-cockpit-page { height: auto; max-height: none; overflow: auto; }
        .ytis-cockpit-shell { display:flex; flex-direction:column; }
        .ytis-cockpit-header, .ytis-focus-grid, .ytis-mode-grid-2 { grid-template-columns: 1fr; height: auto; max-height: none; }
        .ytis-mode-tabs { min-height: auto; }
        .ytis-mode-tabs .q-tabs__content { flex-wrap: wrap; }
        .ytis-cockpit-panels .q-tab-panel { overflow: visible; }
    }
    </style>
    """)

def _render_journey(stage: int, project: dict[str, Any], mission: Any | None, next_step: str, card_count: int) -> None:
    steps = [
        ("Source", _source_ready_text(project), "check" if project else "1"),
        ("Mission", "Ready" if mission else "Needed", "2"),
        ("Prompt", "Waiting" if next_step else "Complete", "3"),
        ("Answer", "Needed" if next_step else "Saved", "4"),
        ("Cards", f"{card_count} card(s)" if card_count else "Not created", "5"),
        ("Next", "Roadmap/Search", "6"),
    ]
    ui.label("Journey overview").classes("text-xs font-bold text-blue-300 uppercase")
    with ui.element("div").classes("ytis-journey-line"):
        for index, (title, subtitle, marker) in enumerate(steps, start=1):
            cls = "ytis-journey-step"
            if index < stage:
                cls += " ytis-journey-done"
            elif index == stage:
                cls += " ytis-journey-now"
            with ui.element("div").classes(cls):
                with ui.element("div").classes("ytis-journey-dot"):
                    ui.label(str(marker)).classes("text-xs")
                ui.label(title).classes("ytis-journey-title")
                ui.label(subtitle).classes("text-[11px]")

def _project_by_name(projects: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for project in projects:
        if str(project.get("name", "")).strip() == str(name or "").strip():
            return project
    return {}


def _is_source_ready(project: dict[str, Any]) -> bool:
    if not project:
        return False
    transcripts = _safe_int(project.get("transcripts_created", project.get("_txt_files", 0)))
    words = _safe_int(project.get("total_words", 0))
    status = str(project.get("_hygiene_status") or "").lower()
    zip_value = str(project.get("zip_path") or "").strip()
    zip_ok = bool(zip_value and Path(zip_value).exists())
    return transcripts > 0 and words > 0 and status != "broken" and zip_ok


def _source_detail_text(project: dict[str, Any]) -> str:
    if not project:
        return "No source selected."
    transcripts = _compact(project.get("transcripts_created", project.get("_txt_files", 0)))
    words = _compact(project.get("total_words", 0))
    status = str(project.get("_hygiene_status") or "unknown")
    zip_value = str(project.get("zip_path") or "")
    zip_text = "ZIP ready" if zip_value and Path(zip_value).exists() else "ZIP missing"
    return f"{_source_ready_text(project)} | {transcripts} transcripts | {words} words | {status} | {zip_text}"


def _normalise_compare_token(text: str) -> str:
    return "".join(ch.lower() for ch in str(text or "") if ch.isalnum())


def _url_project_warning(project_name: str, url: str) -> str:
    name_token = _normalise_compare_token(project_name)
    url_token = _normalise_compare_token(url)
    if not name_token or not url_token:
        return ""
    if len(name_token) >= 6 and name_token not in url_token:
        return "Project name does not obviously match the YouTube URL. Check before building."
    return ""


def _render_guided_start_dialog(state: AppState, project_root: Path, projects: list[dict[str, Any]], default_kind: str = "Career learning") -> None:
    project_names = [str(p.get("name", "")) for p in projects if p.get("name")]

    with ui.dialog() as dialog, ui.card().classes("ytis-guided-card"):
        with ui.element("div").classes("ytis-guided-header"):
            ui.label("Start new guided research").classes("text-2xl font-bold")
            ui.label("YTIS will not guess. Choose one objective and one clear source path. The action button always stays visible.").classes("text-sm text-slate-400")

        with ui.element("div").classes("ytis-guided-body"):
            with ui.grid().classes("ytis-grid-2 w-full mt-3"):
                kind = ui.select(
                    ["Career learning", "Business model extraction", "Career + business", "Find better sources"],
                    value=default_kind,
                    label="1. What do you want to do?",
                ).classes("w-full")
                language = ui.select(["en", "es"], value="en", label="Transcript language for a new source").classes("w-full")

            ui.separator().classes("my-3")
            ui.label("2. Choose one source path").classes("ytis-guided-section-title")
            source_mode = ui.radio(
                ["Use existing source project", "Build new source from YouTube URL"],
                value="Use existing source project" if project_names else "Build new source from YouTube URL",
            ).props("inline").classes("text-sm mt-1")

            with ui.grid().classes("ytis-grid-2 w-full mt-2"):
                existing_card = ui.card().classes("ytis-guided-source-card")
                with existing_card:
                    ui.label("Use existing source project").classes("font-bold")
                    existing_project = ui.select(
                        project_names,
                        value=project_names[0] if project_names else None,
                        label="Existing project",
                    ).classes("w-full")
                    existing_summary = ui.label("Select a project to see readiness.").classes("text-xs text-slate-400")

                new_card = ui.card().classes("ytis-guided-source-card")
                with new_card:
                    ui.label("Build new source from YouTube URL").classes("font-bold")
                    url = ui.input("YouTube channel/video URL", placeholder="https://www.youtube.com/@vishakha.sadhwani/videos").props("debounce=0").classes("w-full")
                    project_name = ui.input("New project name", placeholder="VishakhaSadhwani").props("debounce=0").classes("w-full")
                    overwrite_confirm = ui.checkbox("Project already exists; reuse/refresh it intentionally.", value=False)
                    overwrite_confirm.visible = False
                    new_source_warning = ui.label("").classes("text-xs text-amber-300")

            ui.separator().classes("my-3")
            ui.label("3. Mission preview").classes("ytis-guided-section-title")
            with ui.element("div").classes("ytis-guided-preview mt-2"):
                mission_name = ui.input("Mission name").props("debounce=0").classes("w-full")
                mission_name_preview = ui.label("Mission name preview: -").classes("text-xs text-blue-300")
                goal = ui.textarea("Mission goal").classes("w-full").props("rows=3")
                topics_preview = ui.label("").classes("text-xs text-slate-400")
                source_preview = ui.label("").classes("text-xs text-slate-400")
                status = ui.label("Ready. Pick one source path. YTIS will block unsafe combinations.").classes("text-xs text-slate-400")

        def selected_source_name() -> str:
            if source_mode.value == "Use existing source project":
                return str(existing_project.value or "").strip()
            return str(project_name.value or "").strip()

        def selected_source_project() -> dict[str, Any]:
            return _project_by_name(projects, selected_source_name())

        def set_status(message: str, color_class: str = "text-slate-400") -> None:
            status.text = message
            status.classes(remove="text-slate-400 text-blue-300 text-green-300 text-amber-300 text-red-300")
            status.classes(add=color_class)
            status.update()

        def refresh_preview() -> None:
            cfg = _mission_type_config(str(kind.value or "Career learning"))
            mode = str(source_mode.value or "Use existing source project")
            source_name = selected_source_name()
            preview_source_name = source_name or ("Selected expert" if mode == "Use existing source project" else "New source")
            computed_mission_name = f"{preview_source_name} - {cfg['name_suffix']}"
            mission_name.value = computed_mission_name
            mission_name_preview.text = "Mission name preview: " + computed_mission_name
            goal.value = cfg["goal"]
            topics_preview.text = "Topics: " + ", ".join(cfg["topics"])

            if mode == "Use existing source project":
                project = selected_source_project()
                existing_summary.text = _source_detail_text(project) if project else "No existing project selected."
                source_preview.text = "Source: existing project " + (source_name or "-")
                overwrite_confirm.visible = False
                new_source_warning.text = ""
                existing_card.visible = True
                new_card.visible = False
                existing_card.classes(add="ytis-guided-source-card-active")
                new_card.classes(remove="ytis-guided-source-card-active")
                set_status("Ready. Existing source mode requires a source pack that is already ZIP-ready.")
            else:
                project = selected_source_project()
                warning_parts = []
                if project:
                    if _is_source_ready(project):
                        warning_parts.append("A ZIP-ready project with this name already exists.")
                        overwrite_confirm.visible = True
                    else:
                        warning_parts.append("An incomplete project with this name exists. YTIS will repair/rebuild it before creating a mission.")
                        overwrite_confirm.visible = False
                else:
                    overwrite_confirm.visible = False
                mismatch = _url_project_warning(source_name, str(url.value or ""))
                if mismatch:
                    warning_parts.append(mismatch)
                new_source_warning.text = " ".join(warning_parts)
                source_preview.text = "Source: build new YouTube source " + (source_name or "-")
                existing_card.visible = False
                new_card.visible = True
                existing_card.classes(remove="ytis-guided-source-card-active")
                new_card.classes(add="ytis-guided-source-card-active")
                if warning_parts:
                    set_status("Warning: " + " ".join(warning_parts), "text-amber-300")
                else:
                    set_status("Ready. New source mode requires a YouTube URL and a project name before mission creation.")

            for item in [mission_name, mission_name_preview, goal, topics_preview, source_preview, existing_summary, new_source_warning, overwrite_confirm, existing_card, new_card]:
                item.update()

        def validate_existing_source() -> tuple[bool, str, dict[str, Any]]:
            source_name = selected_source_name()
            if not source_name:
                return False, "Select an existing source project.", {}
            project = selected_source_project()
            if not project:
                return False, f"Existing project not found: {source_name}", {}
            if not _is_source_ready(project):
                return False, "Selected source is not ZIP-ready. Use Sources/Build or Inspector first.", project
            return True, "", project

        def validate_new_source() -> tuple[bool, str]:
            source_name = selected_source_name()
            source_url = str(url.value or "").strip()
            if not source_url:
                return False, "Paste the YouTube channel/video URL for the new source."
            if not source_name:
                return False, "Enter a project name for this YouTube source."
            existing = selected_source_project()
            if existing and _is_source_ready(existing) and not overwrite_confirm.value:
                return False, "This project name already exists and is ZIP-ready. Tick the confirmation box if you intentionally want to reuse/refresh it."
            return True, ""

        async def create_from_dialog() -> None:
            refresh_preview()
            cfg = _mission_type_config(str(kind.value or "Career learning"))
            source_name = selected_source_name()
            source_url = str(url.value or "").strip()
            mode = str(source_mode.value or "Use existing source project")
            project_record: dict[str, Any] = {}
            previous_project = dict(getattr(state, "current_project", {}) or {})

            try:
                if mode == "Use existing source project":
                    ok, message, project_record = validate_existing_source()
                    if not ok:
                        ui.notify(message, type="warning")
                        set_status(message, "text-amber-300")
                        return
                else:
                    ok, message = validate_new_source()
                    if not ok:
                        ui.notify(message, type="warning")
                        set_status(message, "text-amber-300")
                        return
                    mismatch = _url_project_warning(source_name, source_url)
                    if mismatch:
                        set_status("Warning: " + mismatch + " YTIS will continue only if the build produces a ZIP-ready source.", "text-amber-300")
                    from ytis.core.builder import BuildOptions, build_research_pack
                    from ytis.core.project_hygiene import audit_projects
                    set_status("Building or repairing source pack. The mission will be created only after ZIP readiness is verified.", "text-blue-300")
                    options = BuildOptions(
                        name=source_name,
                        url=source_url,
                        lang=language.value or "en",
                        output_downloads=state.downloads_dir,
                        base_projects_dir=state.projects_dir(),
                        mode="reuse",
                    )
                    result = await asyncio.to_thread(build_research_pack, options, lambda message, percent=None: None)
                    if _safe_int(result.transcripts_created) <= 0 or _safe_int(result.total_words) <= 0:
                        raise RuntimeError("Source build finished but no usable transcripts/words were created. No mission was created.")
                    if not Path(result.zip_path).exists():
                        raise RuntimeError("Source build did not create the research ZIP. No mission was created: " + str(result.zip_path))

                    refreshed_projects = audit_projects(state.load_projects())
                    project_record = _project_by_name(refreshed_projects, source_name) or {
                        "name": source_name,
                        "url": source_url,
                        "language": language.value or "en",
                        "build_mode": result.mode,
                        "videos_found": result.videos_found,
                        "transcripts_created": result.transcripts_created,
                        "missing_subtitles": result.missing_subtitles,
                        "total_words": result.total_words,
                        "zip_path": str(result.zip_path),
                        "project_dir": str(result.project_dir),
                    }
                    if not _is_source_ready(project_record):
                        detail = _source_detail_text(project_record)
                        raise RuntimeError("Source is not ZIP-ready after build. No mission was created. " + detail)

                if not _is_source_ready(project_record):
                    raise RuntimeError("Selected source is not ZIP-ready. No mission was created. " + _source_detail_text(project_record))

                from ytis.core.missions import create_mission
                final_mission_name = str(mission_name.value or "").strip() or f"{source_name} - {cfg['name_suffix']}"
                mission = create_mission(
                    project_root=project_root,
                    name=final_mission_name,
                    goal=goal.value or cfg["goal"],
                    focus_preset=cfg["focus"],
                    projects=[source_name],
                    topics=list(cfg["topics"]),
                )
                state.set_current_project(project_record)
                _write_current_mission_id(project_root, str(_get_attr(mission, "mission_id", "")))
                ui.notify("Guided mission created. Upload the evidence ZIP before sending Step 1.", type="positive")
                dialog.close()
                ui.timer(0.7, lambda: ui.navigate.to("/"), once=True)
            except Exception as exc:
                state.set_current_project(previous_project)
                set_status("Start failed: " + str(exc), "text-red-300")
                ui.notify("Could not start guided research: " + str(exc), type="negative")

        for control in [kind, source_mode, existing_project, project_name, url, language]:
            control.on("update:model-value", lambda e: refresh_preview())
            control.on("input", lambda e: refresh_preview())
            control.on("keyup", lambda e: refresh_preview())
            control.on("blur", lambda e: refresh_preview())
        # One delayed refresh catches browser/autofill and Playwright fill operations that update
        # the input value before NiceGUI emits update:model-value. This keeps the visible
        # mission preview synced with the project field without creating a mission.
        ui.timer(0.35, refresh_preview, once=True)
        refresh_preview()

        with ui.element("div").classes("ytis-guided-footer"):
            with ui.row().classes("w-full justify-between items-center gap-2"):
                ui.label("Safe rule: YTIS creates the mission only after one source path is clear and ready.").classes("text-xs text-slate-400")
                with ui.row().classes("gap-2"):
                    ui.button("Cancel", on_click=dialog.close).props("outline")
                    ui.button("Continue Guided Research", icon="rocket_launch", on_click=create_from_dialog, color="primary")
    dialog.open()

def _render_stat_rows(project_root: Path, project: dict[str, Any], mission: Any | None, linked: list[Any], card_count: int, queue_count: int) -> None:
    transcripts = _safe_int(project.get("transcripts_created", project.get("_txt_files", 0))) if project else 0
    words = _safe_int(project.get("total_words", 0)) if project else 0
    rows = [
        ("Transcripts", _compact(transcripts), "article"),
        ("Total words", _compact(words), "notes"),
        ("Analyses saved", _compact(len(linked)), "save"),
        ("Knowledge cards", _compact(card_count), "category"),
        ("Research queries", _compact(queue_count), "search"),
    ]
    for label, value, icon in rows:
        with ui.row().classes("ytis-glance-row"):
            with ui.row().classes("items-center gap-2"):
                ui.icon(icon).classes("text-blue-400")
                ui.label(label).classes("text-sm text-slate-300")
            ui.label(value).classes("text-sm font-bold")


def _render_prompt_loop(project_root: Path, downloads_dir: Path, mission: Any | None, selected_projects: list[dict[str, Any]], next_step: str, next_label: str) -> None:
    if not mission:
        with ui.card().classes("ytis-cockpit-card p-5 h-full"):
            ui.label("No mission selected").classes("text-xl font-bold")
            ui.label("Create a guided mission from Cockpit or Sources. Advanced mission management is still available.").classes("text-sm text-slate-400")
            ui.button("Open Mission Manager", icon="flag", on_click=lambda: ui.navigate.to("/missions")).props("outline")
        return
    if not next_step:
        with ui.card().classes("ytis-cockpit-card p-5 h-full"):
            ui.label("Mission complete").classes("text-xl font-bold")
            ui.label("All mission steps have saved answers.").classes("text-green-300 mt-2")
            ui.label("Next: create cards, build a roadmap, or search for stronger sources.").classes("text-sm text-slate-300")
            with ui.row().classes("gap-2 mt-4"):
                ui.button("Export Final Pack", icon="archive", on_click=lambda: _export_final_pack_ui(project_root, mission, downloads_dir), color="primary")
                ui.button("Knowledge Cards", icon="category", on_click=lambda: ui.navigate.to("/knowledge")).props("outline")
                ui.button("Analysis Library", icon="move_to_inbox", on_click=lambda: ui.navigate.to("/analysis-library")).props("outline")
        return
    prompt = _prompt_for_analysis_step(mission, selected_projects, next_step)
    zip_paths = [str(p.get("zip_path") or "") for p in selected_projects if isinstance(p, dict) and p.get("zip_path")]
    evidence_zip = zip_paths[0] if zip_paths else ""
    with ui.card().classes("ytis-cockpit-card p-4 h-full"):
        ui.label(next_label).classes("text-xs font-bold text-blue-300 uppercase")
        with ui.row().classes("items-center justify-between gap-2 bg-slate-950/35 border border-blue-500/20 rounded-lg px-3 py-2 mb-2"):
            with ui.column().classes("gap-0 min-w-0"):
                ui.label("Evidence first").classes("text-xs font-bold text-blue-300 uppercase")
                if evidence_zip:
                    ui.label("Upload the source pack ZIP to ChatGPT before sending this prompt.").classes("text-xs text-slate-300")
                    ui.label(evidence_zip).classes("text-[11px] text-slate-500 truncate")
                else:
                    ui.label("No source pack ZIP found for this mission. Open Sources/Library before running the prompt.").classes("text-xs text-amber-300")
            with ui.row().classes("gap-2"):
                ui.button("Export Step ZIP", icon="archive", on_click=lambda: _export_step_handoff_ui(project_root, mission, downloads_dir, next_step), color="primary").props("dense")
                ui.button("Open ChatGPT", icon="open_in_new", on_click=_open_chatgpt).props("outline dense")
                if evidence_zip:
                    ui.button("Copy ZIP path", icon="content_copy", on_click=lambda: (_copy_to_clipboard(evidence_zip), ui.notify("Evidence ZIP path copied", type="positive"))).props("outline dense")
        with ui.grid().style("grid-template-columns: 1fr 1fr; gap: 12px; height: calc(100% - 78px); min-height: 0;").classes("w-full"):
            with ui.column().classes("gap-2 min-h-0"):
                ui.label("Prompt to send to ChatGPT").classes("text-sm text-blue-300")
                prompt_box = ui.textarea(value=prompt).classes("ytis-prompt-box w-full flex-1").props("readonly")
                prompt_box.style("height: 100%; min-height: 230px;")
                with ui.row().classes("gap-2"):
                    ui.button("Copy Prompt", icon="content_copy", on_click=lambda: (_copy_to_clipboard(prompt), ui.notify("Prompt copied", type="positive"))).props("outline dense")
                    ui.button("Export Handoff", icon="archive", on_click=lambda: _export_step_handoff_ui(project_root, mission, downloads_dir, next_step)).props("outline dense")
            with ui.column().classes("gap-2 min-h-0"):
                ui.label("Paste ChatGPT answer here").classes("text-sm text-blue-300")
                answer_box = ui.textarea(placeholder="Paste the answer from ChatGPT...").classes("ytis-answer-box w-full flex-1")
                answer_box.style("height: 100%; min-height: 230px;")
                status_label = ui.label("Waiting for answer.").classes("text-xs text-slate-400")
                def do_save() -> None:
                    text = answer_box.value or ""
                    if not text.strip():
                        ui.notify("Paste the ChatGPT answer first", type="warning")
                        return
                    try:
                        from ytis.core.chatgpt_handoff import save_chatgpt_answer
                        result = save_chatgpt_answer(
                            project_root=project_root,
                            mission_id=str(_get_attr(mission, "mission_id", "")),
                            answer_text=text,
                            chain_step=next_step,
                            source_evidence_pack=evidence_zip,
                        )
                        status_label.text = f"Saved: {result.record_id}"
                        status_label.classes(remove="text-slate-400")
                        status_label.classes(add="text-green-400")
                        status_label.update()
                        if result.all_steps_complete:
                            ui.notify("Saved. Mission completed.", type="positive")
                        else:
                            ui.notify("Saved and advanced", type="positive")
                        ui.timer(0.7, lambda: ui.navigate.to("/"), once=True)
                    except Exception as exc:
                        ui.notify("Save failed: " + str(exc), type="negative")
                ui.button("Save Answer & Advance", icon="arrow_forward", on_click=do_save, color="primary").classes("w-full")


def _render_dashboard_body(state: AppState) -> None:
    _render_cockpit_css()
    project_root = _project_root(state)
    runtime = _load_runtime(project_root, state)
    missions = runtime.get("missions", [])
    records = runtime.get("records", [])
    projects = runtime.get("projects", [])
    mission = _select_current_mission(project_root, missions)
    selected_projects = _selected_project_records(mission, projects) if mission else []
    project = selected_projects[0] if selected_projects else _latest_project(projects)
    linked = _mission_records(records, mission) if mission else []
    progress = _progress_for_mission(records, mission) if mission else {step: 0 for step in CHAIN_ORDER}
    next_step = _next_pending_step(progress) if mission else ""
    next_label = STEP_LABELS_FALLBACK.get(next_step, next_step) if next_step else "Mission complete"
    done = _done_count(progress)
    card_count = _knowledge_card_count(project_root, mission) if mission else _knowledge_card_count(project_root)
    total_cards = _knowledge_card_count(project_root)
    queue_count = _research_queue_count(project_root)
    stage = _journey_stage(next_step, mission, project, card_count)
    transcripts = _safe_int(project.get("transcripts_created", project.get("_txt_files", 0))) if project else 0
    words = _safe_int(project.get("total_words", 0)) if project else 0

    if not project:
        next_title = "Start with a source"
        next_body = "Add public-safe source material or choose an existing source so YTIS has evidence to analyze. YouTube transcript packs are the first supported input."
        next_button = ("Start guided research", "rocket_launch", lambda: _render_guided_start_dialog(state, project_root, projects, "Career learning"))
        secondary_buttons = [("Open Sources", "folder", lambda: ui.navigate.to("/build"))]
    elif not mission:
        next_title = "Create a guided mission"
        next_body = "The source is ready. Choose what you want to learn or analyze and YTIS will create the right mission."
        next_button = ("Create mission", "flag", lambda: _render_guided_start_dialog(state, project_root, projects, "Career + business"))
        secondary_buttons = [("Sources", "folder", lambda: ui.notify("Use the Sources tab above", type="info"))]
    elif next_step:
        next_title = "Send the next prompt to ChatGPT"
        next_body = "Export the step handoff ZIP, upload it to ChatGPT, then paste the answer back in the Mission tab."
        next_button = ("Open Mission tab", "flag", lambda: ui.notify("Use the Mission tab above", type="info"))
        secondary_buttons = [("Export handoff ZIP", "archive", lambda: _export_step_handoff_ui(project_root, mission, state.downloads_dir, next_step)), ("Copy current prompt", "content_copy", lambda: (_copy_to_clipboard(_prompt_for_analysis_step(mission, selected_projects, next_step)), ui.notify("Prompt copied", type="positive")))]
    elif card_count <= 0:
        next_title = "Create Knowledge Cards"
        next_body = "The mission is complete. Convert the useful lessons into reusable cards before moving on."
        next_button = ("Open Knowledge", "category", lambda: ui.navigate.to("/knowledge"))
        secondary_buttons = [("Saved analyses", "move_to_inbox", lambda: ui.navigate.to("/analysis-library"))]
    else:
        next_title = "Start the next research loop"
        next_body = "Knowledge is captured. Start a new expert mission, build a roadmap, or search for stronger sources."
        next_button = ("Start next research", "rocket_launch", lambda: _render_guided_start_dialog(state, project_root, projects, "Career learning"))
        secondary_buttons = [("Find sources", "radar", lambda: ui.navigate.to("/research-radar")), ("Open cards", "category", lambda: ui.navigate.to("/knowledge"))]

    with ui.element("div").classes("ytis-cockpit-page"):
        with ui.element("div").classes("ytis-cockpit-shell"):
            with ui.element("div").classes("ytis-cockpit-header"):
                with ui.card().classes("ytis-cockpit-card ytis-cockpit-title-card"):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("construction").classes("text-2xl text-blue-400")
                        with ui.column().classes("gap-0 min-w-0"):
                            ui.label("YTIS").classes("ytis-title-main")
                            ui.label("Local AI Source Intelligence OS").classes("ytis-title-sub")
                    ui.label("What are you working on today?").classes("ytis-title-question")
                    ui.label("One screen. One next action. Advanced tools stay in the sidebar.").classes("ytis-title-sub")

                with ui.tabs().classes("ytis-mode-tabs w-full") as tabs:
                    cockpit_tab = ui.tab("Cockpit", icon="home")
                    sources_tab = ui.tab("Sources", icon="folder")
                    mission_tab = ui.tab("Mission", icon="flag")
                    discovery_tab = ui.tab("Discovery", icon="radar")
                    knowledge_tab = ui.tab("Knowledge", icon="category")
                    evidence_tab = ui.tab("Evidence", icon="hub")

                with ui.card().classes("ytis-cockpit-card ytis-current-source-card"):
                    ui.label("Current project").classes("text-xs text-slate-400")
                    ui.label(str(project.get("name", "No source selected")) if project else "No source selected").classes("ytis-current-name")
                    ui.label(_source_ready_text(project)).classes("text-xs text-green-300" if project else "text-xs text-orange-300")
                    ui.label(f"YTIS {state.app_version}").classes("text-xs text-slate-500 mt-2")

            with ui.tab_panels(tabs, value=cockpit_tab).classes("ytis-cockpit-panels w-full") as panels:
                with ui.tab_panel(cockpit_tab):
                    with ui.element("div").classes("ytis-focus-grid"):
                        with ui.element("div").classes("ytis-mode-column"):
                            with ui.card().classes("ytis-cockpit-card ytis-primary-card ytis-compact-card"):
                                ui.label("Next action").classes("text-xs font-bold text-green-300 uppercase")
                                ui.label(next_title).classes("text-xl font-bold")
                                ui.label(next_body).classes("text-xs text-slate-300")
                                label, icon, handler = next_button
                                if str(label).lower().startswith("open mission"):
                                    ui.button(label, icon=icon, on_click=lambda: _switch_cockpit_tab(tabs, panels, mission_tab), color="positive").classes("mt-2")
                                else:
                                    ui.button(label, icon=icon, on_click=handler, color="positive").classes("mt-2")
                                if secondary_buttons:
                                    with ui.row().classes("ytis-small-action-row mt-2"):
                                        for s_label, s_icon, s_handler in secondary_buttons:
                                            ui.button(s_label, icon=s_icon, on_click=s_handler).props("outline dense")

                            with ui.card().classes("ytis-cockpit-card ytis-compact-card ytis-card-fill"):
                                ui.label("Current mission").classes("text-xs font-bold text-blue-300 uppercase")
                                if mission:
                                    ui.label(str(_get_attr(mission, "name", "Untitled mission"))).classes("text-lg font-bold")
                                    with ui.row().classes("items-center gap-2"):
                                        ui.badge(str(_get_attr(mission, "focus_preset", "Custom") or "Custom"), color="blue")
                                        step_text = f"Step {done} of 5"
                                        if next_step and done <= 0:
                                            step_text = "Step 1 pending"
                                        elif next_step:
                                            step_text = f"Step {done + 1} pending"
                                        ui.label(step_text).classes("text-xs text-slate-400")
                                    ui.label(_short_goal(str(_get_attr(mission, "goal", "")), 170)).classes("ytis-compact-description text-xs text-slate-300 mt-2")
                                else:
                                    ui.label("No mission yet.").classes("text-sm text-slate-400")
                                    ui.button("Start guided mission", icon="rocket_launch", on_click=lambda: _render_guided_start_dialog(state, project_root, projects, "Career learning")).props("outline")

                        with ui.element("div").classes("ytis-mode-column"):
                            with ui.card().classes("ytis-cockpit-card ytis-compact-card"):
                                _render_journey(stage, project, mission, next_step, card_count)
                            with ui.card().classes("ytis-cockpit-card ytis-compact-card ytis-card-fill"):
                                ui.label("Guided workflow").classes("text-xs font-bold text-blue-300 uppercase")
                                ui.label("Use the mode tabs above instead of navigating through internal pages.").classes("text-sm text-slate-300")
                                with ui.grid().style("grid-template-columns: 1fr 1fr; gap: 8px;").classes("mt-3"):
                                    ui.button("Study an expert", icon="school", on_click=lambda: _render_guided_start_dialog(state, project_root, projects, "Career learning")).props("outline")
                                    ui.button("Analyze business", icon="paid", on_click=lambda: _render_guided_start_dialog(state, project_root, projects, "Business model extraction")).props("outline")
                                    ui.button("Career + business", icon="hub", on_click=lambda: _render_guided_start_dialog(state, project_root, projects, "Career + business")).props("outline")
                                    ui.button("Find sources", icon="radar", on_click=lambda: _render_guided_start_dialog(state, project_root, projects, "Find better sources")).props("outline")
                                ui.separator().classes("my-3")
                                ui.label("Focus rule").classes("text-xs font-bold text-slate-400 uppercase")
                                ui.label("Sidebar stays collapsible. The cockpit remains the normal workflow.").classes("text-sm text-slate-300")

                        with ui.element("div").classes("ytis-mode-column"):
                            with ui.card().classes("ytis-cockpit-card ytis-compact-card"):
                                ui.label("At a glance").classes("text-xs font-bold text-blue-300 uppercase")
                                _render_stat_rows(project_root, project, mission, linked, card_count or total_cards, queue_count)
                            with ui.card().classes("ytis-cockpit-card ytis-compact-card ytis-card-fill"):
                                ui.label("Advanced access").classes("text-xs font-bold text-blue-300 uppercase")
                                ui.label("Use only when the cockpit cannot answer your question.").classes("text-sm text-slate-400")
                                with ui.grid().style("grid-template-columns: 1fr 1fr; gap: 6px;").classes("mt-3"):
                                    for label, path, icon in [("Build", "/build", "construction"), ("Missions", "/missions", "flag"), ("Search", "/search", "search"), ("Health", "/health", "monitor_heart")]:
                                        ui.button(label, icon=icon, on_click=lambda p=path: ui.navigate.to(p)).props("outline dense")

                with ui.tab_panel(sources_tab):
                    with ui.element("div").classes("ytis-mode-grid-2"):
                        with ui.card().classes("ytis-cockpit-card ytis-compact-card"):
                            ui.label("Sources").classes("ytis-mode-headline")
                            ui.label("Question: Is the source evidence ready?").classes("ytis-tab-hint")
                            if project:
                                ui.label(str(project.get("name", "Unnamed"))).classes("text-xl font-bold mt-3")
                                ui.label(_source_ready_text(project)).classes("text-green-300")
                                ui.label(f"Transcripts: {_compact(transcripts)} | Words: {_compact(words)}").classes("text-sm text-slate-300")
                            else:
                                ui.label("No source selected yet.").classes("text-orange-300 mt-4")
                            with ui.row().classes("ytis-small-action-row mt-4"):
                                ui.button("Start guided research", icon="rocket_launch", on_click=lambda: _render_guided_start_dialog(state, project_root, projects, "Career learning"), color="primary")
                                ui.button("Manual build", icon="construction", on_click=lambda: ui.navigate.to("/build")).props("outline")
                                ui.button("Library", icon="folder", on_click=lambda: ui.navigate.to("/library")).props("outline")
                        with ui.card().classes("ytis-cockpit-card ytis-compact-card ytis-panel-scroll"):
                            ui.label("Available source projects").classes("ytis-mode-headline")
                            for p in projects[:12]:
                                with ui.row().classes("w-full justify-between items-center py-1"):
                                    ui.label(str(p.get("name", "Unnamed"))).classes("font-bold")
                                    ui.label(f"{_compact(p.get('transcripts_created', 0))} transcripts").classes("text-xs text-slate-400")

                with ui.tab_panel(mission_tab):
                    _render_prompt_loop(project_root, state.downloads_dir, mission, selected_projects, next_step, next_label)

                with ui.tab_panel(discovery_tab):
                    with ui.element("div").classes("ytis-mode-grid-2"):
                        with ui.card().classes("ytis-cockpit-card ytis-compact-card"):
                            ui.label("Discovery").classes("ytis-mode-headline")
                            ui.label("Question: What should I search next?").classes("ytis-tab-hint")
                            ui.label("Generate search campaigns, evaluate experts, and bring the strongest source back into Sources.").classes("text-sm text-slate-300 mt-2")
                            with ui.row().classes("ytis-small-action-row mt-4"):
                                ui.button("Research Radar", icon="radar", on_click=lambda: ui.navigate.to("/research-radar"), color="primary")
                                ui.button("Analyze Expert", icon="psychology", on_click=lambda: ui.navigate.to("/expert-intelligence")).props("outline")
                                ui.button("Start from source", icon="rocket_launch", on_click=lambda: _render_guided_start_dialog(state, project_root, projects, "Career + business")).props("outline")
                        with ui.card().classes("ytis-cockpit-card ytis-compact-card"):
                            ui.label("Research queue").classes("ytis-mode-headline")
                            ui.label(f"Saved queries: {_compact(queue_count)}").classes("text-green-300")
                            ui.label("Next: choose one strong public-safe source, then start a guided mission.").classes("text-sm text-slate-300 mt-2")

                with ui.tab_panel(knowledge_tab):
                    with ui.element("div").classes("ytis-mode-grid-2"):
                        with ui.card().classes("ytis-cockpit-card ytis-compact-card"):
                            ui.label("Knowledge").classes("ytis-mode-headline")
                            ui.label("Question: What have I learned and saved?").classes("ytis-tab-hint")
                            ui.label(f"Knowledge cards: {_compact(total_cards)}").classes("text-green-300 mt-3")
                            ui.label(f"Cards linked to current mission: {_compact(card_count)}").classes("text-sm text-slate-300")
                            with ui.row().classes("ytis-small-action-row mt-4"):
                                ui.button("Knowledge Cards", icon="category", on_click=lambda: ui.navigate.to("/knowledge"), color="primary")
                                ui.button("Saved Analyses", icon="move_to_inbox", on_click=lambda: ui.navigate.to("/analysis-library")).props("outline")
                        with ui.card().classes("ytis-cockpit-card ytis-compact-card"):
                            ui.label("Next knowledge actions").classes("ytis-mode-headline")
                            for item in ["Create learning roadmap from cards.", "Create business model cards from expert analysis.", "Export action pack for ChatGPT review."]:
                                ui.label("- " + item).classes("text-sm text-slate-300 mt-1")

                with ui.tab_panel(evidence_tab):
                    with ui.element("div").classes("ytis-mode-grid-2"):
                        with ui.card().classes("ytis-cockpit-card ytis-compact-card"):
                            ui.label("Evidence").classes("ytis-mode-headline")
                            ui.label("Question: Where is the proof?").classes("ytis-tab-hint")
                            ui.label("Search and inspect transcripts, topic evidence, and saved analyses.").classes("text-sm text-slate-300 mt-2")
                            with ui.row().classes("ytis-small-action-row mt-4"):
                                ui.button("Search", icon="search", on_click=lambda: ui.navigate.to("/search"), color="primary")
                                ui.button("Viewer", icon="article", on_click=lambda: ui.navigate.to("/viewer")).props("outline")
                                ui.button("Evidence Explorer", icon="hub", on_click=lambda: ui.navigate.to("/intelligence")).props("outline")
                        with ui.card().classes("ytis-cockpit-card ytis-compact-card"):
                            ui.label("Current evidence base").classes("ytis-mode-headline")
                            ui.label(f"Project: {str(project.get('name', 'No source')) if project else 'No source'}").classes("font-bold")
                            ui.label(f"Transcripts: {_compact(transcripts)}").classes("text-sm text-slate-300")
                            ui.label(f"Total words: {_compact(words)}").classes("text-sm text-slate-300")
                            ui.label(f"Saved analyses: {_compact(len(records))}").classes("text-sm text-slate-300")

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


