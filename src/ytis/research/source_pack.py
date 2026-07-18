from __future__ import annotations

from collections.abc import Sequence

from ytis.research.models import SourceDocument


def _validated_sources(sources: Sequence[SourceDocument]) -> list[SourceDocument]:
    items = list(sources)
    source_ids = [source.source_id for source in items]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("source IDs must be unique")
    return items


def edit_source(
    sources: Sequence[SourceDocument],
    *,
    source_id: str,
    title: str | None = None,
    content: str | None = None,
    source_type: str | None = None,
    origin: str | None = None,
) -> tuple[SourceDocument, ...]:
    """Return a source pack with one source replaced, preserving its stable ID and position."""

    items = _validated_sources(sources)
    matches = [index for index, source in enumerate(items) if source.source_id == source_id]
    if not matches:
        raise ValueError(f"unknown source: {source_id}")
    index = matches[0]
    current = items[index]
    items[index] = SourceDocument(
        source_id=current.source_id,
        title=current.title if title is None else title,
        content=current.content if content is None else content,
        source_type=current.source_type if source_type is None else source_type,
        origin=current.origin if origin is None else origin,
    )
    return tuple(items)


def move_source(
    sources: Sequence[SourceDocument],
    *,
    source_id: str,
    target_index: int,
) -> tuple[SourceDocument, ...]:
    """Move one source to a zero-based position without changing any source ID or content."""

    items = _validated_sources(sources)
    if not items:
        raise ValueError("source pack is empty")
    if target_index < 0 or target_index >= len(items):
        raise ValueError("target_index is out of range")
    current_index = next((index for index, source in enumerate(items) if source.source_id == source_id), None)
    if current_index is None:
        raise ValueError(f"unknown source: {source_id}")
    source = items.pop(current_index)
    items.insert(target_index, source)
    return tuple(items)
