from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


FOCUS_OPTIONS = [
    "Business lessons",
    "Offers and pricing",
    "Lead generation",
    "Workflow extraction",
    "Technical learning",
    "Webify service ideas",
    "Custom",
]

TOPIC_OPTIONS = [
    "All topics",
    "Pricing",
    "Offer",
    "Lead generation",
    "Sales call",
    "Cold email",
    "Funnel",
    "Agency",
    "MSP",
    "Niche",
    "Onboarding",
    "Content",
    "Ads",
    "Workflow",
    "Custom",
]

TRACKED_TOPICS = [
    "Pricing",
    "Offer",
    "Lead generation",
    "Workflow extraction",
    "Technical learning",
    "Webify service ideas",
]


@dataclass
class AnalysisRecord:
    record_id: str
    title: str
    created_at: str
    projects: list[str]
    topic: str
    focus_preset: str
    source_bundle: str
    source_evidence_pack: str
    folder: Path
    analysis_path: Path
    metadata_path: Path
    word_count: int
    summary: str


def safe_slug(text: str, fallback: str = "analysis") -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip())
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:80] or fallback


def analysis_root(project_root: Path) -> Path:
    path = project_root / "analysis_results"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def _summary(text: str, max_chars: int = 240) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if len(clean) <= max_chars:
        return clean
    return clean[:max_chars].rstrip() + "..."


