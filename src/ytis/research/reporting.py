from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ytis.research.models import Investigation


def render_markdown(investigation: Investigation) -> str:
    evidence_by_id = {item.evidence_id: item for item in investigation.evidence}
    evidence_counts = Counter(item.source_id for item in investigation.evidence)
    lines = [
        f"# {investigation.title}",
        "",
        f"**Research question:** {investigation.question}",
        "",
        "## Source register",
        "",
    ]
    for source in investigation.sources:
        lines.extend(
            [
                f"### {source.source_id} · {source.title}",
                "",
                f"- Type: `{source.source_type}`",
                f"- Origin: {source.origin}",
                f"- Evidence units: {evidence_counts[source.source_id]}",
                "",
            ]
        )
    lines.extend(["## Findings", ""])
    accepted = [
        finding
        for finding in investigation.findings
        if investigation.review_status(finding.finding_id) == "accepted"
    ]
    if not accepted:
        lines.append("No accepted findings.")
    for finding in accepted:
        lines.extend(
            [
                f"### {finding.title}",
                "",
                f"- Category: `{finding.category}`",
                f"- Confidence: {finding.confidence:.2f}",
                f"- Summary: {finding.summary}",
                "- Evidence:",
            ]
        )
        for evidence_id in finding.evidence_ids:
            evidence = evidence_by_id[evidence_id]
            lines.append(
                f"  - `{evidence.evidence_id}` ({evidence.source_id}, "
                f"chars {evidence.start_offset}-{evidence.end_offset}): {evidence.text}"
            )
        lines.append("")
    lines.extend(
        [
            "## Review summary",
            "",
            f"- Accepted: {sum(investigation.review_status(f.finding_id) == 'accepted' for f in investigation.findings)}",
            f"- Rejected: {sum(investigation.review_status(f.finding_id) == 'rejected' for f in investigation.findings)}",
            f"- Pending: {sum(investigation.review_status(f.finding_id) == 'pending' for f in investigation.findings)}",
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(investigation: Investigation, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "technical-research-report.md"
    json_path = output_dir / "technical-research-report.json"
    markdown_path.write_text(render_markdown(investigation), encoding="utf-8")
    json_path.write_text(json.dumps(investigation.to_dict(), indent=2), encoding="utf-8")
    return markdown_path, json_path
