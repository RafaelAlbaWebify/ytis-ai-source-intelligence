from __future__ import annotations

from pathlib import Path

from ytis.research.extractor import classify_evidence, extract_evidence
from ytis.research.models import Investigation, ReviewDecision, SourceDocument
from ytis.research.reporting import write_reports


class TechnicalResearchService:
    def create_investigation(
        self,
        *,
        investigation_id: str,
        title: str,
        question: str,
        sources: list[SourceDocument],
    ) -> Investigation:
        if not sources:
            raise ValueError("at least one source is required")
        source_ids = [source.source_id for source in sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source IDs must be unique")

        investigation = Investigation(
            investigation_id=investigation_id,
            title=title,
            question=question,
            sources=list(sources),
        )
        for source in sources:
            investigation.evidence.extend(extract_evidence(source))
        investigation.findings = classify_evidence(investigation.evidence)
        self.validate_grounding(investigation)
        return investigation

    def review_finding(
        self,
        investigation: Investigation,
        *,
        finding_id: str,
        status: str,
        note: str = "",
    ) -> ReviewDecision:
        if finding_id not in {finding.finding_id for finding in investigation.findings}:
            raise ValueError(f"unknown finding: {finding_id}")
        decision = ReviewDecision(finding_id=finding_id, status=status, note=note)  # type: ignore[arg-type]
        investigation.reviews.append(decision)
        return decision

    def accept_all(self, investigation: Investigation) -> None:
        for finding in investigation.findings:
            self.review_finding(
                investigation,
                finding_id=finding.finding_id,
                status="accepted",
                note="Accepted by deterministic fixture review.",
            )

    def validate_grounding(self, investigation: Investigation) -> None:
        evidence_ids = {item.evidence_id for item in investigation.evidence}
        if len(evidence_ids) != len(investigation.evidence):
            raise ValueError("evidence IDs must be unique")
        for finding in investigation.findings:
            missing = set(finding.evidence_ids) - evidence_ids
            if missing:
                raise ValueError(
                    f"finding {finding.finding_id} cites missing evidence: {sorted(missing)}"
                )

    def generate_reports(
        self,
        investigation: Investigation,
        output_dir: Path,
    ) -> tuple[Path, Path]:
        self.validate_grounding(investigation)
        return write_reports(investigation, output_dir)
