from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "research-insight-cards"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import (
    JsonInsightCardRepository,
    SourceDocument,
    TechnicalResearchService,
    create_insight_card,
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
    store = OUT / "store"
    service = TechnicalResearchService()
    investigation = service.create_investigation(
        investigation_id="insight-proof-001",
        title="Insight card proof",
        question="What should be retained and acted on?",
        sources=[
            SourceDocument(
                source_id="source-001",
                title="Public-safe architecture note",
                content=(
                    "The platform supports evidence-linked report generation. "
                    "A major risk is losing provenance during manual consolidation."
                ),
                origin="deterministic-fixture",
            )
        ],
    )
    accepted = investigation.findings[0]
    pending = investigation.findings[1]
    service.review_finding(investigation, finding_id=accepted.finding_id, status="accepted")
    card = create_insight_card(
        investigation,
        finding_id=accepted.finding_id,
        action="Preserve source-qualified evidence in every exported report.",
    )
    repository = JsonInsightCardRepository(store)
    path = repository.save(card)
    loaded = repository.load(card.card_id)

    checks = {
        "accepted_finding_converted": card.finding_id == accepted.finding_id,
        "claim_preserved": card.claim == accepted.summary,
        "evidence_preserved": card.evidence_ids == accepted.evidence_ids,
        "confidence_preserved": card.confidence == accepted.confidence,
        "action_preserved": card.action.startswith("Preserve source-qualified"),
        "review_status_accepted": card.review_status == "accepted",
        "atomic_file_created": path.exists() and not path.with_suffix(".json.tmp").exists(),
        "round_trip_equal": loaded == card,
        "list_ids_exact": repository.list_ids() == [card.card_id],
        "pending_finding_rejected": expect_value_error(
            lambda: create_insight_card(investigation, finding_id=pending.finding_id, action="Do something"),
            "only accepted findings",
        ),
        "unknown_finding_rejected": expect_value_error(
            lambda: create_insight_card(investigation, finding_id="missing", action="Do something"),
            "unknown finding",
        ),
        "duplicate_save_rejected": expect_value_error(lambda: repository.save(card), "already exists"),
        "unsafe_id_rejected": expect_value_error(
            lambda: create_insight_card(
                investigation,
                finding_id=accepted.finding_id,
                action="Do something",
                card_id="../escape",
            ) and repository.save(
                create_insight_card(
                    investigation,
                    finding_id=accepted.finding_id,
                    action="Do something",
                    card_id="../escape",
                )
            ),
            "unsafe characters",
        ),
    }
    payload = json.loads(path.read_text(encoding="utf-8"))
    checks["persisted_schema_exact"] = set(payload) == {
        "card_id",
        "investigation_id",
        "finding_id",
        "claim",
        "evidence_ids",
        "confidence",
        "action",
        "review_status",
    }

    report = {"ok": all(checks.values()), "checks": checks, "card": card.to_dict()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "report.md").write_text(
        "# Evidence-linked insight card proof\n\n"
        + "\n".join(f"- {'PASS' if value else 'FAIL'} `{name}`" for name, value in checks.items())
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
