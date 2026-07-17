from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "related-insight-cards"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import InsightCard, JsonInsightCardRepository, find_related_cards, normalize_card_claim


def expect_value_error(fn, text: str) -> bool:
    try:
        fn()
    except ValueError as exc:
        return text in str(exc)
    return False


def card(card_id: str, claim: str, evidence_ids: tuple[str, ...]) -> InsightCard:
    return InsightCard(
        card_id=card_id,
        investigation_id="related-card-proof",
        finding_id=f"finding-{card_id}",
        claim=claim,
        evidence_ids=evidence_ids,
        confidence=0.9,
        action="Review the relationship manually before consolidation.",
    )


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    repository = JsonInsightCardRepository(OUT / "cards")
    cards = [
        card("card-a", "Preserve evidence provenance.", ("source-001:e001",)),
        card("card-b", "  preserve   EVIDENCE provenance. ", ("source-002:e001",)),
        card("card-c", "Retain exact source references.", ("source-001:e001", "source-003:e001")),
        card("card-d", "A completely distinct reviewed action.", ("source-004:e001",)),
    ]
    for item in cards:
        repository.save(item)
    loaded = repository.list_cards()
    relations = find_related_cards(loaded)
    by_pair = {relation.card_ids: relation for relation in relations}

    checks = {
        "claim_normalization_case_whitespace_insensitive": (
            normalize_card_claim(cards[0].claim) == normalize_card_claim(cards[1].claim)
        ),
        "repository_list_cards_round_trip": loaded == cards,
        "same_claim_relation_found": by_pair[("card-a", "card-b")].reasons == ("same-normalized-claim",),
        "shared_evidence_relation_found": by_pair[("card-a", "card-c")].reasons == ("shared-evidence",),
        "shared_evidence_exact": by_pair[("card-a", "card-c")].shared_evidence_ids == ("source-001:e001",),
        "distinct_card_not_related": all("card-d" not in relation.card_ids for relation in relations),
        "relations_deterministic": [relation.card_ids for relation in relations]
        == [("card-a", "card-b"), ("card-a", "card-c")],
        "cards_unchanged": repository.list_cards() == cards,
        "duplicate_ids_rejected": expect_value_error(
            lambda: find_related_cards([cards[0], cards[0]]),
            "card IDs must be unique",
        ),
    }
    result = {
        "ok": all(checks.values()),
        "checks": checks,
        "relations": [
            {
                "card_ids": list(relation.card_ids),
                "reasons": list(relation.reasons),
                "shared_evidence_ids": list(relation.shared_evidence_ids),
            }
            for relation in relations
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (OUT / "report.md").write_text(
        "# Related insight card advisory proof\n\n"
        + "\n".join(f"- {'PASS' if value else 'FAIL'} `{name}`" for name, value in checks.items())
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
