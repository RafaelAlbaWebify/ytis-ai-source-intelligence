from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from ytis.core.paths import safe_name


RESEARCH_GOALS: dict[str, dict[str, Any]] = {
    "Career Learning": {
        "default_topic": "Application Support Engineer",
        "intent": "Find practical expert knowledge that can become a study plan, lab, portfolio artifact, or interview story.",
        "queries": [
            "{topic} day in the life real work",
            "{topic} troubleshooting workflow examples",
            "{topic} interview preparation real incidents",
            "{topic} tools logs SQL API support",
            "{topic} root cause analysis examples",
            "{topic} escalation and incident management",
            "{topic} portfolio project ideas",
            "{topic} mistakes to avoid",
        ],
        "source_type": "Practitioner / operator",
    },
    "Business Model Research": {
        "default_topic": "productized technical audit service",
        "intent": "Find how experts make money, what they sell, who buys, pricing clues, delivery workflow, acquisition, and what Rafael can adapt.",
        "queries": [
            "{topic} business model breakdown",
            "{topic} pricing case study",
            "{topic} how to get clients",
            "{topic} offer breakdown",
            "{topic} delivery workflow",
            "{topic} mistakes and risks",
            "{topic} from zero clients",
            "{topic} consulting retainer audit service",
        ],
        "source_type": "Operator / consultant",
    },
    "Expert Discovery": {
        "default_topic": "software support engineer",
        "intent": "Find credible people worth studying, not generic motivational or course-only content.",
        "queries": [
            "best {topic} YouTube channels practitioners",
            "{topic} real world troubleshooting interview",
            "{topic} conference talk case study",
            "{topic} consultant breakdown workflow",
            "{topic} senior engineer lessons learned",
            "{topic} operations incident postmortem",
            "{topic} practical tutorial full workflow",
        ],
        "source_type": "Expert / practitioner / conference speaker",
    },
    "Niche Discovery": {
        "default_topic": "small business technical operations problems",
        "intent": "Find niches where Rafael's IT operations, application support, Microsoft 365, DNS/email, and troubleshooting strengths can create value.",
        "queries": [
            "{topic} common problems",
            "{topic} consulting opportunities",
            "{topic} productized service ideas",
            "{topic} audit service",
            "{topic} recurring service retainer",
            "{topic} case study small business",
            "{topic} mistakes business owners make",
        ],
        "source_type": "Small business operator / consultant",
    },
    "Build and Lab Ideas": {
        "default_topic": "application support troubleshooting lab",
        "intent": "Find practical projects that prove learning through evidence, documentation, and interview-ready cases.",
        "queries": [
            "{topic} project tutorial",
            "{topic} portfolio project",
            "{topic} incident simulation",
            "{topic} logs SQL API exercise",
            "{topic} runbook example",
            "{topic} root cause analysis lab",
            "{topic} support ticket examples",
        ],
        "source_type": "Builder / teacher / practitioner",
    },
}

SEARCH_MODIFIERS = [
    "case study",
    "breakdown",
    "real example",
    "workflow",
    "pricing",
    "client acquisition",
    "day in the life",
    "mistakes",
    "postmortem",
    "interview",
]

ANTI_HYPE_FILTERS = [
    "only motivational",
    "fake or unverifiable income claim",
    "course pitch without operating detail",
    "no real workflow",
    "no specific examples",
    "promises fast money or no-skill success",
    "too generic to become a study/build action",
]

EXPERT_SOURCE_TYPES = [
    "Practitioner",
    "Operator",
    "Consultant",
    "Agency owner",
    "Founder",
    "Course seller",
    "Content creator",
    "Affiliate marketer",
    "Hype channel",
    "Unknown",
]

EXTRACTION_MODES = [
    "Career Learning",
    "Business Model",
    "Both",
    "Study and Build Plan",
    "Warning / Avoidance Notes",
]


