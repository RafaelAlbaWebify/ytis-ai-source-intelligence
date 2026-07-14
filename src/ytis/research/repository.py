from __future__ import annotations

import json
from pathlib import Path

from ytis.research.models import (
    EvidenceUnit,
    Finding,
    Investigation,
    ReviewDecision,
    SourceDocument,
)


class JsonInvestigationRepository:
    """Local-first persistence for validated technical research investigations."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _path(self, investigation_id: str) -> Path:
        safe = "".join(ch for ch in investigation_id if ch.isalnum() or ch in {"-", "_"}).strip()
        if not safe or safe != investigation_id:
            raise ValueError("investigation_id contains unsupported characters")
        return self.root / f"{safe}.json"

    def save(self, investigation: Investigation) -> Path:
        path = self._path(investigation.investigation_id)
        self.root.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(investigation.to_dict(), indent=2), encoding="utf-8")
        temp.replace(path)
        return path

    def load(self, investigation_id: str) -> Investigation:
        path = self._path(investigation_id)
        if not path.exists():
            raise FileNotFoundError(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid investigation JSON: {path}") from exc
        investigation = self._from_dict(payload)
        if investigation.investigation_id != investigation_id:
            raise ValueError("investigation ID does not match repository filename")
        return investigation

    def list_ids(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(path.stem for path in self.root.glob("*.json") if path.is_file())

    def delete(self, investigation_id: str) -> bool:
        path = self._path(investigation_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    @staticmethod
    def _from_dict(payload: dict) -> Investigation:
        if not isinstance(payload, dict):
            raise ValueError("investigation payload must be an object")
        try:
            investigation = Investigation(
                investigation_id=payload["investigation_id"],
                title=payload["title"],
                question=payload["question"],
                sources=[SourceDocument(**item) for item in payload.get("sources", [])],
                evidence=[EvidenceUnit(**item) for item in payload.get("evidence", [])],
                findings=[
                    Finding(
                        finding_id=item["finding_id"],
                        title=item["title"],
                        summary=item["summary"],
                        category=item["category"],
                        evidence_ids=tuple(item["evidence_ids"]),
                        confidence=item["confidence"],
                    )
                    for item in payload.get("findings", [])
                ],
                reviews=[ReviewDecision(**item) for item in payload.get("reviews", [])],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid investigation payload") from exc
        return investigation
