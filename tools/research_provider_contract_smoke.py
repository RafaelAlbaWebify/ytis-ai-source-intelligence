from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "research-provider-contract"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import Finding, SourceDocument, TechnicalResearchService


class GroundedFixtureProvider:
    provider_name = "grounded-fixture"

    def generate_findings(self, *, question: str, evidence: list) -> list[Finding]:
        assert question
        return [
            Finding(
                finding_id="provider-f001",
                title="Provider-generated grounded finding",
                summary=evidence[0].text,
                category="capability",
                evidence_ids=(evidence[0].evidence_id,),
                confidence=0.91,
            )
        ]


class UngroundedFixtureProvider:
    provider_name = "ungrounded-fixture"

    def generate_findings(self, *, question: str, evidence: list) -> list[Finding]:
        del question, evidence
        return [
            Finding(
                finding_id="provider-f001",
                title="Ungrounded provider finding",
                summary="This finding cites evidence that does not exist.",
                category="risk",
                evidence_ids=("missing:e999",),
                confidence=0.99,
            )
        ]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    source = SourceDocument(
        source_id="provider-source",
        title="Provider contract fixture",
        content="The platform supports provider-independent evidence analysis.",
    )
    service = TechnicalResearchService(provider=GroundedFixtureProvider())
    investigation = service.create_investigation(
        investigation_id="provider-contract-001",
        title="Provider contract proof",
        question="What capability is stated?",
        sources=[source],
    )

    checks = {
        "provider_name_exposed": service.provider_name == "grounded-fixture",
        "custom_provider_used": len(investigation.findings) == 1,
        "finding_grounded": investigation.findings[0].evidence_ids == (investigation.evidence[0].evidence_id,),
        "default_provider_available": TechnicalResearchService().provider_name == "deterministic-rules",
    }

    try:
        TechnicalResearchService(provider=UngroundedFixtureProvider()).create_investigation(
            investigation_id="provider-contract-002",
            title="Ungrounded rejection proof",
            question="What risk is stated?",
            sources=[source],
        )
        checks["ungrounded_provider_rejected"] = False
    except ValueError as exc:
        checks["ungrounded_provider_rejected"] = "missing evidence" in str(exc)

    report = {
        "ok": all(checks.values()),
        "provider": service.provider_name,
        "checks": checks,
        "finding": investigation.findings[0].finding_id,
        "evidence": investigation.findings[0].evidence_ids,
    }
    (OUT / "provider-contract-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "provider-contract-report.md").write_text(
        "# Research Provider Contract Report\n\n"
        + f"- Overall: {'PASS' if report['ok'] else 'FAIL'}\n"
        + f"- Provider: `{report['provider']}`\n\n"
        + "## Checks\n\n"
        + "\n".join(f"- {'PASS' if value else 'FAIL'} `{name}`" for name, value in checks.items())
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
