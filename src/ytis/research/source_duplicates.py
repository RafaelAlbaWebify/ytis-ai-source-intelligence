from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from ytis.research.models import SourceDocument


@dataclass(frozen=True)
class DuplicateSourceGroup:
    fingerprint: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.fingerprint) != 64:
            raise ValueError("fingerprint must be a SHA-256 hex digest")
        if len(self.source_ids) < 2:
            raise ValueError("duplicate group requires at least two source IDs")
        if len(self.source_ids) != len(set(self.source_ids)):
            raise ValueError("duplicate group source IDs must be unique")


def normalize_source_content(content: str) -> str:
    text = str(content or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def source_fingerprint(source: SourceDocument) -> str:
    normalized = normalize_source_content(source.content)
    if not normalized:
        raise ValueError("source content is required")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def find_duplicate_sources(sources: list[SourceDocument]) -> tuple[DuplicateSourceGroup, ...]:
    source_ids = [source.source_id for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("source IDs must be unique")
    grouped: dict[str, list[str]] = {}
    for source in sources:
        grouped.setdefault(source_fingerprint(source), []).append(source.source_id)
    duplicates = [
        DuplicateSourceGroup(fingerprint=fingerprint, source_ids=tuple(ids))
        for fingerprint, ids in grouped.items()
        if len(ids) > 1
    ]
    return tuple(sorted(duplicates, key=lambda item: item.source_ids))
