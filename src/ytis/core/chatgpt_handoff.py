from __future__ import annotations

import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ytis.core.analysis_inbox import CHAIN_STEP_LABELS, read_analysis, save_analysis, list_analyses
from ytis.core.io_utils import atomic_write_json, atomic_write_text, now_stamp, now_text, safe_slug
from ytis.core.missions import CHAIN_STEPS, Mission, generate_prompt_chain, list_missions, save_mission, selected_project_records
from ytis.core.registry import read_project_summaries

CHAIN_ORDER = [f"STEP_{idx:02d}_{step['name']}" for idx, step in enumerate(CHAIN_STEPS, start=1)]


@dataclass(frozen=True)
class HandoffResult:
    zip_path: Path
    folder: Path
    mission_id: str
    mission_name: str
    step_id: str
    step_label: str
    included_research_packs: list[Path]
    previous_answers: list[Path]
    report_path: Path


@dataclass(frozen=True)
class SaveAnswerResult:
    record_id: str
    chain_step: str
    chain_step_label: str
    all_steps_complete: bool
    mission_status: str


@dataclass(frozen=True)
class FinalPackResult:
    zip_path: Path
    folder: Path
    mission_id: str
    mission_name: str
    saved_answers: int
    card_candidates_path: Path
    report_path: Path


def _load_mission(project_root: Path, mission_id: str) -> Mission:
    for mission in list_missions(project_root):
        if mission.mission_id == mission_id:
            return mission
    raise RuntimeError(f"Mission not found: {mission_id}")


def _step_title(step_id: str) -> str:
    return CHAIN_STEP_LABELS.get(step_id, step_id)


def _mission_records(project_root: Path, mission_id: str) -> list[Any]:
    records = [r for r in list_analyses(project_root) if str(getattr(r, "mission_id", "")) == mission_id]
    order_index = {step: idx for idx, step in enumerate(CHAIN_ORDER)}
    return sorted(
        records,
        key=lambda r: (
            order_index.get(str(getattr(r, "chain_step", "")), 999),
            str(getattr(r, "created_at", "")),
            str(getattr(r, "record_id", "")),
        ),
    )


def mission_progress(project_root: Path, mission_id: str) -> dict[str, int]:
    progress = {step: 0 for step in CHAIN_ORDER}
    for record in _mission_records(project_root, mission_id):
        step = str(getattr(record, "chain_step", ""))
        if step in progress:
            progress[step] += 1
    progress["Total"] = sum(progress.values())
    return progress


def next_pending_step(project_root: Path, mission_id: str) -> str:
    progress = mission_progress(project_root, mission_id)
    for step in CHAIN_ORDER:
        if progress.get(step, 0) <= 0:
            return step
    return ""


def all_steps_complete(project_root: Path, mission_id: str) -> bool:
    return next_pending_step(project_root, mission_id) == ""


def complete_mission_if_ready(project_root: Path, mission_id: str) -> bool:
    mission = _load_mission(project_root, mission_id)
    if not all_steps_complete(project_root, mission_id):
        return False
    if mission.status != "completed":
        mission.status = "completed"
        save_mission(mission)
    return True


def _projects_for_mission(project_root: Path, mission: Mission) -> list[dict[str, Any]]:
    return selected_project_records(mission, read_project_summaries(project_root / "projects"))


def _prompt_for_step(mission: Mission, projects: list[dict[str, Any]], step_id: str) -> str:
    chain = generate_prompt_chain(mission, projects)
    for candidate_step_id, (_, prompt) in zip(CHAIN_ORDER, chain):
        if candidate_step_id == step_id:
            return prompt
    return ""


def _copy_if_exists(src_value: Any, destination_dir: Path, prefix: str = "") -> Path | None:
    if not src_value:
        return None
    src = Path(str(src_value))
    if not src.exists() or not src.is_file():
        return None
    destination_dir.mkdir(parents=True, exist_ok=True)
    name = f"{safe_slug(prefix, 'source', 40)}__{src.name}" if prefix else src.name
    dst = destination_dir / name
    shutil.copy2(src, dst)
    return dst


def _write_previous_answers(project_root: Path, mission_id: str, handoff_root: Path, current_step: str) -> list[Path]:
    order_index = {step: idx for idx, step in enumerate(CHAIN_ORDER)}
    current_idx = order_index.get(current_step, 999)
    out_dir = handoff_root / "previous_answers"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for record in _mission_records(project_root, mission_id):
        step = str(getattr(record, "chain_step", ""))
        if order_index.get(step, 999) >= current_idx:
            continue
        text = read_analysis(record)
        filename = f"{order_index.get(step, 0) + 1:02d}_{safe_slug(_step_title(step), 'answer', 70)}__{safe_slug(getattr(record, 'record_id', ''), 'record', 35)}.md"
        dst = out_dir / filename
        atomic_write_text(dst, text, encoding="utf-8")
        written.append(dst)
    return written


