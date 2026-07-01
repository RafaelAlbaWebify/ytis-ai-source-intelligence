from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any


PROMPT_TEMPLATES: dict[str, str] = {
    "Master Upload Analysis": "master",
    "Workflow Extraction": "workflow",
    "Business Lessons": "business",
    "Offer / Pricing Extraction": "offer",
    "Content Strategy": "content",
    "Service Ideas for Webify": "service",
}


def _safe_text(value: Any, default: str = "-") -> str:
    if value is None or value == "":
        return default
    return str(value)


def _safe_int(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except Exception:
        return "0"


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return cleaned[:60] or "YTIS_PROMPT"


def project_context(project: dict[str, Any]) -> str:
    return f"""Project context:
- Project name: {_safe_text(project.get("name"))}
- Source URL: {_safe_text(project.get("url"))}
- Build mode: {_safe_text(project.get("build_mode"))}
- Language: {_safe_text(project.get("language"))}
- Videos found: {_safe_text(project.get("videos_found"), "0")}
- Transcripts created: {_safe_text(project.get("transcripts_created"), "0")}
- Missing subtitles: {_safe_text(project.get("missing_subtitles"), "0")}
- Total words: {_safe_int(project.get("total_words"))}
- Project folder: {_safe_text(project.get("project_dir"))}
- ZIP path: {_safe_text(project.get("zip_path"))}
"""


def generate_prompt(project: dict[str, Any], template_name: str, extra_notes: str = "") -> str:
    template_key = PROMPT_TEMPLATES.get(template_name, "master")
    context = project_context(project)
    notes = extra_notes.strip() or "No extra notes."

    if template_key == "workflow":
        task = """Your task:
Analyze the uploaded YTIS transcript pack and extract practical workflows.

Focus on:
1. Repeatable step-by-step workflows.
2. Acquisition, sales, delivery, onboarding, operations, and retention systems.
3. What the creator actually does, not just abstract advice.
4. Sequences, checklists, scripts, SOPs, decision rules, and examples.
5. Separate proven patterns from speculative claims.

Output format:
- Executive summary.
- Workflow inventory table.
- Detailed workflow breakdowns.
- Implementation checklist.
- Risks, assumptions, and missing information.
- Top 10 actions I could implement in my business."""
    elif template_key == "business":
        task = """Your task:
Analyze the uploaded YTIS transcript pack and extract the strongest business lessons.

Focus on:
1. Offers, pricing, positioning, niches, customer acquisition, sales, delivery, retention, and operations.
2. Advice that appears repeatedly across videos.
3. Advice supported by concrete examples.
4. Lessons relevant to a small IT operations / application support / automation business.
5. Ideas that are realistic for Rafael Alba / Webify Digital Solutions, not generic guru advice.

Output format:
- Executive summary.
- Main business principles.
- Repeated patterns.
- Practical opportunities.
- What to ignore or treat with skepticism.
- Action plan for the next 30 days."""
    elif template_key == "offer":
        task = """Your task:
Analyze the uploaded YTIS transcript pack and extract all useful information about offers, pricing, packaging, monetization, and sales positioning.

Focus on:
1. Offer design.
2. Pricing logic.
3. Value propositions.
4. Guarantees, risk reversal, objections, and proof.
5. How services are packaged.
6. What could apply to Webify Digital Solutions.

Output format:
- Offer/pricing summary.
- Extracted offer patterns.
- Example offer structures.
- Pricing lessons.
- Objections and how they are handled.
- Suggested service packages for my situation."""
    elif template_key == "content":
        task = """Your task:
Analyze the uploaded YTIS transcript pack and extract content strategy lessons.

Focus on:
1. Topics that appear frequently.
2. Hooks, titles, positioning, stories, and teaching patterns.
3. How trust and authority are built.
4. How content connects to offers or business outcomes.
5. What could be reused for a practical IT/business YouTube or LinkedIn strategy.

Output format:
- Content strategy summary.
- Topic clusters.
- Hook/title patterns.
- Authority-building patterns.
- Suggested content plan.
- Risks and clichés to avoid."""
    elif template_key == "service":
        task = """Your task:
Analyze the uploaded YTIS transcript pack and extract realistic service ideas for Webify Digital Solutions.

Important context:
Rafael Alba is strongest in IT operations, Microsoft 365, Entra ID, Windows endpoints, DNS, manufacturing IT, SQL-dependent application support, incident management, documentation, and troubleshooting under production pressure.
Do not position him as a generic web designer, software agency, cybersecurity expert, cloud architect, DBA, or developer unless the evidence strongly supports it.

Focus on:
1. Services that are realistic for his current skills.
2. Services that can be productized.
3. Services that businesses may urgently need.
4. Services that can be delivered remotely or semi-remotely.
5. Services that produce portfolio evidence.

Output format:
- Best service opportunities.
- Why each fits or does not fit Rafael.
- Target customer.
- Offer statement.
- Delivery workflow.
- Pricing logic.
- Portfolio artifact to create.
- First 10 validation actions."""
    else:
        task = """Your task:
Analyze the uploaded YTIS transcript pack deeply.

Focus on:
1. Core ideas and recurring themes.
2. Practical workflows and frameworks.
3. Business advice, offers, pricing, sales, operations, and delivery.
4. Important examples, stories, and case studies.
5. Advice that is repeated, concrete, or actionable.
6. Advice that is vague, risky, exaggerated, or not applicable.

Output format:
- Executive summary.
- Main themes.
- Most actionable lessons.
- Workflow/table extraction.
- Quotes or close paraphrases with source video names when possible.
- Recommended actions.
- What to ignore or verify further."""

    return f"""# YTIS Analysis Prompt

You are analyzing a YouTube transcript research pack generated by YTIS.

{context}

Extra notes from me:
{notes}

Instructions:
- Use the uploaded ZIP/files as the primary source.
- Do not hallucinate facts that are not supported by the transcripts.
- When possible, reference the source video filename or title.
- Prefer concrete workflows, examples, and operational details.
- Be skeptical of generic advice.
- Make the answer practical and implementation-oriented.

{task}
"""


def save_prompt(prompt_text: str, downloads_dir: Path, project_name: str, template_name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_project = _safe_filename(project_name)
    safe_template = _safe_filename(template_name)
    path = downloads_dir / f"YTIS_PROMPT_{safe_project}_{safe_template}_{stamp}.md"
    path.write_text(prompt_text, encoding="utf-8")
    return path
