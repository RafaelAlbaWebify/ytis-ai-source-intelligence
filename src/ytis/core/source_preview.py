from __future__ import annotations

import base64
import json
import mimetypes
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


VIDEO_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})")
HANDLE_RE = re.compile(r"youtube\.com/@([^/?#]+)")


@dataclass
class SourcePreview:
    source_type: str
    title: str
    subtitle: str
    image_url: str
    image_path: str
    image_data_uri: str
    status: str
    error: str = ""


def safe_project_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", (name or "YTIS_Source").strip())
    return cleaned[:80] or "YTIS_Source"


def image_to_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _download(url: str, target: Path, timeout: int = 20) -> bool:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=timeout) as response:
        data = response.read()
    if not data or len(data) < 1000:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return True


def _best_thumbnail(thumbnails: list[dict[str, Any]]) -> str:
    if not thumbnails:
        return ""
    sorted_items = sorted(
        thumbnails,
        key=lambda item: int(item.get("width") or 0) * int(item.get("height") or 0),
        reverse=True,
    )
    return str(sorted_items[0].get("url") or "")


def _yt_dlp_metadata(url: str, timeout: int = 40) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--dump-single-json",
        "--playlist-items",
        "1",
        "--skip-download",
        url,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "yt-dlp metadata failed")
    return json.loads(completed.stdout)


def capture_source_preview(url: str, project_name: str, projects_dir: Path) -> SourcePreview:
    url = (url or "").strip()
    project_name = project_name or "YTIS_Source"
    preview_dir = projects_dir / safe_project_name(project_name) / "source_preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    target = preview_dir / "source_preview.jpg"

    video_match = VIDEO_RE.search(url)
    if video_match:
        video_id = video_match.group(1)
        candidates = [
            f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            f"https://img.youtube.com/vi/{video_id}/sddefault.jpg",
            f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        ]
        last_error = ""
        for candidate in candidates:
            try:
                if _download(candidate, target):
                    return SourcePreview(
                        source_type="Video",
                        title=project_name,
                        subtitle=f"Video ID: {video_id}",
                        image_url=candidate,
                        image_path=str(target),
                        image_data_uri=image_to_data_uri(target),
                        status="Captured video thumbnail",
                    )
            except Exception as exc:
                last_error = str(exc)
        return SourcePreview(
            source_type="Video",
            title=project_name,
            subtitle=f"Video ID: {video_id}",
            image_url=candidates[-1],
            image_path="",
            image_data_uri="",
            status="Preview capture failed",
            error=last_error,
        )

    try:
        metadata = _yt_dlp_metadata(url)
        title = str(metadata.get("channel") or metadata.get("title") or project_name)
        handle_match = HANDLE_RE.search(url)
        subtitle = f"@{handle_match.group(1)}" if handle_match else str(metadata.get("uploader") or "YouTube channel")

        thumb_url = _best_thumbnail(metadata.get("thumbnails") or [])
        if not thumb_url:
            entries = metadata.get("entries") or []
            if entries:
                first = entries[0] or {}
                thumb_url = _best_thumbnail(first.get("thumbnails") or []) or str(first.get("thumbnail") or "")

        if not thumb_url:
            raise RuntimeError("No thumbnail URL found in yt-dlp metadata")

        _download(thumb_url, target)
        meta_path = preview_dir / "source_preview_metadata.json"
        meta_path.write_text(
            json.dumps(
                {
                    "source_url": url,
                    "title": title,
                    "subtitle": subtitle,
                    "image_url": thumb_url,
                    "image_path": str(target),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return SourcePreview(
            source_type="Channel",
            title=title,
            subtitle=subtitle,
            image_url=thumb_url,
            image_path=str(target),
            image_data_uri=image_to_data_uri(target),
            status="Captured channel preview",
        )
    except Exception as exc:
        return SourcePreview(
            source_type="Channel",
            title=project_name,
            subtitle=url,
            image_url="",
            image_path="",
            image_data_uri="",
            status="Preview capture failed",
            error=str(exc),
        )


def preview_from_url_only(url: str, project_name: str) -> SourcePreview:
    video_match = VIDEO_RE.search(url or "")
    if video_match:
        video_id = video_match.group(1)
        thumb = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        return SourcePreview(
            source_type="Video",
            title=project_name or "YouTube video",
            subtitle=f"Video ID: {video_id}",
            image_url=thumb,
            image_path="",
            image_data_uri="",
            status="Remote thumbnail preview",
        )

    handle_match = HANDLE_RE.search(url or "")
    handle = handle_match.group(1) if handle_match else "youtube-channel"
    return SourcePreview(
        source_type="Channel",
        title=project_name or "YouTube channel",
        subtitle=f"@{handle}",
        image_url="https://www.youtube.com/img/desktop/yt_1200.png",
        image_path="",
        image_data_uri="",
        status="Placeholder preview. Use Capture Preview for a real saved image.",
    )
