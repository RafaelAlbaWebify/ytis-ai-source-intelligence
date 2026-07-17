from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
EXAMPLE = ROOT / "examples" / "portfolio-investigation"
OUT = ROOT / "artifacts" / "portfolio-example"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import InsightCard, JsonInvestigationRepository, TechnicalResearchService

REPORT_FILES = (
    "source-credibility.md",
    "business-model.md",
    "technical-lessons.md",
    "learning-roadmap.md",
    "opportunity-analysis.md",
)


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    investigation_payload = json.loads((EXAMPLE / "investigation.json").read_text(encoding="utf-8"))
    repository_root = OUT / "investigations"
    repository_root.mkdir(parents=True)
    target = repository_root / "portfolio-architecture-review.json"
    target.write_text(json.dumps(investigation_payload, indent=2), encoding="utf-8")
    investigation = JsonInvestigationRepository(repository_root).load("portfolio-architecture-review")
    TechnicalResearchService().validate_grounding(investigation)

    source_by_id = {source.source_id: source for source in investigation.sources}
    offset_matches = []
    for evidence in investigation.evidence:
        source = source_by_id[evidence.source_id]
        offset_matches.append(source.content[evidence.start_offset : evidence.end_offset] == evidence.text)

    card_payload = json.loads((EXAMPLE / "insight-card.json").read_text(encoding="utf-8"))
    card = InsightCard.from_dict(card_payload)
    reports = {name: (EXAMPLE / name).read_text(encoding="utf-8") for name in REPORT_FILES}
    evidence_ids = [evidence.evidence_id for evidence in investigation.evidence]
    source_files_match = (
        (EXAMPLE / "source-architecture.md").read_text(encoding="utf-8").strip()
        == investigation.sources[0].content
        and (EXAMPLE / "source-delivery.md").read_text(encoding="utf-8").strip()
        == investigation.sources[1].content
    )

    checks = {
        "repository_round_trip": investigation.investigation_id == "portfolio-architecture-review",
        "grounding_valid": True,
        "source_files_match_payload": source_files_match,
        "all_offsets_exact": all(offset_matches) and len(offset_matches) == 4,
        "all_findings_reviewed_accepted": all(
            investigation.review_status(finding.finding_id) == "accepted"
            for finding in investigation.findings
        ),
        "card_matches_accepted_finding": (
            card.finding_id == "finding-004"
            and card.review_status == "accepted"
            and card.evidence_ids == ("source-002:e002",)
        ),
        "all_five_reports_committed": set(reports) == set(REPORT_FILES),
        "every_report_contains_all_evidence_ids": all(
            all(evidence_id in report_text for evidence_id in evidence_ids)
            for report_text in reports.values()
        ),
        "every_report_has_review_boundary": all(
            "Only human-accepted findings are included." in report_text
            for report_text in reports.values()
        ),
        "source_credibility_avoids_autonomous_score": (
            "requires human assessment" in reports["source-credibility.md"]
        ),
        "readme_documents_safety_boundary": "Safety boundary" in (EXAMPLE / "README.md").read_text(encoding="utf-8"),
    }
    result = {
        "ok": all(checks.values()),
        "checks": checks,
        "investigation_id": investigation.investigation_id,
        "source_ids": [source.source_id for source in investigation.sources],
        "finding_ids": [finding.finding_id for finding in investigation.findings],
        "card_id": card.card_id,
        "report_files": list(REPORT_FILES),
    }
    (OUT / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (OUT / "report.md").write_text(
        "# Portfolio example proof\n\n"
        + "\n".join(f"- {'PASS' if value else 'FAIL'} `{name}`" for name, value in checks.items())
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
