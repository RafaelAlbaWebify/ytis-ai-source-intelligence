from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


VIDEO_ID_RE = re.compile(r"\[([A-Za-z0-9_-]{6,})\]")


@dataclass
class HygieneReport:
    status: str
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    srt_files: int = 0
    srt_unique_ids: int = 0
    txt_files: int = 0
    txt_unique_ids: int = 0
    duplicate_ids: list[str] = field(default_factory=list)
    has_summary: bool = False
    has_index: bool = False
    has_missing_report: bool = False
    has_combined_md: bool = False
    has_zip: bool = False

    def issue_text(self) -> str:
        values = self.issues + self.warnings
        return "; ".join(values) if values else "OK"


def _video_id_from_name(name: str) -> str:
    match = VIDEO_ID_RE.search(name)
    return match.group(1) if match else ""


def _count_unique_ids(files: list[Path]) -> tuple[int, list[str]]:
    ids: list[str] = []
    for path in files:
        video_id = _video_id_from_name(path.name)
        if video_id:
            ids.append(video_id)

    duplicates = sorted({video_id for video_id in ids if ids.count(video_id) > 1})
    return len(set(ids)), duplicates


def _safe_path(project: dict[str, Any], key: str) -> Path | None:
    value = project.get(key)
    if not value:
        return None
    try:
        return Path(str(value))
    except Exception:
        return None


def audit_project(project: dict[str, Any]) -> HygieneReport:
    report = HygieneReport(status="clean")

    project_dir = _safe_path(project, "project_dir")
    zip_path = _safe_path(project, "zip_path")

    if not project_dir or not project_dir.exists():
        report.status = "broken"
        report.issues.append("project folder missing")
        return report

    raw_srt_dir = project_dir / "raw_srt"
    clean_txt_dir = project_dir / "clean_txt"
    summary_path = project_dir / "project_summary.json"
    index_path = project_dir / "transcript_index.csv"
    missing_path = project_dir / "missing_subtitles_report.csv"
    combined_path = project_dir / "ALL_TRANSCRIPTS_COMBINED.md"

    report.has_summary = summary_path.exists()
    report.has_index = index_path.exists()
    report.has_missing_report = missing_path.exists()
    report.has_combined_md = combined_path.exists()
    report.has_zip = bool(zip_path and zip_path.exists())

    srt_files = sorted(raw_srt_dir.glob("*.srt")) if raw_srt_dir.exists() else []
    txt_files = sorted(clean_txt_dir.glob("*.txt")) if clean_txt_dir.exists() else []

    report.srt_files = len(srt_files)
    report.txt_files = len(txt_files)
    report.srt_unique_ids, duplicate_srt_ids = _count_unique_ids(srt_files)
    report.txt_unique_ids, duplicate_txt_ids = _count_unique_ids(txt_files)
    report.duplicate_ids = sorted(set(duplicate_srt_ids + duplicate_txt_ids))

    if not report.has_summary:
        report.issues.append("summary missing")
    if not report.has_index:
        report.warnings.append("index missing")
    if not report.has_missing_report:
        report.warnings.append("missing report absent")
    if not report.has_combined_md:
        report.warnings.append("combined MD missing")
    if not report.has_zip:
        report.issues.append("ZIP missing")

    if report.srt_files == 0:
        report.issues.append("no SRT files")
    if report.txt_files == 0:
        report.issues.append("no TXT files")
    if report.srt_files != report.txt_files:
        report.issues.append("SRT/TXT count mismatch")
    if report.srt_unique_ids and report.srt_files != report.srt_unique_ids:
        report.issues.append("duplicate SRT video IDs")
    if report.txt_unique_ids and report.txt_files != report.txt_unique_ids:
        report.issues.append("duplicate TXT video IDs")
    if report.duplicate_ids:
        report.issues.append("duplicate IDs: " + ",".join(report.duplicate_ids[:5]))

    registry_transcripts = project.get("transcripts_created")
    try:
        if registry_transcripts is not None and int(registry_transcripts) != report.txt_files:
            report.warnings.append("registry transcript count differs from files")
    except Exception:
        pass

    if report.issues:
        report.status = "broken"
    elif report.warnings:
        report.status = "review"
    else:
        report.status = "clean"

    return report


def audit_projects(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for project in projects:
        report = audit_project(project)
        item = dict(project)
        item["_hygiene"] = report
        item["_hygiene_status"] = report.status
        item["_hygiene_issues"] = report.issue_text()
        item["_srt_files"] = report.srt_files
        item["_txt_files"] = report.txt_files
        item["_duplicate_ids"] = ",".join(report.duplicate_ids)
        enriched.append(item)
    return enriched


def read_project_summary(project_dir: Path) -> dict[str, Any]:
    path = project_dir / "project_summary.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
