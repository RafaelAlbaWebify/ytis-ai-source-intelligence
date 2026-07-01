from __future__ import annotations

import csv
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


TOPIC_KEYWORDS: dict[str, list[str]] = {
    "Pricing": ["pricing", "price", "prices", "charge", "charging", "fee", "fees", "retainer", "budget", "quote", "proposal"],
    "Offer": ["offer", "offers", "guarantee", "guaranteed", "package", "positioning", "promise", "value proposition"],
    "Lead generation": ["lead generation", "qualified lead", "qualified leads", "leads", "prospects", "prospecting", "appointments", "pipeline"],
    "Sales call": ["sales call", "discovery call", "strategy call", "closing call", "sales process", "objection", "objections", "close the deal", "closing"],
    "Cold email": ["cold email", "email outreach", "outreach", "cold outreach", "inbox", "reply rate", "sequence"],
    "Funnel": ["funnel", "funnels", "landing page", "opt-in", "conversion", "webinar", "lead magnet"],
    "Agency": ["agency", "agencies", "client work", "done for you", "service business"],
    "MSP": ["msp", "managed service", "managed services", "it services", "it support", "technology company", "technology companies"],
    "Niche": ["niche", "vertical", "target market", "specialize", "specialise", "industry specific"],
    "Onboarding": ["onboarding", "onboard", "client onboarding", "handoff", "kickoff", "implementation"],
    "Content": ["content marketing", "content", "youtube", "linkedin", "personal brand", "social media"],
    "Ads": ["ads", "advertising", "google ads", "facebook ads", "paid ads", "campaign", "ad spend"],
    "Workflow": ["workflow", "process", "system", "sop", "framework", "steps", "checklist", "automation"],
}


@dataclass
class LibraryStats:
    projects: int
    videos: int
    transcripts: int
    words: int
    missing: int
    zip_ready: int


@dataclass
class BundleResult:
    bundle_path: Path
    prompt_path: Path
    readme_path: Path
    included_zips: list[Path]
    skipped_projects: list[str]


@dataclass
class TopicHit:
    project: str
    topic: str
    file_name: str
    file_path: str
    matches: int
    snippet: str


def as_int(value: Any) -> int:
    try:
        if value is None or value == "":
            return 0
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return 0


def compact(value: Any) -> str:
    n = as_int(value)
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if abs(n) >= 1_000:
        return f"{n / 1_000:.1f}k".replace(".0k", "k")
    return f"{n:,}"


def summarize(projects: list[dict[str, Any]]) -> LibraryStats:
    return LibraryStats(
        projects=len(projects),
        videos=sum(as_int(p.get("videos_found")) for p in projects),
        transcripts=sum(as_int(p.get("transcripts_created")) for p in projects),
        words=sum(as_int(p.get("total_words")) for p in projects),
        missing=sum(as_int(p.get("missing_subtitles")) for p in projects),
        zip_ready=sum(1 for p in projects if p.get("zip_path") and Path(str(p.get("zip_path"))).exists()),
    )


def density(project: dict[str, Any]) -> int:
    transcripts = as_int(project.get("transcripts_created"))
    words = as_int(project.get("total_words"))
    return int(words / transcripts) if transcripts else 0


def strength(project: dict[str, Any]) -> str:
    words = as_int(project.get("total_words"))
    transcripts = as_int(project.get("transcripts_created"))
    if transcripts >= 100 and words >= 150_000:
        return "Deep library"
    if transcripts >= 50 and words >= 75_000:
        return "Strong library"
    if transcripts >= 30:
        return "Useful library"
    return "Small pack"