def _now_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _safe_read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def workspace_dir(root: Path) -> Path:
    return root / "ytis_state" / "expert_intelligence"


def research_queue_path(root: Path) -> Path:
    return workspace_dir(root) / "research_queue.json"


def expert_profiles_path(root: Path) -> Path:
    return workspace_dir(root) / "expert_profiles.json"


def load_research_queue(root: Path) -> list[dict[str, Any]]:
    data = _safe_read_json(research_queue_path(root), [])
    return data if isinstance(data, list) else []


def save_research_queue(root: Path, rows: list[dict[str, Any]]) -> None:
    _write_json(research_queue_path(root), rows)


def load_expert_profiles(root: Path) -> list[dict[str, Any]]:
    data = _safe_read_json(expert_profiles_path(root), [])
    return data if isinstance(data, list) else []


def save_expert_profiles(root: Path, rows: list[dict[str, Any]]) -> None:
    _write_json(expert_profiles_path(root), rows)


def generate_search_campaign(goal: str, topic: str, notes: str = "") -> dict[str, Any]:
    config = RESEARCH_GOALS.get(goal) or RESEARCH_GOALS["Career Learning"]
    topic = (topic or "").strip() or config["default_topic"]
    notes = (notes or "").strip()
    rows: list[dict[str, Any]] = []
    for index, template in enumerate(config["queries"], start=1):
        query = template.format(topic=topic).strip()
        purpose = _purpose_for_query(goal, query)
        rows.append(
            {
                "query_id": f"draft_{index}",
                "query": query,
                "goal": goal,
                "priority": "High" if index <= 4 else "Medium",
                "source_type": config["source_type"],
                "status": "To search",
                "purpose": purpose,
                "what_to_look_for": _look_for(goal),
                "good_source_signs": _good_source_signs(goal),
                "reject_if": list(ANTI_HYPE_FILTERS),
                "next_action": "Search YouTube manually, shortlist 1 to 3 credible videos, then capture transcripts into YTIS.",
                "notes": notes,
            }
        )
    return {
        "campaign_id": _now_id("campaign"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "goal": goal,
        "topic": topic,
        "intent": config["intent"],
        "queries": rows,
    }


def _purpose_for_query(goal: str, query: str) -> str:
    if goal == "Career Learning":
        return "Extract real skills, workflows, mistakes, tools, labs, and interview material."
    if goal == "Business Model Research":
        return "Extract monetization method, offer, pricing, customer, delivery, and acquisition clues."
    if goal == "Expert Discovery":
        return "Find credible experts and reject low-signal channels before spending time on transcripts."
    if goal == "Niche Discovery":
        return "Find painful niches where Rafael's practical IT/support strengths could fit."
    if goal == "Build and Lab Ideas":
        return "Find practical build projects that produce proof of skill and reusable documentation."
    return "Find useful evidence for the current YTIS research direction."


def _look_for(goal: str) -> list[str]:
    common = ["specific examples", "operational detail", "mistakes explained", "proof or case detail"]
    if goal == "Career Learning":
        return common + ["tools used", "incident workflow", "what to study", "what to build"]
    if goal == "Business Model Research":
        return common + ["offer", "customer", "pricing", "acquisition channel", "delivery process"]
    if goal == "Expert Discovery":
        return common + ["professional background", "practitioner credibility", "non-generic teaching"]
    if goal == "Niche Discovery":
        return common + ["urgent business pain", "repeatable problem", "buyer with budget", "fit for Rafael"]
    if goal == "Build and Lab Ideas":
        return common + ["project steps", "evidence artifact", "portfolio value", "interview relevance"]
    return common


def _good_source_signs(goal: str) -> list[str]:
    signs = [
        "shows a concrete workflow",
        "uses real examples or case studies",
        "explains tradeoffs and mistakes",
        "is specific enough to become a card, lab, or action",
    ]
    if goal in {"Business Model Research", "Niche Discovery"}:
        signs += ["mentions customer type", "explains pricing or delivery", "shows acquisition path"]
    if goal in {"Career Learning", "Build and Lab Ideas"}:
        signs += ["names tools and evidence", "connects to real work or interviews"]
    return signs


def append_campaign_to_queue(root: Path, campaign: dict[str, Any]) -> int:
    queue = load_research_queue(root)
    added = 0
    existing = {str(row.get("query", "")).lower().strip() for row in queue}
    for row in campaign.get("queries", []):
        query = str(row.get("query") or "").strip()
        if not query or query.lower() in existing:
            continue
        new_row = dict(row)
        new_row["query_id"] = _now_id("query") + f"_{added + 1}"
        new_row["campaign_id"] = campaign.get("campaign_id")
        new_row["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        queue.append(new_row)
        existing.add(query.lower())
        added += 1
    save_research_queue(root, queue)
    return added


def add_custom_query(root: Path, query: str, goal: str, priority: str, notes: str = "") -> dict[str, Any]:
    row = {
        "query_id": _now_id("query"),
        "campaign_id": "manual",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "query": query.strip(),
        "goal": goal,
        "priority": priority,
        "source_type": (RESEARCH_GOALS.get(goal) or {}).get("source_type", "Unknown"),
        "status": "To search",
        "purpose": _purpose_for_query(goal, query),
        "what_to_look_for": _look_for(goal),
        "good_source_signs": _good_source_signs(goal),
        "reject_if": list(ANTI_HYPE_FILTERS),
        "next_action": "Search YouTube manually, then capture any strong transcript into YTIS.",
        "notes": notes.strip(),
    }
    rows = load_research_queue(root)
    rows.append(row)
    save_research_queue(root, rows)
    return row


def update_query_status(root: Path, query_id: str, status: str) -> bool:
    rows = load_research_queue(root)
    changed = False
    for row in rows:
        if str(row.get("query_id")) == query_id:
            row["status"] = status
            row["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            changed = True
            break
    if changed:
        save_research_queue(root, rows)
    return changed


def delete_query(root: Path, query_id: str) -> bool:
    rows = load_research_queue(root)
    new_rows = [row for row in rows if str(row.get("query_id")) != query_id]
    if len(new_rows) == len(rows):
        return False
    save_research_queue(root, new_rows)
    return True


def export_research_queue(root: Path, downloads_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_root = downloads_dir / f"YTIS_RESEARCH_RADAR_EXPORT_{stamp}"
    export_root.mkdir(parents=True, exist_ok=True)
    queue = load_research_queue(root)
    profiles = load_expert_profiles(root)
    _write_json(export_root / "research_queue.json", queue)
    _write_json(export_root / "expert_profiles.json", profiles)
    (export_root / "research_queue.md").write_text(_queue_markdown(queue), encoding="utf-8")
    (export_root / "README.md").write_text(
        "# YTIS Research Radar Export\n\nThis pack contains search queries, research queue status, and expert profile records.\n",
        encoding="utf-8",
    )
    zip_path = downloads_dir / f"YTIS_RESEARCH_RADAR_EXPORT_{stamp}.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", export_root)
    return zip_path


def _queue_markdown(rows: list[dict[str, Any]]) -> str:
    lines = ["# Research Queue", ""]
    if not rows:
        lines.append("No queries saved yet.")
        return "\n".join(lines) + "\n"
    for row in rows:
        lines.extend(
            [
                f"## {row.get('query', '-')}",
                f"- Goal: {row.get('goal', '-')}",
                f"- Priority: {row.get('priority', '-')}",
                f"- Status: {row.get('status', '-')}",
                f"- Purpose: {row.get('purpose', '-')}",
                "- What to look for: " + "; ".join(row.get("what_to_look_for", []) or []),
                "- Reject if: " + "; ".join(row.get("reject_if", []) or []),
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def save_expert_profile(root: Path, profile: dict[str, Any]) -> dict[str, Any]:
    rows = load_expert_profiles(root)
    row = dict(profile)
    row["profile_id"] = row.get("profile_id") or _now_id("expert")
    row["created_at"] = row.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows.append(row)
    save_expert_profiles(root, rows)
    return row



def _humanize_project_name(value: str) -> str:
    text = str(value or '').strip()
    if not text:
        return ''
    text = re.sub(r'[_-]+', ' ', text)
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def infer_profile_defaults(project: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, str]:
    """Infer conservative profile defaults from selected project metadata.

    These are hypotheses for prompt quality, not facts. The prompt still asks ChatGPT
    to separate transcript-supported claims from assumptions.
    """
    profile = profile or {}
    project_name_raw = str(project.get('name') or profile.get('project') or '').strip()
    url = str(project.get('url') or '').strip()
    haystack = f"{project_name_raw} {url}".lower()
    project_name = _humanize_project_name(project_name_raw) or 'Selected project'

    source_name = str(profile.get('source_name') or '').strip()
    if not source_name:
        # Prefer a YouTube handle when available; otherwise use the project name.
        match = re.search(r'youtube\.com/@([^/\s]+)', url, flags=re.I)
        source_name = _humanize_project_name(match.group(1)) if match else project_name

    topic = str(profile.get('topic') or '').strip()
    source_type = str(profile.get('source_type') or '').strip() or 'Unknown'
    business_type = str(profile.get('business_type') or '').strip() or 'Unknown'
    target_audience = str(profile.get('target_audience') or '').strip()
    credibility_notes = str(profile.get('credibility_notes') or '').strip()
    relevance = str(profile.get('rafael_relevance') or '').strip()

    if 'kieranmoloney' in haystack or 'kieran moloney' in haystack:
        topic = topic or 'business, service offers, web agency/service operations, productized services, and client acquisition'
        source_type = source_type if source_type != 'Unknown' else 'Operator / consultant / educator hypothesis'
        business_type = business_type if business_type != 'Unknown' else 'Service business / consulting / content-led acquisition hypothesis'
        target_audience = target_audience or 'freelancers, small service providers, agency owners, and people trying to sell services'
        credibility_notes = credibility_notes or 'YTIS should verify whether the transcript contains practical examples, pricing, delivery workflow, client acquisition details, or only generic advice.'
        relevance = relevance or 'Useful for Webify positioning, productized audit/service ideas, client acquisition lessons, and business-model extraction. Must be checked against Rafael real strengths.'
    elif 'jakestechjourney' in haystack or 'jakes tech journey' in haystack or 'jake' in haystack and 'tech' in haystack:
        topic = topic or 'IT career learning, technical skills, support work, and practical technology learning'
        source_type = source_type if source_type != 'Unknown' else 'Practitioner / educator hypothesis'
        business_type = business_type if business_type != 'Unknown' else 'Content / education hypothesis'
        target_audience = target_audience or 'IT learners, support professionals, and people building technical careers'
        credibility_notes = credibility_notes or 'YTIS should verify practical detail, real examples, tools, labs, and career relevance before trusting the advice.'
        relevance = relevance or 'Useful for career learning, study plans, labs, portfolio artifacts, and interview preparation.'
    else:
        topic = topic or f'topics covered by {project_name}'
        target_audience = target_audience or 'Unknown until transcript evidence is reviewed'
        credibility_notes = credibility_notes or 'Unknown until transcript evidence is reviewed. Check for specificity, real examples, and proof.'
        relevance = relevance or 'Assess whether this source helps Rafael learn, build, improve career positioning, or understand a business model.'

    return {
        'source_name': source_name,
        'source_type': source_type,
        'topic': topic,
        'business_type': business_type,
        'target_audience': target_audience,
        'credibility_notes': credibility_notes,
        'rafael_relevance': relevance,
    }

def generate_expert_prompt(project: dict[str, Any], profile: dict[str, Any], mode: str, notes: str = "") -> str:
    project_name = str(project.get("name") or "No project selected")
    url = str(project.get("url") or "-")
    total_words = str(project.get("total_words") or "0")
    transcripts = str(project.get("transcripts_created") or "0")
    inferred = infer_profile_defaults(project, profile)
    source_name = inferred["source_name"]
    source_type = inferred["source_type"]
    topic = inferred["topic"]
    business_type = inferred["business_type"]
    target_audience = inferred["target_audience"]
    credibility_notes = inferred["credibility_notes"]
    relevance = inferred["rafael_relevance"]
    notes = (notes or "").strip() or "No extra notes."

    mode_block = _mode_instructions(mode)

    return f"""# YTIS Expert Intelligence Prompt

You are analyzing YouTube transcript evidence from YTIS.

Project context:
- Project: {project_name}
- Source URL: {url}
- Transcripts: {transcripts}
- Total words: {total_words}

Expert/source profile:
- Expert/channel/source: {source_name}
- Topic: {topic}
- Source type hypothesis: {source_type}
- Business type hypothesis: {business_type}
- Target audience hypothesis: {target_audience}
- Credibility notes from Rafael/YTIS: {credibility_notes}
- Relevance to Rafael: {relevance}

Extra notes:
{notes}

Important context about Rafael:
- Rafael is strongest in IT operations, application support, Microsoft 365, Entra ID, Windows/endpoints, DNS/email basics, manufacturing IT/MES exposure, SQL-dependent applications from the support side, incident management, documentation, runbooks, and troubleshooting under production pressure.
- Do not position him as a generic developer, generic agency, cybersecurity expert, cloud architect, DBA, AI agency, or generic web designer unless the transcript evidence strongly supports it.
- Be skeptical. Separate what is supported by transcript evidence from assumptions.

Your task:
{mode_block}

Required output format:
1. Expert/source summary.
2. Credibility assessment.
3. Evidence quality and hype risk.
4. Career lessons for Rafael.
5. Business model / monetization extraction.
6. Customer, offer, pricing, delivery, and acquisition clues.
7. Rafael fit: fits now, fits later, does not fit, and why.
8. What Rafael should study next.
9. What Rafael should build or document next.
10. What Rafael could test as a business idea.
11. What to avoid or treat with skepticism.
12. Knowledge cards that should be created.
13. Search queries to find better sources on this topic.

Grounding rules:
- Use the uploaded transcript/project evidence as primary source.
- Mention source video names or transcript filenames when possible.
- Do not invent claims, pricing, credentials, or business models.
- If the transcript does not prove something, label it as inference or unknown.
"""


def _mode_instructions(mode: str) -> str:
    if mode == "Career Learning":
        return "Extract what Rafael should learn for career improvement: concepts, tools, workflows, practical labs, portfolio artifacts, interview stories, and mistakes to avoid."
    if mode == "Business Model":
        return "Extract how the expert/source appears to make money: offers, pricing clues, customer segments, acquisition channels, delivery model, required proof, risks, and what Rafael could realistically adapt."
    if mode == "Study and Build Plan":
        return "Turn the expert/source lessons into a practical study and build plan: 30-day plan, labs, artifacts, documentation, interview talking points, and proof-of-skill outputs."
    if mode == "Warning / Avoidance Notes":
        return "Identify hype, weak claims, unrealistic advice, missing evidence, risky positioning, and what Rafael should not copy."
    return "Extract both career learning value and business model value, then judge credibility, evidence strength, Rafael fit, study/build actions, and business actions."


def save_expert_prompt(prompt_text: str, downloads_dir: Path, source_name: str, mode: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    source = safe_name(source_name or "expert")[:60]
    safe_mode = safe_name(mode or "expert_intelligence")[:60]
    path = downloads_dir / f"YTIS_EXPERT_INTELLIGENCE_PROMPT_{source}_{safe_mode}_{stamp}.md"
    path.write_text(prompt_text, encoding="utf-8")
    return path
