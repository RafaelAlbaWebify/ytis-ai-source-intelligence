from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
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
from ytis.core.io_utils import atomic_write_json, now_stamp, unique_child_path
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


def _duplicate_record_ids(records) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record in records:
        video_id = getattr(record, "video_id", "") or getattr(record, "filename", "")
        if not video_id:
            continue
        if video_id in seen:
            duplicates.add(video_id)
        seen.add(video_id)
    return sorted(duplicates)


def _copy_existing_raw_srt(final_project_dir: Path, stage_project_dir: Path) -> int:
    """Seed a staged build with existing subtitles, without copying stale generated outputs."""
    source_raw = final_project_dir / "raw_srt"
    target_raw = stage_project_dir / "raw_srt"
    if not source_raw.exists():
        return 0

    copied = 0
    target_raw.mkdir(parents=True, exist_ok=True)
    for source_file in source_raw.glob("*.srt"):
        if not source_file.is_file():
            continue
        shutil.copy2(source_file, target_raw / source_file.name)
        copied += 1
    return copied


def _move_to_backup(path: Path, backup_root: Path, stamp: str) -> Path | None:
    if not path.exists():
        return None
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_path = unique_child_path(backup_root, f"{path.name}__{stamp}")
    shutil.move(str(path), str(backup_path))
    return backup_path


def _restore_from_backup(backup_path: Path | None, target_path: Path) -> None:
    if backup_path is None or not backup_path.exists():
        return
    if target_path.exists():
        if target_path.is_dir():
            shutil.rmtree(target_path)
        else:
            target_path.unlink()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(backup_path), str(target_path))


def _discard_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _preserve_failed_stage(stage_container: Path, failed_root: Path, stamp: str, reason: str) -> None:
    """Keep a failed staged build for diagnosis without touching the live project."""
    if not stage_container.exists():
        return
    failed_root.mkdir(parents=True, exist_ok=True)
    failure_note = stage_container / "BUILD_FAILED.txt"
    try:
        failure_note.write_text(reason, encoding="utf-8")
    except Exception:
        pass
    failed_path = unique_child_path(failed_root, f"{stage_container.name}__failed_{stamp}")
    shutil.move(str(stage_container), str(failed_path))


def _verify_zip(zip_path: Path) -> None:
    if not zip_path.exists() or zip_path.stat().st_size <= 0:
        raise RuntimeError(f"ZIP creation did not produce a usable file: {zip_path}")


def _build_into_stage(
    *,
    options: BuildOptions,
    mode: str,
    project_name: str,
    final_project_dir: Path,
    stage_project_dir: Path,
    temp_zip_path: Path,
    callback: LogCallback | None,
) -> tuple[dict, BuildResult]:
    """Build and validate a complete research pack in a staging folder."""
    raw_srt_dir = stage_project_dir / "raw_srt"
    clean_txt_dir = stage_project_dir / "clean_txt"
    master_file = stage_project_dir / "ALL_TRANSCRIPTS_COMBINED.md"
    index_file = stage_project_dir / "transcript_index.csv"
    missing_file = stage_project_dir / "missing_subtitles_report.csv"
    prompt_file = stage_project_dir / "README_ANALYSIS_PROMPT.md"
    summary_file = stage_project_dir / "project_summary.json"

    if callback:
        callback(f"Preparing transactional staging folder: {stage_project_dir}", 0.05)
        callback(f"Build mode: {mode}", 0.06)

    raw_srt_dir.mkdir(parents=True, exist_ok=True)
    clean_txt_dir.mkdir(parents=True, exist_ok=True)
    options.output_downloads.mkdir(parents=True, exist_ok=True)

    seeded = _copy_existing_raw_srt(final_project_dir, stage_project_dir)
    if callback and seeded:
        callback(f"Seeded staged build with {seeded} existing SRT files from the live project.", 0.10)

    existing_srt_count = len(list(raw_srt_dir.glob("*.srt")))
    videos = []

    if mode == "repackage":
        if existing_srt_count == 0:
            raise RuntimeError("Repackage mode requested, but no existing SRT files were found.")
        if callback:
            callback(f"Repackage mode: using {existing_srt_count} staged SRT files. No YouTube download.", 0.20)
        keep_one_subtitle_per_video(raw_srt_dir, options.lang, callback)
        assert_unique_subtitles(raw_srt_dir)

    elif mode == "reuse":
        if existing_srt_count > 0:
            if callback:
                callback(f"Reuse mode: found {existing_srt_count} staged SRT files. Skipping YouTube subtitle download.", 0.20)
            keep_one_subtitle_per_video(raw_srt_dir, options.lang, callback)
            assert_unique_subtitles(raw_srt_dir)
        else:
            if callback:
                callback("Reuse mode: no existing SRT files found, so YTIS will download subtitles once.", 0.20)
            videos = fetch_channel_video_index(options.url, callback)
            download_subtitles(options.url, raw_srt_dir, options.lang, callback)

    elif mode == "refresh":
        if callback:
            callback("Refresh mode: contacting YouTube and updating subtitles in staging.", 0.20)
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

    duplicate_ids = _duplicate_record_ids(records)
    if duplicate_ids:
        if callback:
            callback("Duplicate transcript records detected after cleaning: " + ", ".join(duplicate_ids[:8]), None)
            callback("Retrying subtitle duplicate cleanup before packaging.", None)
        keep_one_subtitle_per_video(raw_srt_dir, options.lang, callback)
        assert_unique_subtitles(raw_srt_dir)
        records = clean_all_srt(raw_srt_dir, clean_txt_dir, callback)
        duplicate_ids = _duplicate_record_ids(records)

    if duplicate_ids:
        raise RuntimeError("Duplicate transcript records detected before ZIP creation after retry: " + ", ".join(duplicate_ids))

    unique_record_ids = {r.video_id for r in records if r.video_id}

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
        "transactional_build": True,
        "project_dir": str(final_project_dir),
        "zip_path": str(options.output_downloads / f"{project_name}_YTIS_RESEARCH_READY.zip"),
        "videos_found": len(videos),
        "transcripts_created": len(records),
        "unique_transcript_ids": len(unique_record_ids),
        "missing_subtitles": missing_subtitles,
        "total_words": total_words,
        "built_at": now_stamp(),
    }
    atomic_write_json(summary_file, summary)

    create_zip(stage_project_dir, temp_zip_path, callback)
    _verify_zip(temp_zip_path)

    return summary, BuildResult(
        project_dir=final_project_dir,
        zip_path=options.output_downloads / f"{project_name}_YTIS_RESEARCH_READY.zip",
        videos_found=len(videos),
        transcripts_created=len(records),
        total_words=total_words,
        missing_subtitles=missing_subtitles,
        mode=mode,
    )


