from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "technical-research"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import SourceDocument, TechnicalResearchService
from ytis.research.models import Finding


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    service = TechnicalResearchService()
    source = SourceDocument(
        source_id="source-001",
        title="Public-safe technical architecture note",
        origin="deterministic-fixture",
        content=(
            "The platform supports local transcript cleaning and validated ZIP packaging. "
            "The current workflow requires human review before findings are published. "
            "A major risk is that unsupported claims could appear without evidence links. "
            "The next step should add structured evidence-linked findings and reports."
        ),
    )
    investigation = service.create_investigation(
        investigation_id="investigation-001",
        title="Technical source research baseline",
        question="What capabilities, constraints, risks, and recommendations are stated?",
        sources=[source],
    )

    checks: dict[str, bool] = {}
    checks["source_preserved"] = len(investigation.sources) == 1
    checks["evidence_created"] = len(investigation.evidence) == 4
    checks["findings_created"] = len(investigation.findings) == 4
    checks["all_categories_present"] = {f.category for f in investigation.findings} == {
        "capability",
        "constraint",
        "risk",
        "recommendation",
    }
    checks["all_findings_grounded"] = all(f.evidence_ids for f in investigation.findings)
    checks["offsets_match_source"] = all(
        source.content[e.start_offset:e.end_offset] == e.text for e in investigation.evidence
    )

    accepted_id = investigation.findings[0].finding_id
    rejected_id = investigation.findings[1].finding_id
    service.review_finding(investigation, finding_id=accepted_id, status="accepted")
    service.review_finding(investigation, finding_id=rejected_id, status="rejected")
    checks["review_statuses_recorded"] = (
        investigation.review_status(accepted_id) == "accepted"
        and investigation.review_status(rejected_id) == "rejected"
    )

    markdown_path, json_path = service.generate_reports(investigation, OUT)
    markdown = markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    checks["reports_created"] = markdown_path.exists() and json_path.exists()
    checks["accepted_finding_in_markdown"] = investigation.findings[0].title in markdown
    checks["rejected_finding_excluded_from_markdown"] = investigation.findings[1].title not in markdown
    checks["json_contains_evidence"] = len(payload.get("evidence", [])) == 4
    checks["json_contains_reviews"] = len(payload.get("reviews", [])) == 2

    duplicate_rejected = False
    try:
        service.create_investigation(
            investigation_id="bad-duplicate",
            title="Duplicate source IDs",
            question="Should fail",
            sources=[source, source],
        )
    except ValueError:
        duplicate_rejected = True
    checks["duplicate_source_ids_rejected"] = duplicate_rejected

    ungrounded_rejected = False
    try:
        investigation.findings.append(
            Finding(
                finding_id="bad-finding",
                title="Ungrounded",
                summary="This finding cites missing evidence.",
                category="risk",
                evidence_ids=("missing:e999",),
                confidence=0.5,
            )
        )
        service.validate_grounding(investigation)
    except ValueError:
        ungrounded_rejected = True
    finally:
        investigation.findings = [f for f in investigation.findings if f.finding_id != "bad-finding"]
    checks["ungrounded_findings_rejected"] = ungrounded_rejected

    report = {
        "ok": all(checks.values()),
        "checks": checks,
        "counts": {
            "sources": len(investigation.sources),
            "evidence": len(investigation.evidence),
            "findings": len(investigation.findings),
            "reviews": len(investigation.reviews),
        },
        "outputs": {
            "markdown": str(markdown_path),
            "json": str(json_path),
        },
    }
    (OUT / "technical-research-smoke.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    lines = [
        "# Technical Research Smoke Test",
        "",
        f"- Overall: {'PASS' if report['ok'] else 'FAIL'}",
        f"- Evidence units: {report['counts']['evidence']}",
        f"- Findings: {report['counts']['findings']}",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {'PASS' if value else 'FAIL'} `{name}`" for name, value in checks.items())
    (OUT / "technical-research-smoke.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
