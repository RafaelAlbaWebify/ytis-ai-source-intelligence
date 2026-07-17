from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ytis.research.models import Finding, Investigation

ReportTemplate = Literal[
    "source-credibility",
    "business-model",
    "technical-lessons",
    "learning-roadmap",
    "opportunity-analysis",
]

REPORT_TEMPLATES: tuple[str, ...] = (
    "source-credibility",
    "business-model",
    "technical-lessons",
    "learning-roadmap",
    "opportunity-analysis",
)


@dataclass(frozen=True)
class ReviewedReport:
    template: ReportTemplate
    title: str
    markdown: str
    accepted_finding_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.template not in REPORT_TEMPLATES:
            raise ValueError(f"unsupported report template: {self.template}")
        if not self.title.strip():
            raise ValueError("report title is required")
        if not self.markdown.strip():
            raise ValueError("report markdown is required")
        if len(self.accepted_finding_ids) != len(set(self.accepted_finding_ids)):
            raise ValueError("accepted finding IDs must be unique")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("evidence IDs must be unique")


def _accepted(investigation: Investigation) -> list[Finding]:
    return [
        finding
        for finding in investigation.findings
        if investigation.review_status(finding.finding_id) == "accepted"
    ]


def _grounded_evidence_ids(investigation: Investigation, findings: list[Finding]) -> tuple[str, ...]:
    available = {item.evidence_id for item in investigation.evidence}
    ordered: list[str] = []
    for finding in findings:
        for evidence_id in finding.evidence_ids:
            if evidence_id not in available:
                raise ValueError(f"finding {finding.finding_id} cites missing evidence: {evidence_id}")
            if evidence_id not in ordered:
                ordered.append(evidence_id)
    return tuple(ordered)


def _finding_lines(findings: list[Finding], *, categories: set[str] | None = None) -> list[str]:
    selected = [finding for finding in findings if categories is None or finding.category in categories]
    if not selected:
        return ["No accepted findings matched this section."]
    lines: list[str] = []
    for finding in selected:
        evidence = ", ".join(f"`{item}`" for item in finding.evidence_ids)
        lines.extend(
            [
                f"### {finding.title}",
                "",
                f"- Category: `{finding.category}`",
                f"- Confidence: {finding.confidence:.2f}",
                f"- Claim: {finding.summary}",
                f"- Evidence: {evidence}",
                "",
            ]
        )
    return lines


def render_reviewed_report(investigation: Investigation, template: str) -> ReviewedReport:
    if template not in REPORT_TEMPLATES:
        raise ValueError(f"unsupported report template: {template}")
    accepted = _accepted(investigation)
    evidence_ids = _grounded_evidence_ids(investigation, accepted)
    category_counts = Counter(finding.category for finding in accepted)
    reviewed_count = sum(investigation.review_status(item.finding_id) != "pending" for item in investigation.findings)
    header = [
        f"# {investigation.title} — {template.replace('-', ' ').title()}",
        "",
        f"**Research question:** {investigation.question}",
        "",
        "## Review boundary",
        "",
        f"- Total findings: {len(investigation.findings)}",
        f"- Reviewed findings: {reviewed_count}",
        f"- Accepted findings used: {len(accepted)}",
        f"- Evidence units cited: {len(evidence_ids)}",
        "- Only human-accepted findings are included.",
        "",
    ]

    if template == "source-credibility":
        source_counts = Counter(item.source_id for item in investigation.evidence if item.evidence_id in evidence_ids)
        body = ["## Source coverage", ""]
        if not investigation.sources:
            body.append("No sources are available.")
        for source in investigation.sources:
            body.extend(
                [
                    f"### {source.source_id} · {source.title}",
                    "",
                    f"- Accepted evidence units cited: {source_counts[source.source_id]}",
                    f"- Origin: {source.origin}",
                    "- Credibility decision: requires human assessment; YTIS reports provenance and coverage only.",
                    "",
                ]
            )
        body.extend(["## Accepted claims", "", *_finding_lines(accepted)])
        title = "Source credibility and provenance"
    elif template == "business-model":
        body = [
            "## Evidence-backed business signals",
            "",
            *_finding_lines(accepted, categories={"capability", "constraint", "recommendation"}),
            "## Risks",
            "",
            *_finding_lines(accepted, categories={"risk"}),
        ]
        title = "Business model extraction"
    elif template == "technical-lessons":
        body = [
            "## Capabilities and implementation lessons",
            "",
            *_finding_lines(accepted, categories={"capability", "constraint"}),
            "## Engineering risks and recommendations",
            "",
            *_finding_lines(accepted, categories={"risk", "recommendation"}),
        ]
        title = "Technical lessons"
    elif template == "learning-roadmap":
        recommendations = [item for item in accepted if item.category == "recommendation"]
        constraints = [item for item in accepted if item.category == "constraint"]
        body = ["## Learning priorities", ""]
        ordered = recommendations + constraints
        if not ordered:
            body.append("No accepted recommendations or constraints are available.")
        for index, finding in enumerate(ordered, start=1):
            body.extend(
                [
                    f"### {index}. {finding.title}",
                    "",
                    f"- Learning objective: {finding.summary}",
                    f"- Basis: `{finding.category}` at confidence {finding.confidence:.2f}",
                    f"- Evidence: {', '.join(f'`{item}`' for item in finding.evidence_ids)}",
                    "",
                ]
            )
        title = "Learning roadmap"
    else:
        body = [
            "## Opportunity signals",
            "",
            *_finding_lines(accepted, categories={"capability", "recommendation"}),
            "## Constraints and risks",
            "",
            *_finding_lines(accepted, categories={"constraint", "risk"}),
            "## Category balance",
            "",
            *[f"- {category}: {category_counts[category]}" for category in sorted(category_counts)],
            "",
        ]
        title = "Opportunity analysis"

    markdown = "\n".join(header + body).rstrip() + "\n"
    return ReviewedReport(
        template=template,  # type: ignore[arg-type]
        title=title,
        markdown=markdown,
        accepted_finding_ids=tuple(item.finding_id for item in accepted),
        evidence_ids=evidence_ids,
    )


def write_reviewed_report(
    investigation: Investigation,
    template: str,
    output_dir: Path,
) -> Path:
    report = render_reviewed_report(investigation, template)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{template}.md"
    path.write_text(report.markdown, encoding="utf-8")
    return path
