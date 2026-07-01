from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

from ytis.core.models import VideoRecord

LogCallback = Callable[[str, float | None], None]


def run_command(args: list[str], callback: LogCallback | None = None) -> None:
    if callback:
        callback("Running: " + " ".join(args), None)

    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert process.stdout is not None
    for line in process.stdout:
        line = line.rstrip()
        if callback and line:
            callback(line, None)

    code = process.wait()
    if code != 0:
        raise RuntimeError(f"Command failed with exit code {code}: {' '.join(args)}")


def fetch_channel_video_index(url: str, callback: LogCallback | None = None) -> list[VideoRecord]:
    args = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist",
        "--dump-json",
        "--ignore-errors",
        url,
    ]

    if callback:
        callback("Fetching channel video index...", 0.12)

    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    videos: list[VideoRecord] = []
    assert process.stdout is not None
    for line in process.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        video_id = data.get("id") or ""
        title = data.get("title") or video_id
        videos.append(
            VideoRecord(
                video_id=video_id,
                title=title,
                upload_date=str(data.get("upload_date") or ""),
                duration=str(data.get("duration") or ""),
                webpage_url=data.get("url") or data.get("webpage_url") or "",
            )
        )

    stderr = process.stderr.read() if process.stderr else ""
    code = process.wait()

    if callback and stderr.strip():
        callback(stderr.strip(), None)

    if code != 0 and not videos:
        raise RuntimeError("Could not fetch channel video index.")

    if callback:
        callback(f"Videos found: {len(videos)}", 0.18)

    return videos


def download_subtitles(url: str, raw_srt_dir: Path, lang: str, callback: LogCallback | None = None) -> None:
    raw_srt_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(raw_srt_dir / "%(upload_date)s - %(title).120s [%(id)s].%(ext)s")

    args = [
        sys.executable, "-m", "yt_dlp",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", f"{lang}.*",
        "--convert-subs", "srt",
        "--ignore-errors",
        "--no-overwrites",
        "-o", output_template,
        url,
    ]

    if callback:
        callback("Downloading subtitles...", 0.25)

    run_command(args, callback)
    remove_duplicate_orig_subtitles(raw_srt_dir, callback)

    if callback:
        kept = len(list(raw_srt_dir.glob("*.srt")))
        callback(f"SRT files kept: {kept}", 0.45)


def remove_duplicate_orig_subtitles(raw_srt_dir: Path, callback: LogCallback | None = None) -> None:
    removed = 0
    for pattern in ["*.en-orig.srt", "*-orig.srt"]:
        for path in raw_srt_dir.glob(pattern):
            path.unlink(missing_ok=True)
            removed += 1

    if callback:
        callback(f"Duplicate orig subtitles removed: {removed}", 0.48)
