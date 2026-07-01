from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal

from ytis.core.cleaner import clean_all_srt
from ytis.core.downloader import (
    assert_unique_subtitles,
    download_subtitles,
    fetch_channel_video_index,
    keep_one_subtitle_per_video,
)
from ytis.core.indexer import write_missing_report, write_transcript_index
from ytis.core.packager import create_zip, write_combined_markdown
from ytis.core.paths import safe_name
from ytis.core.prompts import write_analysis_prompt
from ytis.core.registry import upsert_project


LogCallback = Callable[[str, float | None], None]
BuildMode = Literal["reuse", "refresh", "repackage"]


@dataclass
class BuildOptions:
    name: str
    url: str
    lang: str
    output_downloads: Path
    base_projects_dir: Path
    mode: BuildMode = "reuse"


@dataclass
class BuildResult:
    project_dir: Path
    zip_path: Path
    videos_found: int
    transcripts_created: int
    total_words: int
    missing_subtitles: int
    mode: str


def build_research_pack(options: BuildOptions, callback: LogCallback | None = None) -> BuildResult:
    project_name = safe_name(options.name)
    mode = options.mode if options.mode in {"reuse", "refresh", "repackage"} else "reuse"

    project_dir = options.base_projects_dir / f"{project_name}_YTIS_RESEARCH_READY"
    raw_srt_dir = project_dir / "raw_srt"
    clean_txt_dir = project_dir / "clean_txt"

    master_file = project_dir / "ALL_TRANSCRIPTS_COMBINED.md"
    index_file = project_dir / "transcript_index.csv"
    missing_file = project_dir / "missing_subtitles_report.csv"
    prompt_file = project_dir / "README_ANALYSIS_PROMPT.md"
    summary_file = project_dir / "project_summary.json"
    zip_path = options.output_downloads / f"{project_name}_YTIS_RESEARCH_READY.zip"

    if callback:
        callback(f"Preparing folders: {project_dir}", 0.05)
        callback(f"Build mode: {mode}", 0.06)

    raw_srt_dir.mkdir(parents=True, exist_ok=True)
    clean_txt_dir.mkdir(parents=True, exist_ok=True)
    options.output_downloads.mkdir(parents=True, exist_ok=True)

    for old_file in [master_file, index_file, missing_file, prompt_file, summary_file]:
        old_file.unlink(missing_ok=True)

    existing_srt_count = len(list(raw_srt_dir.glob("*.srt")))
    videos = []

    if mode == "repackage":
        if existing_srt_count == 0:
            raise RuntimeError("Repackage mode requested, but no existing SRT files were found.")
        if callback:
            callback(f"Repackage mode: using {existing_srt_count} existing SRT files. No YouTube download.", 0.20)
        keep_one_subtitle_per_video(raw_srt_dir, options.lang, callback)
        assert_unique_subtitles(raw_srt_dir)

    elif mode == "reuse":
        if existing_srt_count > 0:
            if callback:
                callback(f"Reuse mode: found {existing_srt_count} existing SRT files. Skipping YouTube subtitle download.", 0.20)
            keep_one_subtitle_per_video(raw_srt_dir, options.lang, callback)
            assert_unique_subtitles(raw_srt_dir)
        else:
            if callback:
                callback("Reuse mode: no existing SRT files found, so YTIS will download subtitles once.", 0.20)
            videos = fetch_channel_video_index(options.url, callback)
            download_subtitles(options.url, raw_srt_dir, options.lang, callback)

    elif mode == "refresh":
        if callback:
            callback("Refresh mode: contacting YouTube and updating subtitles.", 0.20)
        videos = fetch_channel_video_index(options.url, callback)
        download_subtitles(options.url, raw_srt_dir, options.lang, callback)

    if not videos and mode in {"reuse", "repackage"}:
        try:
            videos = fetch_channel_video_index(options.url, callback)
        except Exception as exc:
            if callback:
                callback(f"Could not fetch channel index for missing report: {exc}", None)
            videos = []

    records = clean_all_srt(raw_srt_dir, clean_txt_dir, callback)

    unique_record_ids = {r.video_id for r in records if r.video_id}
    if len(unique_record_ids) != len(records):
        duplicate_ids = []
        seen = set()
        for r in records:
            if r.video_id in seen:
                duplicate_ids.append(r.video_id)
            seen.add(r.video_id)
        raise RuntimeError("Duplicate transcript records detected before ZIP creation: " + ", ".join(sorted(set(duplicate_ids))))

    write_combined_markdown(records, clean_txt_dir, master_file, callback)
    write_transcript_index(records, index_file, callback)
    write_missing_report(videos, records, missing_file, callback)
    write_analysis_prompt(project_name, options.url, prompt_file)

    if callback:
        callback("Analysis prompt written", 0.88)

    total_words = sum(r.word_count for r in records)
    missing_subtitles = max(0, len(videos) - len(unique_record_ids)) if videos else 0

    summary = {
        "name": project_name,
        "url": options.url,
        "language": options.lang,
        "status": "completed",
        "build_mode": mode,
        "project_dir": str(project_dir),
        "zip_path": str(zip_path),
        "videos_found": len(videos),
        "transcripts_created": len(records),
        "unique_transcript_ids": len(unique_record_ids),
        "missing_subtitles": missing_subtitles,
        "total_words": total_words,
        "built_at": datetime.now().isoformat(timespec="seconds"),
    }
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    upsert_project(options.base_projects_dir, summary)

    if callback:
        callback("Project registry updated", 0.90)

    create_zip(project_dir, zip_path, callback)

    if callback:
        callback(
            f"Summary: {len(videos)} videos, {len(records)} transcripts, "
            f"{missing_subtitles} missing, {total_words} words",
            0.99,
        )
        callback("All tasks completed successfully.", 1.0)

    return BuildResult(
        project_dir=project_dir,
        zip_path=zip_path,
        videos_found=len(videos),
        transcripts_created=len(records),
        total_words=total_words,
        missing_subtitles=missing_subtitles,
        mode=mode,
    )
