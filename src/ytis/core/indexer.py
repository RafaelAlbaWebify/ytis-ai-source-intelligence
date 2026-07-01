from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable

from ytis.core.models import TranscriptRecord, VideoRecord

LogCallback = Callable[[str, float | None], None]


def write_transcript_index(records: list[TranscriptRecord], output_path: Path, callback: LogCallback | None = None) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["upload_date", "title", "video_id", "srt_file", "txt_file", "word_count", "char_count"],
        )
        writer.writeheader()
        for rec in records:
            writer.writerow(
                {
                    "upload_date": rec.upload_date,
                    "title": rec.title,
                    "video_id": rec.video_id,
                    "srt_file": rec.filename,
                    "txt_file": rec.txt_file,
                    "word_count": rec.word_count,
                    "char_count": rec.char_count,
                }
            )

    if callback:
        callback(f"Transcript index written: {output_path.name}", 0.78)


def write_missing_report(videos: list[VideoRecord], records: list[TranscriptRecord], output_path: Path, callback: LogCallback | None = None) -> None:
    transcript_ids = {r.video_id for r in records if r.video_id}
    missing = [v for v in videos if v.video_id and v.video_id not in transcript_ids]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["video_id", "title", "upload_date", "duration", "webpage_url"])
        writer.writeheader()
        for video in missing:
            writer.writerow(
                {
                    "video_id": video.video_id,
                    "title": video.title,
                    "upload_date": video.upload_date,
                    "duration": video.duration,
                    "webpage_url": video.webpage_url,
                }
            )

    if callback:
        callback(f"Missing subtitles report written: {len(missing)} missing", 0.82)
