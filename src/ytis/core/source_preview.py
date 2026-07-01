from __future__ import annotations

import base64
import json
import mimetypes
import re
import subprocess
import sys
import zipfile
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


def expected_research_project_dir(projects_dir: Path, project_name: str) -> Path:
    safe = safe_project_name(project_name)
    ready_dir = projects_dir / f"{safe}_YTIS_RESEARCH_READY"
    if ready_dir.exists():
        return ready_dir
    plain_dir = projects_dir / safe
    if plain_dir.exists():
        return plain_dir
    return ready_dir


def image_to_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def existing_preview(project_dir: Path, url: str, project_name: str) -> SourcePreview | None:
    preview_dir = project_dir / "source_preview"
    image_path = preview_dir / "source_preview.jpg"
    meta_path = preview_dir / "source_preview_metadata.json"
    if not image_path.exists():
        return None

    metadata: dict[str, Any] = {}
    if meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        except Exception:
            metadata = {}

    fallback = preview_from_url_only(url, project_name)
    return SourcePreview(
        source_type=str(metadata.get("source_type") or fallback.source_type),
        title=str(metadata.get("title") or project_name or fallback.title),
        subtitle=str(metadata.get("subtitle") or fallback.subtitle),
        image_url=str(metadata.get("image_url") or fallback.image_url),
        image_path=str(image_path),
        image_data_uri=image_to_data_uri(image_path),
        status="Loaded local source preview",
    )


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


def _write_metadata(preview_dir: Path, data: dict[str, Any]) -> None:
    (preview_dir / "source_preview_metadata.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def capture_source_preview_to_project_dir(url: str, project_name: str, project_dir: Path) -> SourcePreview:
    url = (url or "").strip()
    project_name = project_name or "YTIS_Source"
    preview_dir = project_dir / "source_preview"
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
                    data = {
                        "source_type": "Video",
                        "source_url": url,
                        "title": project_name,
                        "subtitle": f"Video ID: {video_id}",
                        "image_url": candidate,
                        "image_path": str(target),
                    }
                    _write_metadata(preview_dir, data)
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
        return SourcePreview("Video", project_name, f"Video ID: {video_id}", candidates[-1], "", "", "Preview capture failed", last_error)

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
        data = {
            "source_type": "Channel",
            "source_url": url,
            "title": title,
            "subtitle": subtitle,
            "image_url": thumb_url,
            "image_path": str(target),
        }
        _write_metadata(preview_dir, data)

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
        return SourcePreview("Channel", project_name, url, "", "", "", "Preview capture failed", str(exc))


def capture_source_preview(url: str, project_name: str, projects_dir: Path) -> SourcePreview:
    project_dir = expected_research_project_dir(projects_dir, project_name)
    return capture_source_preview_to_project_dir(url, project_name, project_dir)


def add_preview_to_zip(zip_path: Path, project_dir: Path) -> bool:
    preview_dir = project_dir / "source_preview"
    if not zip_path.exists() or not preview_dir.exists():
        return False

    preview_files = [p for p in preview_dir.rglob("*") if p.is_file()]
    if not preview_files:
        return False

    base_name = project_dir.name
    with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        existing = set(archive.namelist())
        for path in preview_files:
            rel = path.relative_to(project_dir).as_posix()
            arcname = f"{base_name}/{rel}"
            if arcname in existing:
                continue
            archive.write(path, arcname)
    return True


def preview_from_url_only(url: str, project_name: str) -> SourcePreview:
    video_match = VIDEO_RE.search(url or "")
    if video_match:
        video_id = video_match.group(1)
        thumb = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        return SourcePreview("Video", project_name or "YouTube video", f"Video ID: {video_id}", thumb, "", "", "Remote thumbnail preview")

    handle_match = HANDLE_RE.search(url or "")
    handle = handle_match.group(1) if handle_match else "youtube-channel"
    return SourcePreview(
        "Channel",
        project_name or "YouTube channel",
        f"@{handle}",
        "https://www.youtube.com/img/desktop/yt_1200.png",
        "",
        "",
        "Placeholder preview. Local preview will be captured automatically during build.",
    )