def _zip_folder(folder: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in folder.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(folder))


def export_step_handoff(
    project_root: Path,
    mission_id: str,
    downloads_dir: Path,
    step_id: str | None = None,
) -> HandoffResult:
    mission = _load_mission(project_root, mission_id)
    step = step_id or next_pending_step(project_root, mission_id)
    if not step:
        raise RuntimeError("Mission has no pending step. Export the final action pack instead.")

    projects = _projects_for_mission(project_root, mission)
    step_label = _step_title(step)
    stamp = now_stamp()
    root = mission.folder / "chatgpt_handoffs" / f"STEP_HANDOFF_{stamp}_{safe_slug(step_label, 'step', 60)}"
    root.mkdir(parents=True, exist_ok=False)

    prompt = _prompt_for_step(mission, projects, step)
    atomic_write_text(root / "NEXT_PROMPT_TO_SEND.md", prompt, encoding="utf-8")
    atomic_write_json(root / "MISSION.json", {
        "mission_id": mission.mission_id,
        "mission_name": mission.name,
        "focus_preset": mission.focus_preset,
        "status": mission.status,
        "pending_step": step,
        "pending_step_label": step_label,
        "projects": mission.projects,
        "created_at": mission.created_at,
        "exported_at": now_text(),
    })

    research_dir = root / "research_packs"
    included: list[Path] = []
    skipped: list[str] = []
    for project in projects:
        copied = _copy_if_exists(project.get("zip_path"), research_dir, str(project.get("name", "source")))
        if copied:
            included.append(copied)
        else:
            skipped.append(f"{project.get('name', 'Unnamed')}: ZIP missing or unavailable")

    previous = _write_previous_answers(project_root, mission_id, root, step)
    all_prompts_dir = root / "prompt_chain"
    all_prompts_dir.mkdir(parents=True, exist_ok=True)
    for index, (name, prompt_text) in enumerate(generate_prompt_chain(mission, projects), start=1):
        atomic_write_text(all_prompts_dir / f"STEP_{index:02d}_{name}.md", prompt_text, encoding="utf-8")

    instructions = f"""# ChatGPT handoff instructions

Mission: {mission.name}
Current step: {step_label}

Use this ZIP in ChatGPT:
1. Upload this handoff ZIP.
2. Paste the content of NEXT_PROMPT_TO_SEND.md.
3. When ChatGPT answers, paste the full answer back into YTIS Mission tab and click Save Answer & Advance.

Included research packs:
{chr(10).join('- ' + p.name for p in included) or '- None'}

Previous answers:
{chr(10).join('- ' + p.name for p in previous) or '- None'}

Skipped:
{chr(10).join('- ' + item for item in skipped) or '- None'}
"""
    atomic_write_text(root / "UPLOAD_INSTRUCTIONS.md", instructions, encoding="utf-8")

    report_path = root / "HANDOFF_REPORT.md"
    atomic_write_text(report_path, f"""# YTIS ChatGPT Step Handoff

Mission: {mission.name}
Mission ID: `{mission.mission_id}`
Step: {step_label}
Exported: {now_text()}

Included research packs: {len(included)}
Previous answers included: {len(previous)}

Next action:
Upload this ZIP to ChatGPT and paste `NEXT_PROMPT_TO_SEND.md`.
""", encoding="utf-8")

    zip_path = downloads_dir / f"YTIS_CHATGPT_STEP_HANDOFF_{safe_slug(mission.name, 'mission', 60)}_{safe_slug(step_label, 'step', 35)}_{stamp}.zip"
    _zip_folder(root, zip_path)
    return HandoffResult(zip_path, root, mission.mission_id, mission.name, step, step_label, included, previous, report_path)


