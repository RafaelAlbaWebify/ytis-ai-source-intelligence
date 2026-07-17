from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

FindingCategory = Literal["capability", "constraint", "risk", "recommendation"]
ReviewStatus = Literal["pending", "accepted", "rejected"]

SOURCE_TYPES: tuple[str, ...] = (
    "text",
    "technical-note",
    "pasted-text",
    "article-notes",
    "document-notes",
    "job-description",
    "transcript",
)


def _required(value: str, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


@dataclass(frozen=True)
class SourceDocument:
    source_id: str
    title: str
    content: str
    source_type: str = "text"
    origin: str = "fixture"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _required(self.source_id, "source_id"))
        object.__setattr__(self, "title", _required(self.title, "title"))
        object.__setattr__(self, "content", _required(self.content, "content"))
        source_type = _required(self.source_type, "source_type").lower()
        if source_type not in SOURCE_TYPES:
            raise ValueError(f"unsupported source type: {source_type}")
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(self, "origin", _required(self.origin, "origin"))


@dataclass(frozen=True)
class EvidenceUnit:
    evidence_id: str
    source_id: str
    text: str
    start_offset: int
    end_offset: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", _required(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "source_id", _required(self.source_id, "source_id"))
        object.__setattr__(self, "text", _required(self.text, "text"))
        if self.start_offset < 0 or self.end_offset <= self.start_offset:
            raise ValueError("evidence offsets must define a positive range")


@dataclass(frozen=True)
class Finding:
    finding_id: str
    title: str
    summary: str
    category: FindingCategory
    evidence_ids: tuple[str, ...]
    confidence: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "finding_id", _required(self.finding_id, "finding_id"))
        object.__setattr__(self, "title", _required(self.title, "title"))
        object.__setattr__(self, "summary", _required(self.summary, "summary"))
        if self.category not in {"capability", "constraint", "risk", "recommendation"}:
            raise ValueError(f"unsupported category: {self.category}")
        if not self.evidence_ids:
            raise ValueError("finding must cite at least one evidence unit")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class ReviewDecision:
    finding_id: str
    status: ReviewStatus
    note: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "finding_id", _required(self.finding_id, "finding_id"))
        if self.status not in {"pending", "accepted", "rejected"}:
            raise ValueError(f"unsupported review status: {self.status}")


@dataclass
class Investigation:
    investigation_id: str
    title: str
    question: str
    sources: list[SourceDocument] = field(default_factory=list)
    evidence: list[EvidenceUnit] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    reviews: list[ReviewDecision] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.investigation_id = _required(self.investigation_id, "investigation_id")
        self.title = _required(self.title, "title")
        self.question = _required(self.question, "question")

    def review_status(self, finding_id: str) -> str:
        for decision in reversed(self.reviews):
            if decision.finding_id == finding_id:
                return decision.status
        return "pending"

    def to_dict(self) -> dict:
        return asdict(self)
