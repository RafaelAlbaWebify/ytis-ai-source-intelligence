from __future__ import annotations

import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ytis.core.io_utils import atomic_write_json, atomic_write_text, now_stamp, unique_child_path

MISSION_FOCUS_OPTIONS = [
    "Career learning",
    "Business model extraction",
    "Career + business",
    "Expert/source credibility",
    "Study/build roadmap",
    "Search discovery",
    "Business lessons",
    "Offers and pricing",
    "Lead generation",
    "Workflow extraction",
    "Technical learning",
    "Webify service ideas",
    "Custom",
]

MISSION_TOPIC_OPTIONS = [
    "Application Support",
    "Production support",
    "Troubleshooting",
    "Logs",
    "Monitoring",
    "SQL support",
    "APIs",
    "RCA",
    "Cloud basics",
    "DevOps basics",
    "Build projects",
    "Interview preparation",
    "Business model",
    "Monetization",
    "Offer",
    "Pricing",
    "Lead generation",
    "Workflow",
    "Niche",
    "Webify service ideas",
    "Technical learning",
]

MISSION_TEMPLATES: dict[str, str] = {
    "Career learning": "Extract practical career lessons from the selected expert/source evidence. Identify what Rafael should study, practice, build, document, and explain in interviews. Keep the output aligned with Application Support, software support, IT operations, troubleshooting, evidence gathering, documentation, and production-support growth.",
    "Business model extraction": "Analyze how the selected expert/source appears to make money. Extract the business model, offer, customer, pricing clues, delivery workflow, acquisition path, proof requirements, risks, and what Rafael could or should not adapt. Separate transcript-backed evidence from assumptions.",
    "Career + business": "Extract both career-learning value and business-model value from the selected expert/source evidence. Identify skills, workflows, study/build actions, monetization patterns, acquisition clues, credibility signals, hype risks, and Rafael-fit conclusions.",
    "Expert/source credibility": "Evaluate whether the selected YouTube expert/source is worth studying. Assess credibility, practical examples, evidence quality, specificity, hype risk, and relevance to Rafael before turning the source into study or business actions.",
    "Study/build roadmap": "Turn the selected source evidence into a realistic study and build roadmap for Rafael, including what to learn, what lab or project to build, what documentation to create, and what interview talking points to prepare.",
    "Search discovery": "Extract better search angles, YouTube queries, expert types, niche research paths, and source-selection criteria from the selected evidence or goal.",
    "Webify service ideas": "Extract realistic service ideas, offer structures, pricing clues, acquisition workflows, and validation steps for Webify Digital Solutions. Avoid positioning Rafael as a generic developer or agency unless transcript evidence strongly supports it.",
    "Offer design": "Study how offers are packaged, positioned, priced, guaranteed, sold, and differentiated. Extract practical offer patterns and weak assumptions.",
    "Lead generation": "Study how leads are generated, qualified, followed up, and converted. Extract repeatable outreach, content, funnel, and sales workflows.",
    "Workflow extraction": "Extract repeatable workflows, SOPs, checklists, implementation processes, and operating systems that can be applied or tested.",
    "Technical learning": "Extract technical learning, support workflows, troubleshooting methods, operational practices, and career-relevant knowledge.",
    "Custom": "",
}

CHAIN_STEPS = [
    {
        "name": "01_extract_map",
        "title": "Source credibility and topic map",
        "task": "Map what the selected source actually teaches. Identify main topics, practical examples, credibility signals, weak evidence, hype risk, and relevance to the mission goal. Do not produce final recommendations yet.",
    },
    {
        "name": "02_compare_patterns",
        "title": "Career and business value extraction",
        "task": "Extract the useful career-learning value and/or business-model value requested by the mission. Identify skills, tools, workflows, monetization patterns, customer/audience clues, offer/pricing clues, and contradictions.",
    },
    {
        "name": "03_extract_workflows",
        "title": "Workflows, labs, and operating systems",
        "task": "Turn the strongest findings into concrete workflows, checklists, labs, study tasks, build projects, templates, scripts, or operating systems. Make them practical and step-by-step.",
    },
    {
        "name": "04_apply_to_rafael_webify",
        "title": "Rafael fit, risks, and positioning",
        "task": "Apply the findings to Rafael Alba. Respect his real background in IT operations, application support, Microsoft 365, DNS/email basics, manufacturing IT, SQL-dependent applications from the support side, incident management, documentation, and troubleshooting. Separate what fits now, what fits later, and what should be avoided.",
    },
    {
        "name": "05_validation_plan",
        "title": "Action roadmap, cards, and next searches",
        "task": "Turn the mission findings into a 7-day and 30-day action roadmap. Include study/build actions, possible Knowledge Cards, business tests if relevant, open questions, and better YouTube search queries to find stronger sources.",
    },
]

