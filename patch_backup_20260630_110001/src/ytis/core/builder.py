from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from ytis.core.cleaner import clean_all_srt
from ytis.core.downloader import download_subtitles, fetch_channel_video_index
from ytis.core.indexer import write_missing_report, write_transcript_index
from ytis.core.packager import create_zip, write_combined_markdown
from ytis.core.paths import safe_name
from ytis.core.prompts import write_analysis_prompt


LogCallback = Callable[[str, float | None], None]


@dataclass
class BuildOptions:
    name: str
    url: str
    lang: str
    output_downloads: Path
    base_projects_dir: Path


@dataclass
class BuildResult:
    project_dir: Path
    zip_path: Path
    videos_found: int
    transcripts_created: int
    total_words: int
    missing_subtitles: int


def build_research_pack(options: BuildOptions, callback: LogCallback | None = None) -> BuildResult:
    project_name = safe_name(options.name)

    project_dir = options.base_projects_dir / f"{project_name}_YTIS_RESEARCH_READY"
    raw_srt_dir = project_dir / "raw_srt"
    clean_txt_dir = project_dir / "clean_txt"

    master_file = project_dir / "ALL_TRANSCRIPTS_COMBINED.md"
    index_file = project_dir / "transcript_index.csv"
    missing_file = project_dir / "missing_subtitles_report.csv"
    prompt_file = project_dir / "README_ANALYSIS_PROMPT.md"
    zip_path = options.output_downloads / f"{project_name}_YTIS_RESEARCH_READY.zip"

    if callback:
        callback(f"Preparing folders: {project_dir}", 0.05)

    raw_srt_dir.mkdir(parents=True, exist_ok=True)
    clean_txt_dir.mkdir(parents=True, exist_ok=True)
    options.output_downloads.mkdir(parents=True, exist_ok=True)

    # Remove old top-level generated files before rebuilding.
    for old_file in [master_file, index_file, missing_file, prompt_file]:
        old_file.unlink(missing_ok=True)

    videos = fetch_channel_video_index(options.url, callback)
    download_subtitles(options.url, raw_srt_dir, options.lang, callback)

    records = clean_all_srt(raw_srt_dir, clean_txt_dir, callback)

    write_combined_markdown(records, clean_txt_dir, master_file, callback)
    write_transcript_index(records, index_file, callback)
    write_missing_report(videos, records, missing_file, callback)
    write_analysis_prompt(project_name, options.url, prompt_file)

    if callback:
        callback("Analysis prompt written", 0.88)

    create_zip(project_dir, zip_path, callback)

    total_words = sum(r.word_count for r in records)
    missing_subtitles = max(0, len(videos) - len({r.video_id for r in records if r.video_id}))

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
    )
