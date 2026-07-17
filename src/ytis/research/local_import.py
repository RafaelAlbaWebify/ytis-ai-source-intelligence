from __future__ import annotations

from pathlib import Path

from ytis.research.models import SourceDocument

SUPPORTED_LOCAL_SOURCE_SUFFIXES: tuple[str, ...] = (".txt", ".md", ".markdown")
DEFAULT_MAX_SOURCE_BYTES = 1_000_000


def import_local_source(
    path: Path,
    *,
    source_id: str,
    title: str | None = None,
    source_type: str = "document-notes",
    allowed_root: Path | None = None,
    max_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
) -> SourceDocument:
    """Read one public-safe local UTF-8 text file into a validated source document."""

    candidate = Path(path).expanduser()
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    if candidate.is_symlink():
        raise ValueError("symbolic links are not supported for local source import")
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"local source not found: {candidate}") from exc
    if not resolved.is_file():
        raise ValueError("local source must be a file")
    if resolved.suffix.lower() not in SUPPORTED_LOCAL_SOURCE_SUFFIXES:
        raise ValueError(f"unsupported local source extension: {resolved.suffix.lower() or '<none>'}")
    if allowed_root is not None:
        try:
            root = Path(allowed_root).expanduser().resolve(strict=True)
        except FileNotFoundError as exc:
            raise ValueError("allowed_root does not exist") from exc
        if not root.is_dir():
            raise ValueError("allowed_root must be a directory")
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError("local source is outside allowed_root") from exc
    size = resolved.stat().st_size
    if size > max_bytes:
        raise ValueError(f"local source exceeds maximum size of {max_bytes} bytes")
    try:
        content = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("local source must be valid UTF-8 text") from exc
    return SourceDocument(
        source_id=source_id,
        title=title or resolved.stem,
        content=content,
        source_type=source_type,
        origin=str(resolved),
    )