@dataclass
class Mission:
    mission_id: str
    name: str
    goal: str
    focus_preset: str
    projects: list[str]
    topics: list[str]
    status: str
    created_at: str
    updated_at: str
    folder: Path
    metadata_path: Path
    prompt_path: Path

@dataclass
class MissionBundleResult:
    bundle_path: Path
    prompt_path: Path
    included_zips: list[Path]
    skipped_projects: list[str]

@dataclass
class PromptChainResult:
    chain_zip: Path
    chain_folder: Path
    step_paths: list[Path]

def safe_slug(text: str, fallback: str = "mission") -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip())
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:90] or fallback

def missions_root(project_root: Path) -> Path:
    path = project_root / "missions"
    path.mkdir(parents=True, exist_ok=True)
    return path

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _stamp() -> str:
    return now_stamp()

def _mission_from_data(folder: Path, data: dict[str, Any]) -> Mission:
    return Mission(
        mission_id=str(data.get("mission_id") or folder.name),
        name=str(data.get("name") or folder.name),
        goal=str(data.get("goal") or ""),
        focus_preset=str(data.get("focus_preset") or "Custom"),
        projects=list(data.get("projects") or []),
        topics=list(data.get("topics") or []),
        status=str(data.get("status") or "active"),
        created_at=str(data.get("created_at") or ""),
        updated_at=str(data.get("updated_at") or ""),
        folder=folder,
        metadata_path=folder / "mission.json",
        prompt_path=folder / "mission_prompt.md",
    )

def create_mission(
    project_root: Path,
    name: str,
    goal: str,
    focus_preset: str,
    projects: list[str],
    topics: list[str],
    status: str = "active",
) -> Mission:
    clean_name = name.strip() or "Untitled mission"
    mission_stem = f"{_stamp()}_{safe_slug(clean_name)}"
    folder = unique_child_path(missions_root(project_root), mission_stem)
    folder.mkdir(parents=True, exist_ok=False)
    mission_id = folder.name
    (folder / "bundles").mkdir(exist_ok=True)
    (folder / "evidence_packs").mkdir(exist_ok=True)
    (folder / "analyses").mkdir(exist_ok=True)
    (folder / "prompt_chains").mkdir(exist_ok=True)

    created = _now()
    data = {
        "mission_id": mission_id,
        "name": clean_name,
        "goal": goal.strip(),
        "focus_preset": focus_preset,
        "projects": projects,
        "topics": topics,
        "status": status,
        "created_at": created,
        "updated_at": created,
    }
    atomic_write_json(folder / "mission.json", data)
    mission = _mission_from_data(folder, data)
    atomic_write_text(mission.prompt_path, generate_mission_prompt(mission, []), encoding="utf-8")
    return mission

def save_mission(mission: Mission) -> None:
    mission.updated_at = _now()
    data = {
        "mission_id": mission.mission_id,
        "name": mission.name,
        "goal": mission.goal,
        "focus_preset": mission.focus_preset,
        "projects": mission.projects,
        "topics": mission.topics,
        "status": mission.status,
        "created_at": mission.created_at,
        "updated_at": mission.updated_at,
    }
    atomic_write_json(mission.metadata_path, data)
    atomic_write_text(mission.prompt_path, generate_mission_prompt(mission, []), encoding="utf-8")

def list_missions(project_root: Path) -> list[Mission]:
    root = missions_root(project_root)
    missions: list[Mission] = []
    for folder in sorted(root.iterdir(), reverse=True):
        if not folder.is_dir():
            continue
        metadata_path = folder / "mission.json"
        if not metadata_path.exists():
            continue
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
            missions.append(_mission_from_data(folder, data))
        except Exception:
            continue
    return missions

def mission_stats(missions: list[Mission]) -> dict[str, int]:
    return {
        "missions": len(missions),
        "active": sum(1 for m in missions if m.status == "active"),
        "paused": sum(1 for m in missions if m.status == "paused"),
        "completed": sum(1 for m in missions if m.status == "completed"),
    }

def project_lookup(projects: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(p.get("name", "Unnamed")): p for p in projects}

