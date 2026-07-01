from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


VIDEO_ID_RE = re.compile(r"\[([A-Za-z0-9_-]{6,})\]")


@dataclass
class SearchResult:
    project: str
    file_name: str
    file_path: str
    video_id: str
    match_count: int
    snippet: str


def _video_id_from_name(name: str) -> str:
    match = VIDEO_ID_RE.search(name)
    return match.group(1) if match else ""


def _snippet(text: str, needle_lower: str, radius: int = 240) -> str:
    lower = text.lower()
    idx = lower.find(needle_lower)
    if idx < 0:
        return ""
    start = max(0, idx - radius)
    end = min(len(text), idx + len(needle_lower) + radius)
    raw = text[start:end].replace("\r", " ").replace("\n", " ")
    compact = re.sub(r"\s+", " ", raw).strip()
    if start > 0:
        compact = "..." + compact
    if end < len(text):
        compact = compact + "..."
    return compact


def _text_files(project: dict[str, Any]) -> list[Path]:
    project_dir = Path(str(project.get("project_dir", "")))
    clean_dir = project_dir / "clean_txt"
    if not clean_dir.exists():
        return []
    return sorted(clean_dir.glob("*.txt"))


def search_transcripts(
    projects: list[dict[str, Any]],
    query: str,
    project_name: str = "All projects",
    limit: int = 100,
) -> list[SearchResult]:
    needle = (query or "").strip()
    if not needle:
        return []

    needle_lower = needle.lower()
    selected = []
    for project in projects:
        name = str(project.get("name", "Unnamed"))
        if project_name == "All projects" or name == project_name:
            selected.append(project)

    results: list[SearchResult] = []

    for project in selected:
        project_label = str(project.get("name", "Unnamed"))
        for txt in _text_files(project):
            try:
                content = txt.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            content_lower = content.lower()
            count = content_lower.count(needle_lower)
            if count <= 0:
                continue

            results.append(
                SearchResult(
                    project=project_label,
                    file_name=txt.name,
                    file_path=str(txt),
                    video_id=_video_id_from_name(txt.name),
                    match_count=count,
                    snippet=_snippet(content, needle_lower),
                )
            )

            if len(results) >= limit:
                return results

    results.sort(key=lambda item: item.match_count, reverse=True)
    return results[:limit]


def export_results(results: list[SearchResult], downloads_dir: Path, query: str) -> Path:
    safe_query = re.sub(r"[^A-Za-z0-9_-]+", "_", query.strip())[:40] or "search"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = downloads_dir / f"YTIS_SEARCH_RESULTS_{safe_query}_{stamp}.csv"

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["project", "file_name", "video_id", "match_count", "snippet", "file_path"],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "project": result.project,
                    "file_name": result.file_name,
                    "video_id": result.video_id,
                    "match_count": result.match_count,
                    "snippet": result.snippet,
                    "file_path": result.file_path,
                }
            )

    return path