def ranked_projects(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for p in projects:
        item = dict(p)
        item["_density"] = density(item)
        item["_strength"] = strength(item)
        items.append(item)
    return sorted(items, key=lambda p: as_int(p.get("total_words")), reverse=True)


def _clean_txt_files(project: dict[str, Any]) -> list[Path]:
    project_dir = Path(str(project.get("project_dir", "")))
    clean_dir = project_dir / "clean_txt"
    if not clean_dir.exists():
        return []
    return sorted(clean_dir.glob("*.txt"))


def _count_keyword(text_lower: str, keyword: str) -> int:
    # Word-boundary matching reduces false positives for small terms.
    escaped = re.escape(keyword.lower())
    if " " in keyword:
        return len(re.findall(escaped, text_lower))
    return len(re.findall(rf"\b{escaped}\b", text_lower))


def _snippet(text: str, keyword: str, radius: int = 150) -> str:
    lower = text.lower()
    idx = lower.find(keyword.lower())
    if idx < 0:
        return ""
    start = max(0, idx - radius)
    end = min(len(text), idx + len(keyword) + radius)
    snippet = text[start:end].replace("\n", " ")
    snippet = re.sub(r"\s+", " ", snippet).strip()
    return ("..." if start else "") + snippet + ("..." if end < len(text) else "")


def scan_topic_matrix(projects: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[TopicHit]]:
    project_names = [str(p.get("name", "Unnamed")) for p in projects]
    matrix: dict[str, dict[str, int]] = {
        topic: {project_name: 0 for project_name in project_names}
        for topic in TOPIC_KEYWORDS
    }
    evidence: list[TopicHit] = []

    for project in projects:
        project_name = str(project.get("name", "Unnamed"))
        for path in _clean_txt_files(project):
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except Exception:
                continue
            lower = text.lower()

            for topic, keywords in TOPIC_KEYWORDS.items():
                count = 0
                best_keyword = ""
                best_keyword_hits = 0
                for keyword in keywords:
                    hits = _count_keyword(lower, keyword)
                    if hits:
                        count += hits
                        if hits > best_keyword_hits:
                            best_keyword = keyword
                            best_keyword_hits = hits
                if count:
                    matrix[topic][project_name] = matrix[topic].get(project_name, 0) + count
                    evidence.append(
                        TopicHit(
                            project=project_name,
                            topic=topic,
                            file_name=path.name,
                            file_path=str(path),
                            matches=count,
                            snippet=_snippet(text, best_keyword or keywords[0]),
                        )
                    )

    rows: list[dict[str, Any]] = []
    for topic, project_counts in matrix.items():
        total = sum(project_counts.values())
        strongest_project = "-"
        strongest_count = 0
        if project_counts:
            strongest_project, strongest_count = max(project_counts.items(), key=lambda item: item[1])
        row = {
            "Topic": topic,
            "Total": total,
            "Strongest": strongest_project if strongest_count else "-",
        }
        for project_name in project_names:
            row[project_name] = project_counts.get(project_name, 0)
        rows.append(row)

    rows.sort(key=lambda row: int(row["Total"]), reverse=True)
    evidence.sort(key=lambda item: item.matches, reverse=True)
    return rows, evidence


def filter_topic_evidence(evidence: list[TopicHit], topic: str = "All topics", project: str = "All projects") -> list[TopicHit]:
    filtered = evidence
    if topic and topic != "All topics":
        filtered = [item for item in filtered if item.topic == topic]
    if project and project != "All projects":
        filtered = [item for item in filtered if item.project == project]
    return filtered


def export_topic_matrix(matrix_rows: list[dict[str, Any]], downloads_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = downloads_dir / f"YTIS_TOPIC_MATRIX_{stamp}.csv"
    if not matrix_rows:
        path.write_text("", encoding="utf-8")
        return path
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(matrix_rows[0].keys()))
        writer.writeheader()
        writer.writerows(matrix_rows)
    return path


def export_topic_evidence(evidence: list[TopicHit], downloads_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = downloads_dir / f"YTIS_TOPIC_EVIDENCE_{stamp}.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["project", "topic", "file_name", "file_path", "matches", "snippet"])
        writer.writeheader()
        for item in evidence:
            writer.writerow(item.__dict__)
    return path


def generate_prompt(projects: list[dict[str, Any]], focus: str) -> str:
    stats = summarize(projects)
    ranked = ranked_projects(projects)
    matrix_rows, _ = scan_topic_matrix(projects)
    top_topics = matrix_rows[:8]

    project_rows = []
    for p in ranked:
        project_rows.append(
            f"- {p.get('name', 'Unnamed')}: "
            f"{as_int(p.get('videos_found'))} videos, "
            f"{as_int(p.get('transcripts_created'))} transcripts, "
            f"{as_int(p.get('total_words')):,} words, "
            f"strength={strength(p)}, "
            f"ZIP={p.get('zip_path', '-')}"
        )

    topic_rows = []
    for row in top_topics:
        topic_rows.append(f"- {row['Topic']}: {row['Total']} matches, strongest={row['Strongest']}")

    focus = focus.strip() or "Compare all uploaded YTIS packs for business lessons, workflows, service ideas, pricing, offers, and sales patterns."

    return f"""# YTIS Multi-Project Analysis Prompt

You are analyzing multiple YouTube transcript research packs generated by YTIS.

Library context:
- Projects: {stats.projects}
- Videos: {stats.videos}
- Transcripts: {stats.transcripts}
- Total words: {stats.words:,}
- Missing subtitles: {stats.missing}
- ZIP-ready projects: {stats.zip_ready}

Projects:
{chr(10).join(project_rows)}

Local topic scan summary:
{chr(10).join(topic_rows) if topic_rows else "- No topic scan data available."}

Analysis focus:
{focus}

Instructions:
- Use the uploaded ZIP files as the primary source.
- Compare the projects/channels against each other.
- Validate or challenge the local topic scan using the transcript evidence.
- Identify repeated advice across multiple creators.
- Separate common advice from unique advice.
- Prefer concrete workflows, examples, service ideas, offer/pricing logic, sales processes, and operational systems.
- Be skeptical of generic creator advice.
- Do not invent facts that are not supported by the transcripts.
- Reference source project/channel names when possible.

Output format:
1. Executive summary.
2. Project-by-project comparison table.
3. Strongest repeated lessons across all projects.
4. Topic-by-topic comparison.
5. Unique or contradictory lessons.
6. Workflow inventory across the library.
7. Offer/pricing/service ideas relevant to Rafael Alba and Webify Digital Solutions.
8. What to ignore or verify.
9. Practical 30-day action plan.
"""


def save_prompt(text: str, downloads_dir: Path) -> Path:
    path = downloads_dir / f"YTIS_MULTI_PROJECT_PROMPT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path.write_text(text, encoding="utf-8")
    return path


def create_library_upload_bundle(projects: list[dict[str, Any]], focus: str, downloads_dir: Path) -> BundleResult:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_root = downloads_dir / f"YTIS_LIBRARY_UPLOAD_BUNDLE_{stamp}"
    bundle_root.mkdir(parents=True, exist_ok=True)

    prompt_text = generate_prompt(projects, focus)
    prompt_path = bundle_root / "YTIS_MULTI_PROJECT_ANALYSIS_PROMPT.md"
    prompt_path.write_text(prompt_text, encoding="utf-8")

    matrix_rows, evidence = scan_topic_matrix(projects)
    matrix_path = bundle_root / "YTIS_TOPIC_MATRIX.csv"
    evidence_path = bundle_root / "YTIS_TOPIC_EVIDENCE.csv"

    if matrix_rows:
        with matrix_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(matrix_rows[0].keys()))
            writer.writeheader()
            writer.writerows(matrix_rows)
    else:
        matrix_path.write_text("", encoding="utf-8")

    with evidence_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["project", "topic", "file_name", "file_path", "matches", "snippet"])
        writer.writeheader()
        for item in evidence:
            writer.writerow(item.__dict__)

    stats = summarize(projects)
    zip_dir = bundle_root / "research_packs"
    zip_dir.mkdir(parents=True, exist_ok=True)

    included: list[Path] = []
    skipped: list[str] = []

    for project in ranked_projects(projects):
        name = str(project.get("name", "Unnamed"))
        zip_value = project.get("zip_path")
        if not zip_value:
            skipped.append(f"{name}: no ZIP path")
            continue
        src = Path(str(zip_value))
        if not src.exists():
            skipped.append(f"{name}: ZIP missing")
            continue
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name).strip("_") or "project"
        dst = zip_dir / f"{safe_name}__{src.name}"
        shutil.copy2(src, dst)
        included.append(dst)

    readme = bundle_root / "README_UPLOAD_THIS_BUNDLE.md"
    readme.write_text(
        f"""# YTIS Library Upload Bundle

Created: {stamp}

Library summary:
- Projects in registry: {stats.projects}
- ZIP-ready projects copied: {len(included)}
- Videos: {stats.videos}
- Transcripts: {stats.transcripts}
- Words: {stats.words:,}
- Missing subtitles: {stats.missing}

Included analysis helpers:
- YTIS_MULTI_PROJECT_ANALYSIS_PROMPT.md
- YTIS_TOPIC_MATRIX.csv
- YTIS_TOPIC_EVIDENCE.csv

How to use:
1. Upload this bundle ZIP to ChatGPT, or upload the ZIP files inside `research_packs`.
2. Open `YTIS_MULTI_PROJECT_ANALYSIS_PROMPT.md`.
3. Paste the prompt after uploading the research packs.
4. Use the topic matrix/evidence CSV files as navigation aids, not as final truth.

Included research packs:
{chr(10).join(f"- {p.name}" for p in included) or "- None"}

Skipped:
{chr(10).join(f"- {item}" for item in skipped) or "- None"}
""",
        encoding="utf-8",
    )

    bundle_zip = downloads_dir / f"YTIS_LIBRARY_UPLOAD_BUNDLE_{stamp}.zip"
    with zipfile.ZipFile(bundle_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in bundle_root.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(bundle_root))

    return BundleResult(bundle_zip, prompt_path, readme, included, skipped)
