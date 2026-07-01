from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


EXPECTED_FILES = [
    "project_summary.json",
    "transcript_index.csv",
    "missing_subtitles_report.csv",
    "README_ANALYSIS_PROMPT.md",
    "ALL_TRANSCRIPTS_COMBINED.md",
]

PREVIEW_IMAGE = "source_preview/source_preview.jpg"
PREVIEW_METADATA = "source_preview/source_preview_metadata.json"


@dataclass
class PackInspection:
    status: str
    zip_path: str
    zip_exists: bool
    zip_size_mb: float = 0.0
    total_files: int = 0
    raw_srt_count: int = 0
    clean_txt_count: int = 0
    md_count: int = 0
    csv_count: int = 0
    json_count: int = 0
    expected_present: dict[str, bool] = field(default_factory=dict)
    largest_files: list[dict[str, Any]] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    # Source preview validation
    preview_project_image_exists: bool = False
    preview_project_metadata_exists: bool = False
    preview_project_image_path: str = ""
    preview_project_metadata_path: str = ""
    preview_project_image_size_kb: float = 0.0
    preview_zip_image_exists: bool = False
    preview_zip_metadata_exists: bool = False
    preview_zip_image_size_kb: float = 0.0
    preview_title: str = ""
    preview_subtitle: str = ""
    preview_status: str = "missing"

    def issue_text(self) -> str:
        return "; ".join(self.issues) if self.issues else "OK"


def _contains_file(names: list[str], expected: str) -> bool:
    target = expected.lower().replace("\\", "/")
    for name in names:
        if name.lower().replace("\\", "/").endswith(target):
            return True
    return False


def _zip_info_for(names_to_info: dict[str, zipfile.ZipInfo], expected: str) -> zipfile.ZipInfo | None:
    target = expected.lower().replace("\\", "/")
    for name, info in names_to_info.items():
        if name.lower().replace("\\", "/").endswith(target):
            return info
    return None


def _count_suffix(names: list[str], suffix: str) -> int:
    suffix = suffix.lower()
    return sum(1 for name in names if name.lower().endswith(suffix))


def _count_folder_suffix(names: list[str], folder_hint: str, suffix: str) -> int:
    folder_hint = folder_hint.lower()
    suffix = suffix.lower()
    return sum(1 for name in names if folder_hint in name.lower().replace("\\", "/") and name.lower().endswith(suffix))


def _safe_project_dir(project: dict[str, Any]) -> Path | None:
    value = project.get("project_dir")
    if not value:
        return None
    try:
        path = Path(str(value))
        return path if path.exists() else None
    except Exception:
        return None


def _load_preview_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _inspect_project_preview(report: PackInspection, project: dict[str, Any]) -> None:
    project_dir = _safe_project_dir(project)
    if not project_dir:
        return

    preview_image = project_dir / PREVIEW_IMAGE
    preview_metadata = project_dir / PREVIEW_METADATA

    report.preview_project_image_exists = preview_image.exists()
    report.preview_project_metadata_exists = preview_metadata.exists()
    report.preview_project_image_path = str(preview_image)
    report.preview_project_metadata_path = str(preview_metadata)

    if preview_image.exists():
        report.preview_project_image_size_kb = round(preview_image.stat().st_size / 1024, 1)

    metadata = _load_preview_metadata(preview_metadata)
    report.preview_title = str(metadata.get("title") or "")
    report.preview_subtitle = str(metadata.get("subtitle") or "")


def _finalize_preview_status(report: PackInspection) -> None:
    if report.preview_project_image_exists and report.preview_zip_image_exists:
        report.preview_status = "included"
    elif report.preview_project_image_exists and not report.preview_zip_image_exists:
        report.preview_status = "project-only"
    elif report.preview_zip_image_exists and not report.preview_project_image_exists:
        report.preview_status = "zip-only"
    else:
        report.preview_status = "missing"

    if not report.preview_project_image_exists:
        report.issues.append("source preview image missing from project folder")
    if not report.preview_zip_image_exists:
        report.issues.append("source preview image missing from ZIP")
    if report.preview_project_image_exists and report.preview_project_image_size_kb < 5:
        report.issues.append("source preview image is suspiciously small")
    if report.preview_zip_image_exists and report.preview_zip_image_size_kb < 5:
        report.issues.append("source preview image inside ZIP is suspiciously small")


def inspect_pack(project: dict[str, Any]) -> PackInspection:
    zip_value = project.get("zip_path") or ""
    zip_path = Path(str(zip_value)) if zip_value else Path("")

    report = PackInspection(
        status="broken",
        zip_path=str(zip_path) if zip_value else "",
        zip_exists=bool(zip_value and zip_path.exists()),
    )

    _inspect_project_preview(report, project)

    if not zip_value:
        report.issues.append("ZIP path missing from registry")
        _finalize_preview_status(report)
        return report

    if not zip_path.exists():
        report.issues.append("ZIP file does not exist")
        _finalize_preview_status(report)
        return report

    report.zip_size_mb = round(zip_path.stat().st_size / (1024 * 1024), 2)

    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            names = [info.filename for info in infos]
            names_to_info = {info.filename: info for info in infos}

            report.total_files = len(infos)
            report.raw_srt_count = _count_folder_suffix(names, "raw_srt", ".srt")
            report.clean_txt_count = _count_folder_suffix(names, "clean_txt", ".txt")
            report.md_count = _count_suffix(names, ".md")
            report.csv_count = _count_suffix(names, ".csv")
            report.json_count = _count_suffix(names, ".json")
            report.expected_present = {expected: _contains_file(names, expected) for expected in EXPECTED_FILES}

            zip_preview_info = _zip_info_for(names_to_info, PREVIEW_IMAGE)
            zip_preview_meta_info = _zip_info_for(names_to_info, PREVIEW_METADATA)
            report.preview_zip_image_exists = zip_preview_info is not None
            report.preview_zip_metadata_exists = zip_preview_meta_info is not None
            if zip_preview_info:
                report.preview_zip_image_size_kb = round(zip_preview_info.file_size / 1024, 1)

            largest = sorted(infos, key=lambda item: item.file_size, reverse=True)[:10]
            report.largest_files = [
                {
                    "name": item.filename,
                    "size_mb": round(item.file_size / (1024 * 1024), 2),
                    "size_bytes": item.file_size,
                }
                for item in largest
            ]

    except zipfile.BadZipFile:
        report.issues.append("ZIP is invalid or corrupted")
        _finalize_preview_status(report)
        return report
    except Exception as exc:
        report.issues.append(f"ZIP inspection failed: {exc}")
        _finalize_preview_status(report)
        return report

    if report.total_files == 0:
        report.issues.append("ZIP is empty")
    if report.raw_srt_count == 0:
        report.issues.append("no raw_srt SRT files found")
    if report.clean_txt_count == 0:
        report.issues.append("no clean_txt TXT files found")
    if report.raw_srt_count and report.clean_txt_count and report.raw_srt_count != report.clean_txt_count:
        report.issues.append("raw_srt and clean_txt counts differ")

    for expected, present in report.expected_present.items():
        if not present:
            if expected in {"project_summary.json", "transcript_index.csv", "ALL_TRANSCRIPTS_COMBINED.md"}:
                report.issues.append(f"missing expected file: {expected}")

    _finalize_preview_status(report)

    if report.issues:
        report.status = "review" if report.zip_exists and report.total_files > 0 else "broken"
    else:
        report.status = "upload-ready"

    return report