def save_chatgpt_answer(
    project_root: Path,
    mission_id: str,
    answer_text: str,
    chain_step: str | None = None,
    source_evidence_pack: str = "",
) -> SaveAnswerResult:
    mission = _load_mission(project_root, mission_id)
    step = chain_step or next_pending_step(project_root, mission_id)
    if not step:
        raise RuntimeError("Mission has no pending step. The answer was not saved because all steps are already complete.")
    text = (answer_text or "").strip()
    if not text:
        raise RuntimeError("ChatGPT answer is empty.")

    projects = _projects_for_mission(project_root, mission)
    if not source_evidence_pack:
        for project in projects:
            if project.get("zip_path"):
                source_evidence_pack = str(project.get("zip_path"))
                break

    record = save_analysis(
        project_root=project_root,
        title=f"{mission.name} - {_step_title(step)}",
        analysis_text=text,
        projects=list(mission.projects or []),
        topic=_step_title(step),
        focus_preset=mission.focus_preset,
        source_bundle="",
        source_evidence_pack=source_evidence_pack,
        notes="Saved from ChatGPT handoff workflow",
        mission_id=mission.mission_id,
        mission_name=mission.name,
        chain_step=step,
    )
    complete = complete_mission_if_ready(project_root, mission_id)
    mission_after = _load_mission(project_root, mission_id)
    return SaveAnswerResult(record.record_id, step, _step_title(step), complete, mission_after.status)


def _write_all_saved_answers(project_root: Path, mission_id: str, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    order_index = {step: idx for idx, step in enumerate(CHAIN_ORDER)}
    for record in _mission_records(project_root, mission_id):
        step = str(getattr(record, "chain_step", ""))
        idx = order_index.get(step, 999) + 1
        filename = f"STEP_{idx:02d}_{safe_slug(_step_title(step), 'answer', 60)}.md"
        dst = out_dir / filename
        atomic_write_text(dst, read_analysis(record), encoding="utf-8")
        written.append(dst)
    return written


def _extract_save_back_section(text: str) -> str:
    match = re.search(r"(?is)(?:^|\n)#+\s*What to save back into YTIS\s*(.*)$", text or "")
    if match:
        return match.group(1).strip()
    return ""


def _knowledge_card_candidates_from_answers(project_root: Path, mission_id: str) -> str:
    records = _mission_records(project_root, mission_id)
    sections: list[str] = []
    for record in records:
        text = read_analysis(record)
        section = _extract_save_back_section(text)
        if section:
            sections.append(f"## {_step_title(str(getattr(record, 'chain_step', '')))}\n\n{section}")
    if not sections:
        return "# Knowledge Card Candidates\n\nNo explicit 'What to save back into YTIS' sections were found. Review the saved answers manually.\n"
    return "# Knowledge Card Candidates\n\n" + "\n\n---\n\n".join(sections) + "\n"


def export_final_action_pack(project_root: Path, mission_id: str, downloads_dir: Path) -> FinalPackResult:
    mission = _load_mission(project_root, mission_id)
    complete_mission_if_ready(project_root, mission_id)
    mission = _load_mission(project_root, mission_id)

    stamp = now_stamp()
    root = mission.folder / "final_action_packs" / f"FINAL_ACTION_PACK_{stamp}"
    root.mkdir(parents=True, exist_ok=False)

    answers_dir = root / "saved_answers"
    saved = _write_all_saved_answers(project_root, mission_id, answers_dir)

    card_candidates = root / "KNOWLEDGE_CARD_CANDIDATES.md"
    atomic_write_text(card_candidates, _knowledge_card_candidates_from_answers(project_root, mission_id), encoding="utf-8")

    projects = _projects_for_mission(project_root, mission)
    research_dir = root / "research_packs"
    included: list[Path] = []
    for project in projects:
        copied = _copy_if_exists(project.get("zip_path"), research_dir, str(project.get("name", "source")))
        if copied:
            included.append(copied)

    atomic_write_json(root / "MISSION_FINAL_STATE.json", {
        "mission_id": mission.mission_id,
        "mission_name": mission.name,
        "status": mission.status,
        "focus_preset": mission.focus_preset,
        "projects": mission.projects,
        "topics": mission.topics,
        "saved_answers": len(saved),
        "all_steps_complete": all_steps_complete(project_root, mission_id),
        "exported_at": now_text(),
    })

    report_path = root / "FINAL_ACTION_PACK_REPORT.md"
    atomic_write_text(report_path, f"""# YTIS Final Action Pack

Mission: {mission.name}
Mission ID: `{mission.mission_id}`
Status: {mission.status}
Exported: {now_text()}

Saved answers included: {len(saved)}
Research packs included: {len(included)}

Files:
- saved_answers/
- KNOWLEDGE_CARD_CANDIDATES.md
- MISSION_FINAL_STATE.json
- research_packs/
""", encoding="utf-8")

    zip_path = downloads_dir / f"YTIS_FINAL_ACTION_PACK_{safe_slug(mission.name, 'mission', 70)}_{stamp}.zip"
    _zip_folder(root, zip_path)
    return FinalPackResult(zip_path, root, mission.mission_id, mission.name, len(saved), card_candidates, report_path)
