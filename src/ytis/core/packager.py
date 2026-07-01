from __future__ import annotations

from pathlib import Path
from typing import Callable
from zipfile import ZIP_DEFLATED, ZipFile

from ytis.core.models import TranscriptRecord

LogCallback = Callable[[str, float | None], None]


def write_combined_markdown(records: list[TranscriptRecord], clean_txt_dir: Path, output_path: Path, callback: LogCallback | None = None) -> None:
    with output_path.open("w", encoding="utf-8", newline="\n") as out:
        for rec in records:
            txt_path = clean_txt_dir / rec.txt_file
            text = txt_path.read_text(encoding="utf-8", errors="replace") if txt_path.exists() else ""
            out.write(f"# {rec.upload_date} - {rec.title} [{rec.video_id}]\n\n")
            out.write(text)
            out.write("\n\n---\n\n")

    if callback:
        callback(f"Combined markdown written: {output_path.name}", 0.86)


def create_zip(source_dir: Path, zip_path: Path, callback: LogCallback | None = None) -> None:
    if zip_path.exists():
        zip_path.unlink()

    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
        for path in source_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(source_dir.parent))

    if callback:
        callback(f"ZIP created: {zip_path}", 0.96)