def selected_project_records(mission: Mission, projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = project_lookup(projects)
    return [lookup[name] for name in mission.projects if name in lookup]

def _project_summary(project: dict[str, Any]) -> str:
    name = project.get("name", "Unnamed")
    videos = project.get("videos_found", 0)
    transcripts = project.get("transcripts_created", 0)
    words = project.get("total_words", 0)
    zip_path = project.get("zip_path", "")
    return f"- {name}: {videos} videos, {transcripts} transcripts, {words} words, ZIP={zip_path or '-'}"

def generate_mission_prompt(mission: Mission, projects: list[dict[str, Any]]) -> str:
    project_rows = "\n".join(_project_summary(p) for p in projects) if projects else "- Project details will be added when a bundle is generated."
    topics = ", ".join(mission.topics) if mission.topics else "not specified"
    goal = mission.goal.strip() or MISSION_TEMPLATES.get(mission.focus_preset, "")

    return f"""# YTIS Study Mission Prompt

Mission:
{mission.name}

Mission goal:
{goal or '-'}

Focus preset:
{mission.focus_preset}

Topics:
{topics}

Projects:
{project_rows}

Instructions:
- Use the uploaded YTIS research packs as the primary source.
- Work toward the mission goal, not a generic summary.
- Extract concrete lessons, workflows, patterns, examples, warnings, and action items.
- Separate evidence-backed findings from interpretation.
- Reference source project/channel names when possible.
- Be skeptical of generic creator advice.
- Identify what Rafael should test, ignore, or investigate next.

Output format:
1. Mission executive summary.
2. Project-by-project findings.
3. Topic-by-topic findings.
4. Repeated patterns across sources.
5. Unique or contradictory advice.
6. Practical workflows and checklists.
7. Ideas relevant to Rafael/Webify.
8. Weak assumptions and validation needed.
9. Next YTIS evidence pack or follow-up prompt to run.
10. 7-day and 30-day action plan.
"""

def _chain_context(mission: Mission, projects: list[dict[str, Any]]) -> str:
    project_rows = "\n".join(_project_summary(p) for p in projects) if projects else "- Project details unavailable."
    topics = ", ".join(mission.topics) if mission.topics else "not specified"
    goal = mission.goal.strip() or MISSION_TEMPLATES.get(mission.focus_preset, "")
    return f"""Mission: {mission.name}
Goal: {goal or '-'}
Focus preset: {mission.focus_preset}
Topics: {topics}

Projects:
{project_rows}
"""

def generate_prompt_chain(mission: Mission, projects: list[dict[str, Any]]) -> list[tuple[str, str]]:
    context = _chain_context(mission, projects)
    prompts: list[tuple[str, str]] = []
    previous_instruction = "Use the uploaded YTIS research packs as the primary source."

    for index, step in enumerate(CHAIN_STEPS, start=1):
        title = step["title"]
        name = step["name"]
        carry_forward = ""
        if index > 1:
            carry_forward = (
                "\nBefore answering this step, use the previous ChatGPT answer in this chat as context. "
                "Do not repeat everything. Continue the analysis and deepen it.\n"
            )

        prompt = f"""# YTIS Mission Prompt Chain - Step {index}: {title}

Mission context:
{context}

Step task:
{step['task']}

Rules:
- {previous_instruction}
- Work toward the mission goal.
- Be practical and evidence-driven.
- Clearly separate evidence-backed findings from interpretation.
- Reference source project/channel names when possible.
- If evidence is weak or missing, say so.
{carry_forward}

Output:
- Start with a concise step summary.
- Then provide structured findings.
- End with "What to save back into YTIS" as bullet points.
"""
        prompts.append((name, prompt))
    return prompts

def create_prompt_chain_pack(mission: Mission, projects: list[dict[str, Any]], downloads_dir: Path) -> PromptChainResult:
    stamp = _stamp()
    selected = selected_project_records(mission, projects)
    chain_root = mission.folder / "prompt_chains" / f"PROMPT_CHAIN_{stamp}"
    chain_root.mkdir(parents=True, exist_ok=True)

    prompts = generate_prompt_chain(mission, selected)
    step_paths: list[Path] = []
    for index, (name, prompt) in enumerate(prompts, start=1):
        path = chain_root / f"STEP_{index:02d}_{name}.md"
        atomic_write_text(path, prompt, encoding="utf-8")
        step_paths.append(path)

    combined = chain_root / "ALL_STEPS_COMBINED.md"
    atomic_write_text(
        combined,
        "\n\n---\n\n".join(path.read_text(encoding="utf-8") for path in step_paths),
        encoding="utf-8",
    )

    readme = chain_root / "README_PROMPT_CHAIN.md"
    atomic_write_text(
        readme,
        f"""# YTIS Mission Prompt Chain

Mission: {mission.name}
Focus: {mission.focus_preset}

How to use:
1. Upload the mission bundle or selected research packs to ChatGPT.
2. Run STEP_01 first.
3. Save the ChatGPT answer into YTIS Analysis Library.
4. Run STEP_02 in the same chat or with the previous answer pasted.
5. Continue until the final validation/action step.
6. Save important answers back into YTIS Analysis Library.

Files:
{chr(10).join(f"- {path.name}" for path in step_paths)}
- ALL_STEPS_COMBINED.md
""",
        encoding="utf-8",
    )

    downloads_dir.mkdir(parents=True, exist_ok=True)
    zip_path = downloads_dir / f"YTIS_PROMPT_CHAIN_{safe_slug(mission.name)}_{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in chain_root.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(chain_root))

    return PromptChainResult(zip_path, chain_root, step_paths)

def create_mission_bundle(
    mission: Mission,
    projects: list[dict[str, Any]],
    downloads_dir: Path,
) -> MissionBundleResult:
    stamp = _stamp()
    selected = selected_project_records(mission, projects)
    bundle_root = mission.folder / "bundles" / f"MISSION_BUNDLE_{stamp}"
    bundle_root.mkdir(parents=True, exist_ok=True)
    research_dir = bundle_root / "research_packs"
    research_dir.mkdir(exist_ok=True)

    prompt = generate_mission_prompt(mission, selected)
    prompt_path = bundle_root / "MISSION_PROMPT.md"
    atomic_write_text(prompt_path, prompt, encoding="utf-8")
    atomic_write_text(mission.prompt_path, prompt, encoding="utf-8")

    chain = generate_prompt_chain(mission, selected)
    chain_dir = bundle_root / "prompt_chain"
    chain_dir.mkdir(exist_ok=True)
    for index, (name, step_prompt) in enumerate(chain, start=1):
        atomic_write_text(chain_dir / f"STEP_{index:02d}_{name}.md", step_prompt, encoding="utf-8")

    included: list[Path] = []
    skipped: list[str] = []
    for project in selected:
        name = str(project.get("name", "Unnamed"))
        zip_value = project.get("zip_path")
        if not zip_value:
            skipped.append(f"{name}: no ZIP path")
            continue
        src = Path(str(zip_value))
        if not src.exists():
            skipped.append(f"{name}: ZIP missing")
            continue
        safe_name = safe_slug(name, "project")
        dst = research_dir / f"{safe_name}__{src.name}"
        shutil.copy2(src, dst)
        included.append(dst)

    readme = bundle_root / "README_MISSION_BUNDLE.md"
    atomic_write_text(
        readme,
        f"""# YTIS Mission Bundle

Mission: {mission.name}
Focus: {mission.focus_preset}
Topics: {', '.join(mission.topics) if mission.topics else '-'}

Goal:
{mission.goal or '-'}

How to use:
1. Upload this mission bundle ZIP to ChatGPT.
2. Open MISSION_PROMPT.md for one-pass analysis, or use prompt_chain/ for staged analysis.
3. Save the ChatGPT result back into YTIS Analysis Library.

Included research packs:
{chr(10).join(f"- {p.name}" for p in included) or "- None"}

Skipped:
{chr(10).join(f"- {item}" for item in skipped) or "- None"}
""",
        encoding="utf-8",
    )

    downloads_dir.mkdir(parents=True, exist_ok=True)
    bundle_zip = downloads_dir / f"YTIS_MISSION_BUNDLE_{safe_slug(mission.name)}_{stamp}.zip"
    with zipfile.ZipFile(bundle_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in bundle_root.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(bundle_root))

    return MissionBundleResult(bundle_zip, prompt_path, included, skipped)

def update_mission_status(mission: Mission, status: str) -> None:
    mission.status = status
    save_mission(mission)

def read_mission_prompt(mission: Mission) -> str:
    if mission.prompt_path.exists():
        return mission.prompt_path.read_text(encoding="utf-8-sig", errors="replace")
    return generate_mission_prompt(mission, [])
