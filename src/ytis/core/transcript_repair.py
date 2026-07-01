from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


WORD_RE = re.compile(r"\b\w+(?:'\w+)?\b|\[[^\]]+\]", re.UNICODE)


@dataclass
class RepairStats:
    file_name: str
    path: str
    original_words: int
    repaired_words: int
    removed_words: int
    removed_percent: float
    changed: bool


@dataclass
class ProjectRepairReport:
    project_name: str
    project_dir: str
    clean_txt_dir: str
    backup_dir: str
    files_checked: int
    files_changed: int
    original_words: int
    repaired_words: int
    removed_words: int
    removed_percent: float
    file_reports: list[RepairStats]


def _tokens(text: str) -> list[str]:
    return WORD_RE.findall(text)


def _norm(token: str) -> str:
    return token.lower().strip()


def _collapse_repeated_token_runs(tokens: list[str], max_ngram: int = 18, min_ngram: int = 2) -> list[str]:
    output = list(tokens)
    changed = True

    while changed:
        changed = False
        i = 0
        while i < len(output):
            removed_here = False
            max_size = min(max_ngram, (len(output) - i) // 2)
            for size in range(max_size, min_ngram - 1, -1):
                a = [_norm(t) for t in output[i:i + size]]
                b = [_norm(t) for t in output[i + size:i + 2 * size]]
                if a and a == b:
                    del output[i + size:i + 2 * size]
                    changed = True
                    removed_here = True
                    break
            if not removed_here:
                i += 1

    return output


def _repair_text(text: str) -> str:
    tokens = _tokens(text)
    if not tokens:
        return text

    repaired = _collapse_repeated_token_runs(tokens)
    text_out = " ".join(repaired)
    text_out = re.sub(r"\s+([,.;:!?])", r"\1", text_out)
    text_out = re.sub(r"\s+", " ", text_out).strip()
    return text_out + "\n"


def analyze_file(path: Path) -> RepairStats:
    original = path.read_text(encoding="utf-8", errors="replace")
    repaired = _repair_text(original)
    original_words = len(_tokens(original))
    repaired_words = len(_tokens(repaired))
    removed = max(0, original_words - repaired_words)
    percent = round((removed / original_words) * 100, 1) if original_words else 0.0
    return RepairStats(
        file_name=path.name,
        path=str(path),
        original_words=original_words,
        repaired_words=repaired_words,
        removed_words=removed,
        removed_percent=percent,
        changed=original.strip() != repaired.strip(),
    )


def analyze_project(project: dict[str, Any]) -> ProjectRepairReport:
    project_name = str(project.get("name", "Unnamed"))
    project_dir = Path(str(project.get("project_dir", "")))
    clean_txt_dir = project_dir / "clean_txt"

    reports: list[RepairStats] = []
    if clean_txt_dir.exists():
        for path in sorted(clean_txt_dir.glob("*.txt")):
            reports.append(analyze_file(path))

    original_words = sum(item.original_words for item in reports)
    repaired_words = sum(item.repaired_words for item in reports)
    removed_words = max(0, original_words - repaired_words)
    removed_percent = round((removed_words / original_words) * 100, 1) if original_words else 0.0

    return ProjectRepairReport(
        project_name=project_name,
        project_dir=str(project_dir),
        clean_txt_dir=str(clean_txt_dir),
        backup_dir="",
        files_checked=len(reports),
        files_changed=sum(1 for item in reports if item.changed),
        original_words=original_words,
        repaired_words=repaired_words,
        removed_words=removed_words,
        removed_percent=removed_percent,
        file_reports=reports,
    )


def repair_project(project: dict[str, Any]) -> ProjectRepairReport:
    project_name = str(project.get("name", "Unnamed"))
    project_dir = Path(str(project.get("project_dir", "")))
    clean_txt_dir = project_dir / "clean_txt"

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = project_dir / f"clean_txt_backup_before_dedupe_{stamp}"

    if not clean_txt_dir.exists():
        return analyze_project(project)

    backup_dir.mkdir(parents=True, exist_ok=True)

    reports: list[RepairStats] = []
    for path in sorted(clean_txt_dir.glob("*.txt")):
        original = path.read_text(encoding="utf-8", errors="replace")
        repaired = _repair_text(original)
        shutil.copy2(path, backup_dir / path.name)

        if original.strip() != repaired.strip():
            path.write_text(repaired, encoding="utf-8")

        original_words = len(_tokens(original))
        repaired_words = len(_tokens(repaired))
        removed = max(0, original_words - repaired_words)
        percent = round((removed / original_words) * 100, 1) if original_words else 0.0
        reports.append(
            RepairStats(
                file_name=path.name,
                path=str(path),
                original_words=original_words,
                repaired_words=repaired_words,
                removed_words=removed,
                removed_percent=percent,
                changed=original.strip() != repaired.strip(),
            )
        )

    original_words = sum(item.original_words for item in reports)
    repaired_words = sum(item.repaired_words for item in reports)
    removed_words = max(0, original_words - repaired_words)
    removed_percent = round((removed_words / original_words) * 100, 1) if original_words else 0.0

    return ProjectRepairReport(
        project_name=project_name,
        project_dir=str(project_dir),
        clean_txt_dir=str(clean_txt_dir),
        backup_dir=str(backup_dir),
        files_checked=len(reports),
        files_changed=sum(1 for item in reports if item.changed),
        original_words=original_words,
        repaired_words=repaired_words,
        removed_words=removed_words,
        removed_percent=removed_percent,
        file_reports=reports,
    )
