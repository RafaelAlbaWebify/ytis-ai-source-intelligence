from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VIDEO_ID_RE = re.compile(r"\[([A-Za-z0-9_-]{6,})\]")


@dataclass
class TranscriptInfo:
    path: Path
    file_name: str
    video_id: str
    size_kb: float
    word_count: int
    line_count: int
    char_count: int
    text: str


def video_id_from_name(name: str) -> str:
    match = VIDEO_ID_RE.search(name)
    return match.group(1) if match else ""


def list_transcripts(project: dict[str, Any]) -> list[Path]:
    project_dir = Path(str(project.get("project_dir", "")))
    clean_dir = project_dir / "clean_txt"
    if not clean_dir.exists():
        return []
    return sorted(clean_dir.glob("*.txt"))


def read_transcript(path: str | Path) -> TranscriptInfo:
    txt_path = Path(path)
    text = txt_path.read_text(encoding="utf-8", errors="replace")
    words = re.findall(r"\b\w+\b", text)
    lines = text.splitlines()
    return TranscriptInfo(
        path=txt_path,
        file_name=txt_path.name,
        video_id=video_id_from_name(txt_path.name),
        size_kb=round(txt_path.stat().st_size / 1024, 1) if txt_path.exists() else 0.0,
        word_count=len(words),
        line_count=len(lines),
        char_count=len(text),
        text=text,
    )


def search_inside_text(text: str, query: str, radius: int = 180) -> list[str]:
    needle = (query or "").strip()
    if not needle:
        return []
    lower = text.lower()
    needle_lower = needle.lower()
    snippets: list[str] = []
    start = 0
    while True:
        idx = lower.find(needle_lower, start)
        if idx < 0:
            break
        snippet_start = max(0, idx - radius)
        snippet_end = min(len(text), idx + len(needle) + radius)
        snippet = text[snippet_start:snippet_end].replace("\r", " ").replace("\n", " ")
        snippet = re.sub(r"\s+", " ", snippet).strip()
        if snippet_start > 0:
            snippet = "..." + snippet
        if snippet_end < len(text):
            snippet = snippet + "..."
        snippets.append(snippet)
        start = idx + len(needle)
        if len(snippets) >= 50:
            break
    return snippets
