from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ytis.research.extractor import classify_evidence
from ytis.research.models import EvidenceUnit, Finding


@runtime_checkable
class FindingProvider(Protocol):
    """Provider contract for turning evidence into structured findings."""

    provider_name: str

    def generate_findings(
        self,
        *,
        question: str,
        evidence: Sequence[EvidenceUnit],
    ) -> list[Finding]:
        """Return candidate findings that cite evidence IDs from ``evidence``."""


class DeterministicFindingProvider:
    """Offline rule-based provider used as the safe default and CI fixture."""

    provider_name = "deterministic-rules"

    def generate_findings(
        self,
        *,
        question: str,
        evidence: Sequence[EvidenceUnit],
    ) -> list[Finding]:
        del question
        return classify_evidence(evidence)