def _promote_stage(
    *,
    stage_project_dir: Path,
    final_project_dir: Path,
    temp_zip_path: Path,
    final_zip_path: Path,
    base_projects_dir: Path,
    summary: dict,
    stamp: str,
    callback: LogCallback | None,
) -> None:
    """Promote a fully validated staged build to the live project atomically enough for local use."""
    backup_root = base_projects_dir / "_ytis_build_backups"
    project_backup_root = backup_root / "projects"
    zip_backup_root = backup_root / "zips"

    project_backup: Path | None = None
    zip_backup: Path | None = None

    try:
        if callback:
            callback("Promoting staged project to live project folder.", 0.91)
        project_backup = _move_to_backup(final_project_dir, project_backup_root, stamp)
        final_project_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(stage_project_dir), str(final_project_dir))

        if callback:
            callback("Promoting staged source ZIP.", 0.94)
        zip_backup = _move_to_backup(final_zip_path, zip_backup_root, stamp)
        final_zip_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(temp_zip_path), str(final_zip_path))
        _verify_zip(final_zip_path)

        upsert_project(base_projects_dir, summary)
        if callback:
            callback("Project registry updated after successful staged promotion.", 0.97)

    except Exception:
        _restore_from_backup(project_backup, final_project_dir)
        _restore_from_backup(zip_backup, final_zip_path)
        raise


def build_research_pack(options: BuildOptions, callback: LogCallback | None = None) -> BuildResult:
    """Build a source pack transactionally.

    The builder now uses staging -> verify -> promote. A failed build must not
    replace the live project folder, replace the live ZIP, or update the project
    registry. This protects guided missions from half-built source packs.
    """
    project_name = safe_name(options.name)
    mode = options.mode if options.mode in {"reuse", "refresh", "repackage"} else "reuse"

    final_project_dir = options.base_projects_dir / f"{project_name}_YTIS_RESEARCH_READY"
    final_zip_path = options.output_downloads / f"{project_name}_YTIS_RESEARCH_READY.zip"

    stamp = now_stamp()
    staging_root = options.base_projects_dir / "_ytis_build_staging"
    failed_root = options.base_projects_dir / "_ytis_failed_builds"
    stage_container = unique_child_path(staging_root, f"{project_name}__{stamp}")
    stage_project_dir = stage_container / f"{project_name}_YTIS_RESEARCH_READY"
    temp_zip_path = options.output_downloads / f"{project_name}_YTIS_RESEARCH_READY.tmp_{stamp}.zip"

    try:
        summary, result = _build_into_stage(
            options=options,
            mode=mode,
            project_name=project_name,
            final_project_dir=final_project_dir,
            stage_project_dir=stage_project_dir,
            temp_zip_path=temp_zip_path,
            callback=callback,
        )

        _promote_stage(
            stage_project_dir=stage_project_dir,
            final_project_dir=final_project_dir,
            temp_zip_path=temp_zip_path,
            final_zip_path=final_zip_path,
            base_projects_dir=options.base_projects_dir,
            summary=summary,
            stamp=stamp,
            callback=callback,
        )

        try:
            if stage_container.exists():
                shutil.rmtree(stage_container)
        except Exception:
            pass

        if callback:
            callback(
                f"Summary: {result.videos_found} videos, {result.transcripts_created} transcripts, "
                f"{result.missing_subtitles} missing, {result.total_words} words",
                0.99,
            )
            callback("Transactional source build completed successfully.", 1.0)

        return result

    except Exception as exc:
        try:
            temp_zip_path.unlink(missing_ok=True)
        except Exception:
            pass
        _preserve_failed_stage(stage_container, failed_root, stamp, str(exc))
        if callback:
            callback(f"Transactional build failed before live promotion: {exc}", None)
        raise
