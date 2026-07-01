from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from ytis.core.models import TranscriptRecord

LogCallback = Callable[[str, float | None], None]

TIMECODE_RE = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}")
VIDEO_ID_RE = re.compile(r"\[([A-Za-z0-9_-]{6,})\]")


def clean_srt_text(srt_text: str) -> str:
    clean_lines: list[str] = []

    for raw_line in srt_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.isdigit():
            continue
        if TIMECODE_RE.match(line):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = line.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        clean_lines.append(line)

    text = " ".join(clean_lines)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_filename_metadata(path: Path) -> tuple[str, str, str]:
    stem = path.stem

    match = VIDEO_ID_RE.search(stem)
    video_id = match.group(1) if match else ""

    title_part = stem[: match.start()].strip() if match else stem
    title_part = title_part.rstrip(" .-_")

    upload_date = ""
    title = title_part

    if " - " in title_part:
        possible_date, rest = title_part.split(" - ", 1)
        if possible_date.isdigit() and len(possible_date) == 8:
            upload_date = possible_date
            title = rest.strip()

    return upload_date, title, video_id


def clean_all_srt(raw_srt_dir: Path, clean_txt_dir: Path, callback: LogCallback | None = None) -> list[TranscriptRecord]:
    clean_txt_dir.mkdir(parents=True, exist_ok=True)

    for old_txt in clean_txt_dir.glob("*.txt"):
        old_txt.unlink(missing_ok=True)

    records: list[TranscriptRecord] = []

    srt_files = sorted(raw_srt_dir.glob("*.srt"))
    total = max(len(srt_files), 1)

    for idx, srt_path in enumerate(srt_files, start=1):
        text_raw = srt_path.read_text(encoding="utf-8-sig", errors="replace")
        text_clean = clean_srt_text(text_raw)

        upload_date, title, video_id = parse_filename_metadata(srt_path)
        txt_path = clean_txt_dir / f"{srt_path.stem}.txt"
        txt_path.write_text(text_clean, encoding="utf-8")

        word_count = len(text_clean.split()) if text_clean else 0
        records.append(
            TranscriptRecord(
                filename=srt_path.name,
                video_id=video_id,
                title=title,
                upload_date=upload_date,
                txt_file=txt_path.name,
                word_count=word_count,
                char_count=len(text_clean),
            )
        )

        if callback and (idx % 5 == 0 or idx == len(srt_files)):
            callback(f"Cleaned {idx}/{len(srt_files)} SRT files", 0.50 + (idx / total) * 0.20)

    if callback:
        callback(f"TXT files created: {len(records)}", 0.72)

    return records
