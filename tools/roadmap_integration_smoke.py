from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "roadmap-integration"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import (
    JsonInsightCardRepository,
    SourceDocument,
    TechnicalResearchService,
    create_insight_card,
    edit_source,
    find_duplicate_sources,
    import_local_source,
    move_source,
    render_reviewed_report,
)


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    import_root = OUT / "imports"
    import_root.mkdir()
    local_path = import_root / "architecture.md"
    local_path.write_text(
        "The platform supports evidence-linked local reports. "
        "The workflow requires human review before reuse.",
        encoding="utf-8",
    )

    imported = import_local_source(
        local_path,
        source_id="source-001",
        title="Architecture article",
        source_type="article-notes",
        allowed_root=import_root,
    )
    initial_sources = (
        imported,
        SourceDocument(
            source_id="source-002",
            title="Architecture article copy",
            source_type="document-notes",
            origin="local-copy",
            content=(
                "  THE platform supports evidence-linked local reports. "
                "The workflow requires human review before reuse.  "
            ),
        ),
        SourceDocument(
            source_id="source-003",
            title="Role requirement draft",
            source_type="job-description",
            origin="role-fixture-draft",
            content=(
                "A major risk is losing provenance during manual consolidation. "
                "The next step should preserve source-qualified evidence in reusable outputs."
            ),
        ),
    )
    edited_sources = edit_source(
        initial_sources,
        source_id="source-003",
        title="Role requirement",
        origin="role-fixture",
    )
    sources = move_source(edited_sources, source_id="source-003", target_index=1)

    duplicate_groups = find_duplicate_sources(list(sources))
    service = TechnicalResearchService()
    investigation = service.create_investigation(
        investigation_id="roadmap-integration",
        title="Roadmap integration proof",
        question="What capabilities, constraints, risks, and recommendations are stated?",
        sources=list(sources),
    )
    accepted = investigation.findings[0]
    service.review_finding(investigation, finding_id=accepted.finding_id, status="accepted")
    card = create_insight_card(
        investigation,
        finding_id=accepted.finding_id,
        action="Preserve evidence provenance in every reusable output.",
    )
    card_repository = JsonInsightCardRepository(OUT / "cards")
    card_path = card_repository.save(card)
    loaded_card = card_repository.load(card.card_id)
    reviewed_report = render_reviewed_report(investigation, "technical-lessons")
    report_path = OUT / "technical-lessons.md"
    report_path.write_text(reviewed_report.markdown, encoding="utf-8")

    checks = {
        "local_source_imported": imported.content.startswith("The platform supports"),
        "local_origin_preserved": imported.origin == str(local_path.resolve()),
        "source_edit_preserved_stable_id": edited_sources[2].source_id == "source-003",
        "source_edit_updated_metadata": (
            edited_sources[2].title == "Role requirement"
            and edited_sources[2].origin == "role-fixture"
        ),
        "source_reorder_exact": [source.source_id for source in sources]
        == ["source-001", "source-003", "source-002"],
        "typed_sources_preserved": [source.source_type for source in investigation.sources]
        == ["article-notes", "job-description", "document-notes"],
        "origins_preserved": [source.origin for source in investigation.sources]
        == [str(local_path.resolve()), "role-fixture", "local-copy"],
        "duplicate_advisory_exact": [group.source_ids for group in duplicate_groups]
        == [("source-001", "source-002")],
        "duplicate_detection_non_destructive": len(investigation.sources) == 3,
        "analysis_grounded": all(finding.evidence_ids for finding in investigation.findings),
        "accepted_card_created": card.review_status == "accepted",
        "card_action_explicit": card.action.startswith("Preserve evidence provenance"),
        "card_round_trip": loaded_card == card and card_path.exists(),
        "report_accepted_ids_exact": reviewed_report.accepted_finding_ids == (accepted.finding_id,),
        "report_evidence_exact": reviewed_report.evidence_ids == accepted.evidence_ids,
        "report_review_boundary": "Only human-accepted findings are included." in reviewed_report.markdown,
        "report_source_provenance": accepted.evidence_ids[0] in reviewed_report.markdown,
        "report_written": report_path.exists(),
    }
    result = {
        "ok": all(checks.values()),
        "checks": checks,
        "source_order": [source.source_id for source in sources],
        "duplicate_groups": [
            {"fingerprint": group.fingerprint, "source_ids": list(group.source_ids)}
            for group in duplicate_groups
        ],
        "card": card.to_dict(),
        "report": {
            "template": reviewed_report.template,
            "accepted_finding_ids": list(reviewed_report.accepted_finding_ids),
            "evidence_ids": list(reviewed_report.evidence_ids),
        },
    }
    (OUT / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (OUT / "report.md").write_text(
        "# Roadmap integration proof\n\n"
        + "\n".join(f"- {'PASS' if value else 'FAIL'} `{name}`" for name, value in checks.items())
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
