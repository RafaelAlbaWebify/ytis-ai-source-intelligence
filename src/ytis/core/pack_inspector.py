from __future__ import annotations

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

    def issue_text(self) -> str:
        return "; ".join(self.issues) if self.issues else "OK"


def _contains_file(names: list[str], expected: str) -> bool:
    target = expected.lower().replace("\\", "/")
    for name in names:
        if name.lower().replace("\\", "/").endswith(target):
            return True
    return False


def _count_suffix(names: list[str], suffix: str) -> int:
    suffix = suffix.lower()
    return sum(1 for name in names if name.lower().endswith(suffix))


def _count_folder_suffix(names: list[str], folder_hint: str, suffix: str) -> int:
    folder_hint = folder_hint.lower()
    suffix = suffix.lower()
    return sum(1 for name in names if folder_hint in name.lower().replace("\\", "/") and name.lower().endswith(suffix))


def inspect_pack(project: dict[str, Any]) -> PackInspection:
    zip_value = project.get("zip_path") or ""
    zip_path = Path(str(zip_value)) if zip_value else Path("")

    report = PackInspection(
        status="broken",
        zip_path=str(zip_path) if zip_value else "",
        zip_exists=bool(zip_value and zip_path.exists()),
    )

    if not zip_value:
        report.issues.append("ZIP path missing from registry")
        return report

    if not zip_path.exists():
        report.issues.append("ZIP file does not exist")
        return report

    report.zip_size_mb = round(zip_path.stat().st_size / (1024 * 1024), 2)

    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            names = [info.filename for info in infos]

            report.total_files = len(infos)
            report.raw_srt_count = _count_folder_suffix(names, "raw_srt", ".srt")
            report.clean_txt_count = _count_folder_suffix(names, "clean_txt", ".txt")
            report.md_count = _count_suffix(names, ".md")
            report.csv_count = _count_suffix(names, ".csv")
            report.json_count = _count_suffix(names, ".json")
            report.expected_present = {expected: _contains_file(names, expected) for expected in EXPECTED_FILES}

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
        return report
    except Exception as exc:
        report.issues.append(f"ZIP inspection failed: {exc}")
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

    if report.issues:
        report.status = "review" if report.zip_exists and report.total_files > 0 else "broken"
    else:
        report.status = "upload-ready"

    return report
