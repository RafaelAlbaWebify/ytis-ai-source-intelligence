from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

FOCUS_OPTIONS = [
    "Business lessons", "Offers and pricing", "Lead generation",
    "Workflow extraction", "Technical learning", "Webify service ideas", "Custom",
]

TOPIC_OPTIONS = [
    "All topics", "Pricing", "Offer", "Lead generation", "Sales call",
    "Cold email", "Funnel", "Agency", "MSP", "Niche", "Onboarding",
    "Content", "Ads", "Workflow", "Custom",
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
    return clean if len(clean) <= max_chars else clean[:max_chars].rstrip() + "..."

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
    return _record_from_data(folder, metadata)  # type: ignore[return-value]

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
