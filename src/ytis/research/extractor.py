from __future__ import annotations

import re
from collections.abc import Iterable

from ytis.research.models import EvidenceUnit, Finding, SourceDocument

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("capability", ("supports", "provides", "can ", "enables", "allows")),
    ("constraint", ("requires", "depends on", "limited", "only ", "must ")),
    ("risk", ("risk", "failure", "error", "unsafe", "loss", "outage")),
    ("recommendation", ("recommend", "should", "prefer", "avoid", "next step")),
)


def extract_evidence(source: SourceDocument) -> list[EvidenceUnit]:
    evidence: list[EvidenceUnit] = []
    cursor = 0
    for index, sentence in enumerate(_SENTENCE_RE.split(source.content), start=1):
        text = sentence.strip()
        if not text:
            continue
        start = source.content.find(text, cursor)
        if start < 0:
            start = cursor
        end = start + len(text)
        cursor = end
        evidence.append(
            EvidenceUnit(
                evidence_id=f"{source.source_id}:e{index:03d}",
                source_id=source.source_id,
                text=text,
                start_offset=start,
                end_offset=end,
            )
        )
    return evidence


def classify_evidence(evidence: Iterable[EvidenceUnit]) -> list[Finding]:
    findings: list[Finding] = []
    for item in evidence:
        lowered = item.text.lower()
        category = next(
            (name for name, keywords in _RULES if any(keyword in lowered for keyword in keywords)),
            None,
        )
        if category is None:
            continue
        title = item.text.split(":", 1)[0].strip()
        if len(title) > 72:
            title = title[:69].rstrip() + "..."
        findings.append(
            Finding(
                finding_id=f"f{len(findings) + 1:03d}",
                title=title,
                summary=item.text,
                category=category,  # type: ignore[arg-type]
                evidence_ids=(item.evidence_id,),
                confidence=0.75,
            )
        )
    return findings
