from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any

from ytis.research.models import EvidenceUnit, Finding

_ALLOWED_CATEGORIES = {"capability", "constraint", "risk", "recommendation"}
_ROOT_KEYS = {"findings"}
_FINDING_KEYS = {"finding_id", "title", "summary", "category", "evidence_ids", "confidence"}


class StructuredProviderError(ValueError):
    """Raised when a structured provider response violates the contract."""


class StructuredJsonFindingProvider:
    """Vendor-neutral adapter for generators that return strict JSON text.

    The supplied generator receives a deterministic prompt and returns text. This
    class performs no network access and stores no credentials; API-specific
    clients can be wrapped externally and injected as the generator callable.
    """

    def __init__(
        self,
        generator: Callable[[str], str],
        *,
        provider_name: str = "structured-json",
        max_findings: int = 50,
    ) -> None:
        if not callable(generator):
            raise TypeError("generator must be callable")
        name = str(provider_name or "").strip()
        if not name:
            raise ValueError("provider_name is required")
        if max_findings < 1:
            raise ValueError("max_findings must be positive")
        self._generator = generator
        self.provider_name = name
        self.max_findings = max_findings

    def generate_findings(
        self,
        *,
        question: str,
        evidence: Sequence[EvidenceUnit],
    ) -> list[Finding]:
        if not evidence:
            return []
        prompt = self.build_prompt(question=question, evidence=evidence)
        raw = self._generator(prompt)
        if not isinstance(raw, str) or not raw.strip():
            raise StructuredProviderError("generator must return non-empty JSON text")
        payload = self._parse_json(raw)
        return self._parse_findings(payload)

    def build_prompt(self, *, question: str, evidence: Sequence[EvidenceUnit]) -> str:
        lines = [
            "Return exactly one JSON object and no surrounding prose or Markdown.",
            "Use only the supplied evidence IDs. Do not invent evidence or claims.",
            "Allowed categories: capability, constraint, risk, recommendation.",
            "Schema:",
            '{"findings":[{"finding_id":"f001","title":"...","summary":"...",'
            '"category":"capability","evidence_ids":["source:e001"],"confidence":0.75}]}',
            "",
            f"Research question: {str(question or '').strip()}",
            "",
            "Evidence:",
        ]
        for item in evidence:
            lines.append(
                f"- {item.evidence_id} | source={item.source_id} | "
                f"chars={item.start_offset}-{item.end_offset} | {item.text}"
            )
        return "\n".join(lines)

    def _parse_json(self, raw: str) -> dict[str, Any]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StructuredProviderError(f"invalid JSON response: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise StructuredProviderError("response root must be an object")
        extra_root = set(payload) - _ROOT_KEYS
        missing_root = _ROOT_KEYS - set(payload)
        if extra_root or missing_root:
            raise StructuredProviderError(
                f"response root keys must be exactly {_ROOT_KEYS}; "
                f"missing={sorted(missing_root)} extra={sorted(extra_root)}"
            )
        return payload

    def _parse_findings(self, payload: dict[str, Any]) -> list[Finding]:
        records = payload["findings"]
        if not isinstance(records, list):
            raise StructuredProviderError("findings must be an array")
        if len(records) > self.max_findings:
            raise StructuredProviderError(
                f"finding count {len(records)} exceeds maximum {self.max_findings}"
            )

        findings: list[Finding] = []
        for index, record in enumerate(records, start=1):
            if not isinstance(record, dict):
                raise StructuredProviderError(f"finding {index} must be an object")
            keys = set(record)
            extra = keys - _FINDING_KEYS
            missing = _FINDING_KEYS - keys
            if extra or missing:
                raise StructuredProviderError(
                    f"finding {index} keys must be exactly {_FINDING_KEYS}; "
                    f"missing={sorted(missing)} extra={sorted(extra)}"
                )
            if not isinstance(record["finding_id"], str):
                raise StructuredProviderError(f"finding {index} finding_id must be a string")
            if not isinstance(record["title"], str):
                raise StructuredProviderError(f"finding {index} title must be a string")
            if not isinstance(record["summary"], str):
                raise StructuredProviderError(f"finding {index} summary must be a string")
            if record["category"] not in _ALLOWED_CATEGORIES:
                raise StructuredProviderError(
                    f"finding {index} has unsupported category: {record['category']}"
                )
            evidence_ids = record["evidence_ids"]
            if (
                not isinstance(evidence_ids, list)
                or not evidence_ids
                or any(not isinstance(item, str) for item in evidence_ids)
            ):
                raise StructuredProviderError(
                    f"finding {index} evidence_ids must be a non-empty string array"
                )
            confidence = record["confidence"]
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise StructuredProviderError(f"finding {index} confidence must be numeric")
            findings.append(
                Finding(
                    finding_id=record["finding_id"],
                    title=record["title"],
                    summary=record["summary"],
                    category=record["category"],
                    evidence_ids=tuple(evidence_ids),
                    confidence=float(confidence),
                )
            )
        return findings
