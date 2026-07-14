from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "technical-research-repository"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import JsonInvestigationRepository, SourceDocument, TechnicalResearchService


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    store = OUT / "store"
    reports = OUT / "reports"
    repository = JsonInvestigationRepository(store)
    service = TechnicalResearchService()

    source = SourceDocument(
        source_id="source-001",
        title="Persistence fixture",
        origin="deterministic-fixture",
        content=(
            "The system supports local research persistence. "
            "The workflow requires human review before publication. "
            "A risk is that corrupt files could silently replace validated investigations. "
            "The next step should verify atomic save and validated load behavior."
        ),
    )
    investigation = service.create_investigation(
        investigation_id="repository-smoke-001",
        title="Technical research repository smoke",
        question="Can a validated investigation survive a local persistence round trip?",
        sources=[source],
    )
    service.review_finding(
        investigation,
        finding_id=investigation.findings[0].finding_id,
        status="accepted",
        note="Accepted before persistence.",
    )
    service.review_finding(
        investigation,
        finding_id=investigation.findings[1].finding_id,
        status="rejected",
        note="Rejected before persistence.",
    )

    saved_path = repository.save(investigation)
    loaded = repository.load(investigation.investigation_id)
    service.validate_grounding(loaded)
    markdown_path, json_path = service.generate_reports(loaded, reports)

    checks = {
        "saved_file_exists": saved_path.exists(),
        "temporary_file_absent": not saved_path.with_suffix(".json.tmp").exists(),
        "list_contains_id": repository.list_ids() == [investigation.investigation_id],
        "round_trip_equal": loaded.to_dict() == investigation.to_dict(),
        "grounding_survives": all(f.evidence_ids for f in loaded.findings),
        "accepted_review_survives": loaded.review_status(loaded.findings[0].finding_id) == "accepted",
        "rejected_review_survives": loaded.review_status(loaded.findings[1].finding_id) == "rejected",
        "reports_generated": markdown_path.exists() and json_path.exists(),
    }

    invalid_id_rejected = False
    try:
        repository.load("../escape")
    except ValueError:
        invalid_id_rejected = True
    checks["invalid_id_rejected"] = invalid_id_rejected

    corrupt_path = store / "corrupt.json"
    corrupt_path.write_text("{not-json", encoding="utf-8")
    corrupt_rejected = False
    try:
        repository.load("corrupt")
    except ValueError:
        corrupt_rejected = True
    checks["corrupt_json_rejected"] = corrupt_rejected

    mismatch_path = store / "mismatch.json"
    mismatch_payload = loaded.to_dict()
    mismatch_payload["investigation_id"] = "different-id"
    mismatch_path.write_text(json.dumps(mismatch_payload), encoding="utf-8")
    mismatch_rejected = False
    try:
        repository.load("mismatch")
    except ValueError:
        mismatch_rejected = True
    checks["filename_payload_mismatch_rejected"] = mismatch_rejected

    deleted = repository.delete(investigation.investigation_id)
    checks["delete_existing"] = deleted and not saved_path.exists()
    checks["delete_missing_is_false"] = repository.delete(investigation.investigation_id) is False

    result = {"ok": all(checks.values()), "checks": checks}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "repository-smoke.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
