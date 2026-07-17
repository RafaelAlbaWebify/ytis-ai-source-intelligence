from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "reviewed-report-templates"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import (
    REPORT_TEMPLATES,
    SourceDocument,
    TechnicalResearchService,
    render_reviewed_report,
    write_reviewed_report,
)


def expect_value_error(fn, text: str) -> bool:
    try:
        fn()
    except ValueError as exc:
        return text in str(exc)
    return False


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    service = TechnicalResearchService()
    source = SourceDocument(
        source_id="source-001",
        title="Public-safe platform assessment",
        origin="deterministic-fixture",
        content=(
            "The platform supports evidence-linked report generation. "
            "The current workflow requires human review before publication. "
            "A major risk is losing provenance during manual consolidation. "
            "The next step should preserve source-qualified evidence in every report."
        ),
    )
    investigation = service.create_investigation(
        investigation_id="report-template-proof",
        title="Reviewed reporting proof",
        question="What should be retained in reviewed reports?",
        sources=[source],
    )
    accepted = investigation.findings[:3]
    rejected = investigation.findings[3]
    for finding in accepted:
        service.review_finding(investigation, finding_id=finding.finding_id, status="accepted")
    service.review_finding(investigation, finding_id=rejected.finding_id, status="rejected")

    reports = {
        template: render_reviewed_report(investigation, template)
        for template in REPORT_TEMPLATES
    }
    paths = {
        template: write_reviewed_report(investigation, template, OUT / "files")
        for template in REPORT_TEMPLATES
    }
    rejected_marker = rejected.summary
    accepted_ids = tuple(item.finding_id for item in accepted)

    checks = {
        "template_set_exact": REPORT_TEMPLATES == (
            "source-credibility",
            "business-model",
            "technical-lessons",
            "learning-roadmap",
            "opportunity-analysis",
        ),
        "all_templates_rendered": set(reports) == set(REPORT_TEMPLATES),
        "all_files_written": all(path.exists() for path in paths.values()),
        "accepted_ids_exact": all(report.accepted_finding_ids == accepted_ids for report in reports.values()),
        "accepted_claims_present": all(accepted[0].summary in report.markdown for report in reports.values()),
        "rejected_claim_absent": all(rejected_marker not in report.markdown for report in reports.values()),
        "human_review_boundary_visible": all(
            "Only human-accepted findings are included." in report.markdown for report in reports.values()
        ),
        "evidence_provenance_visible": all("source-001:e001" in report.markdown for report in reports.values()),
        "source_credibility_is_non_autonomous": (
            "requires human assessment" in reports["source-credibility"].markdown
        ),
        "technical_sections_present": (
            "Capabilities and implementation lessons" in reports["technical-lessons"].markdown
            and "Engineering risks and recommendations" in reports["technical-lessons"].markdown
        ),
        "opportunity_sections_present": (
            "Opportunity signals" in reports["opportunity-analysis"].markdown
            and "Constraints and risks" in reports["opportunity-analysis"].markdown
        ),
        "unsupported_template_rejected": expect_value_error(
            lambda: render_reviewed_report(investigation, "unknown-template"),
            "unsupported report template",
        ),
    }
    report = {
        "ok": all(checks.values()),
        "checks": checks,
        "templates": {
            name: {
                "title": item.title,
                "accepted_finding_ids": list(item.accepted_finding_ids),
                "evidence_ids": list(item.evidence_ids),
                "path": str(paths[name]),
            }
            for name, item in reports.items()
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "report.md").write_text(
        "# Reviewed report template proof\n\n"
        + "\n".join(f"- {'PASS' if value else 'FAIL'} `{name}`" for name, value in checks.items())
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
