from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from ytis.research.models import Investigation


def _required(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


@dataclass(frozen=True)
class InsightCard:
    card_id: str
    investigation_id: str
    finding_id: str
    claim: str
    evidence_ids: tuple[str, ...]
    confidence: float
    action: str
    review_status: str = "accepted"

    def __post_init__(self) -> None:
        object.__setattr__(self, "card_id", _required(self.card_id, "card_id"))
        object.__setattr__(self, "investigation_id", _required(self.investigation_id, "investigation_id"))
        object.__setattr__(self, "finding_id", _required(self.finding_id, "finding_id"))
        object.__setattr__(self, "claim", _required(self.claim, "claim"))
        object.__setattr__(self, "action", _required(self.action, "action"))
        if not isinstance(self.evidence_ids, tuple) or not self.evidence_ids:
            raise ValueError("insight card must cite at least one evidence unit")
        if not all(isinstance(item, str) and item.strip() for item in self.evidence_ids):
            raise ValueError("insight card evidence IDs must be non-empty strings")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("insight card evidence IDs must be unique")
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise ValueError("confidence must be numeric")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.review_status != "accepted":
            raise ValueError("only accepted findings can become insight cards")

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["evidence_ids"] = list(self.evidence_ids)
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "InsightCard":
        expected = {
            "card_id", "investigation_id", "finding_id", "claim",
            "evidence_ids", "confidence", "action", "review_status",
        }
        if set(payload) != expected:
            raise ValueError("insight card payload has unexpected fields")
        string_fields = ("card_id", "investigation_id", "finding_id", "claim", "action", "review_status")
        if any(not isinstance(payload[field], str) for field in string_fields):
            raise ValueError("insight card string fields must be strings")
        evidence_ids = payload["evidence_ids"]
        if not isinstance(evidence_ids, list) or not all(isinstance(item, str) for item in evidence_ids):
            raise ValueError("evidence_ids must be a list of strings")
        confidence = payload["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError("confidence must be numeric")
        return cls(
            card_id=payload["card_id"], investigation_id=payload["investigation_id"],
            finding_id=payload["finding_id"], claim=payload["claim"],
            evidence_ids=tuple(evidence_ids), confidence=float(confidence),
            action=payload["action"], review_status=payload["review_status"],
        )


def create_insight_card(
    investigation: Investigation, *, finding_id: str, action: str, card_id: str | None = None,
) -> InsightCard:
    finding = next((item for item in investigation.findings if item.finding_id == finding_id), None)
    if finding is None:
        raise ValueError(f"unknown finding: {finding_id}")
    status = investigation.review_status(finding_id)
    if status != "accepted":
        raise ValueError("only accepted findings can become insight cards")
    evidence_ids = {item.evidence_id for item in investigation.evidence}
    missing = set(finding.evidence_ids) - evidence_ids
    if missing:
        raise ValueError(f"finding cites missing evidence: {sorted(missing)}")
    return InsightCard(
        card_id=card_id or f"{investigation.investigation_id}--{finding_id}",
        investigation_id=investigation.investigation_id,
        finding_id=finding.finding_id,
        claim=finding.summary,
        evidence_ids=tuple(finding.evidence_ids),
        confidence=finding.confidence,
        action=action,
        review_status=status,
    )


class JsonInsightCardRepository:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _path(self, card_id: str) -> Path:
        safe = _required(card_id, "card_id")
        if any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for character in safe):
            raise ValueError("card_id contains unsafe characters")
        return self.root / f"{safe}.json"

    def save(self, card: InsightCard, *, overwrite: bool = False) -> Path:
        path = self._path(card.card_id)
        self.root.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite:
            raise ValueError(f"insight card already exists: {card.card_id}")
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(card.to_dict(), indent=2), encoding="utf-8")
        os.replace(temporary, path)
        return path

    def load(self, card_id: str) -> InsightCard:
        path = self._path(card_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"insight card not found: {card_id}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid insight card JSON: {card_id}") from exc
        if not isinstance(payload, dict):
            raise ValueError("insight card payload must be an object")
        card = InsightCard.from_dict(payload)
        if card.card_id != card_id:
            raise ValueError("insight card filename does not match payload ID")
        return card

    def list_ids(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(path.stem for path in self.root.glob("*.json"))