def save_analysis(
    project_root: Path,
    title: str,
    analysis_text: str,
    projects: list[str],
    topic: str,
    focus_preset: str,
    source_bundle: str = "",
    source_evidence_pack: str = "",
    notes: str = "",
) -> AnalysisRecord:
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    title_clean = title.strip() or "Untitled analysis"
    record_id = f"{stamp}_{safe_slug(title_clean)}"
    folder = analysis_root(project_root) / record_id
    folder.mkdir(parents=True, exist_ok=True)

    analysis_path = folder / "analysis.md"
    metadata_path = folder / "metadata.json"
    notes_path = folder / "notes.md"

    body = analysis_text.strip()
    md = f"# {title_clean}\n\n"
    md += f"Created: {created_at}\n\n"
    md += f"Projects: {', '.join(projects) if projects else '-'}\n\n"
    md += f"Topic: {topic or '-'}\n\n"
    md += f"Focus preset: {focus_preset or '-'}\n\n"
    if source_bundle:
        md += f"Source bundle: `{source_bundle}`\n\n"
    if source_evidence_pack:
        md += f"Source evidence pack: `{source_evidence_pack}`\n\n"
    md += "---\n\n" + body + "\n"
    analysis_path.write_text(md, encoding="utf-8")

    notes_path.write_text((notes.strip() + "\n") if notes.strip() else "", encoding="utf-8")

    metadata = {
        "record_id": record_id,
        "title": title_clean,
        "created_at": created_at,
        "projects": projects,
        "topic": topic,
        "focus_preset": focus_preset,
        "source_bundle": source_bundle,
        "source_evidence_pack": source_evidence_pack,
        "analysis_path": str(analysis_path),
        "notes_path": str(notes_path),
        "word_count": _word_count(body),
        "summary": _summary(body),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return _record_from_data(folder, metadata)


def _record_from_data(folder: Path, data: dict[str, Any]) -> AnalysisRecord:
    return AnalysisRecord(
        record_id=str(data.get("record_id") or folder.name),
        title=str(data.get("title") or folder.name),
        created_at=str(data.get("created_at") or ""),
        projects=list(data.get("projects") or []),
        topic=str(data.get("topic") or ""),
        focus_preset=str(data.get("focus_preset") or ""),
        source_bundle=str(data.get("source_bundle") or ""),
        source_evidence_pack=str(data.get("source_evidence_pack") or ""),
        folder=folder,
        analysis_path=folder / "analysis.md",
        metadata_path=folder / "metadata.json",
        word_count=int(data.get("word_count") or 0),
        summary=str(data.get("summary") or ""),
    )


def _record_from_folder(folder: Path) -> AnalysisRecord | None:
    metadata_path = folder / "metadata.json"
    analysis_path = folder / "analysis.md"
    if not metadata_path.exists() or not analysis_path.exists():
        return None
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        return _record_from_data(folder, data)
    except Exception:
        return None


def list_analyses(project_root: Path) -> list[AnalysisRecord]:
    root = analysis_root(project_root)
    records: list[AnalysisRecord] = []
    for folder in sorted(root.iterdir(), reverse=True):
        if folder.is_dir():
            record = _record_from_folder(folder)
            if record:
                records.append(record)
    return records


def filter_analyses(
    records: list[AnalysisRecord],
    project: str = "All projects",
    topic: str = "All topics",
    focus: str = "All focus presets",
    text: str = "",
) -> list[AnalysisRecord]:
    result = records
    if project and project != "All projects":
        result = [r for r in result if project in r.projects]
    if topic and topic != "All topics":
        result = [r for r in result if r.topic == topic]
    if focus and focus != "All focus presets":
        result = [r for r in result if r.focus_preset == focus]
    if text.strip():
        q = text.lower().strip()
        result = [
            r for r in result
            if q in r.title.lower()
            or q in r.summary.lower()
            or q in " ".join(r.projects).lower()
            or q in r.topic.lower()
            or q in r.focus_preset.lower()
        ]
    return result


def read_analysis(record: AnalysisRecord) -> str:
    try:
        return record.analysis_path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return ""


def analysis_stats(records: list[AnalysisRecord]) -> dict[str, Any]:
    projects = sorted({p for r in records for p in r.projects})
    topics = sorted({r.topic for r in records if r.topic})
    focus = sorted({r.focus_preset for r in records if r.focus_preset})
    return {
        "records": len(records),
        "projects": len(projects),
        "topics": len(topics),
        "focus_presets": len(focus),
        "words": sum(r.word_count for r in records),
    }


def coverage_rows(records: list[AnalysisRecord], project_names: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for project in project_names:
        row: dict[str, Any] = {"Project": project}
        project_records = [r for r in records if project in r.projects]
        row["Total"] = len(project_records)
        for topic in TRACKED_TOPICS:
            count = sum(
                1 for r in project_records
                if r.topic == topic
                or r.focus_preset == topic
                or (topic == "Workflow extraction" and r.focus_preset == "Workflow extraction")
                or (topic == "Technical learning" and r.focus_preset == "Technical learning")
                or (topic == "Webify service ideas" and r.focus_preset == "Webify service ideas")
            )
            row[topic] = count
        rows.append(row)
    return rows


def generate_continue_prompt(record: AnalysisRecord) -> str:
    analysis = read_analysis(record)
    return f"""# Continue YTIS Analysis

You previously analyzed a YTIS research bundle/evidence pack.

Saved analysis metadata:
- Title: {record.title}
- Created: {record.created_at}
- Projects: {', '.join(record.projects) if record.projects else '-'}
- Topic: {record.topic or '-'}
- Focus preset: {record.focus_preset or '-'}
- Source bundle: {record.source_bundle or '-'}
- Source evidence pack: {record.source_evidence_pack or '-'}

Task:
Continue from the saved analysis below. Do not repeat the whole analysis. Instead:
1. Extract the most actionable points.
2. Identify weak assumptions or advice that needs validation.
3. Convert the analysis into concrete next actions for Rafael/Webify.
4. Propose the next YTIS evidence pack or prompt to run.
5. Separate what is evidence-backed from what is interpretation.

Saved analysis:
---
{analysis}
"""


def export_analyses_zip(records: list[AnalysisRecord], downloads_dir: Path, name: str = "YTIS_ANALYSIS_EXPORT") -> Path:
    downloads_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = downloads_dir / f"{safe_slug(name)}_{stamp}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest: list[dict[str, Any]] = []
        for record in records:
            base = f"{record.record_id}/"
            if record.analysis_path.exists():
                zf.write(record.analysis_path, base + "analysis.md")
            if record.metadata_path.exists():
                zf.write(record.metadata_path, base + "metadata.json")
            notes_path = record.folder / "notes.md"
            if notes_path.exists():
                zf.write(notes_path, base + "notes.md")
            manifest.append({
                "record_id": record.record_id,
                "title": record.title,
                "created_at": record.created_at,
                "projects": record.projects,
                "topic": record.topic,
                "focus_preset": record.focus_preset,
                "word_count": record.word_count,
                "summary": record.summary,
            })
        zf.writestr("MANIFEST.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        zf.writestr(
            "README.md",
            "# YTIS Analysis Export\n\n"
            "This ZIP contains saved ChatGPT analyses from the YTIS Analysis Inbox.\n"
            "Each folder contains analysis.md, metadata.json, and notes.md when available.\n",
        )
    return zip_path
