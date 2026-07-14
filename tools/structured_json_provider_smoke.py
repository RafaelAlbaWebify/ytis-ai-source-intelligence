from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "structured-json-provider"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import (
    SourceDocument,
    StructuredJsonFindingProvider,
    StructuredProviderError,
    TechnicalResearchService,
)


def expect_error(action, expected_text: str) -> bool:
    try:
        action()
    except (StructuredProviderError, ValueError) as exc:
        return expected_text in str(exc)
    return False


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    source = SourceDocument(
        source_id="source-001",
        title="Structured provider fixture",
        origin="offline-fixture",
        content=(
            "The platform supports local evidence processing. "
            "A major risk is unsupported claims without citations."
        ),
    )
    prompts: list[str] = []

    def valid_generator(prompt: str) -> str:
        prompts.append(prompt)
        return json.dumps(
            {
                "findings": [
                    {
                        "finding_id": "f001",
                        "title": "Local evidence processing",
                        "summary": "The platform supports local evidence processing.",
                        "category": "capability",
                        "evidence_ids": ["source-001:e001"],
                        "confidence": 0.91,
                    },
                    {
                        "finding_id": "f002",
                        "title": "Unsupported claims risk",
                        "summary": "Unsupported claims without citations are a major risk.",
                        "category": "risk",
                        "evidence_ids": ["source-001:e002"],
                        "confidence": 0.88,
                    },
                ]
            }
        )

    provider = StructuredJsonFindingProvider(
        valid_generator,
        provider_name="offline-structured-fixture",
    )
    service = TechnicalResearchService(provider=provider)
    investigation = service.create_investigation(
        investigation_id="structured-provider-001",
        title="Structured provider proof",
        question="What capabilities and risks are explicitly stated?",
        sources=[source],
    )

    checks: dict[str, bool] = {
        "provider_name_exposed": service.provider_name == "offline-structured-fixture",
        "generator_invoked_once": len(prompts) == 1,
        "question_in_prompt": "What capabilities and risks" in prompts[0],
        "all_evidence_ids_in_prompt": all(
            item.evidence_id in prompts[0] for item in investigation.evidence
        ),
        "source_ranges_in_prompt": all(
            f"chars={item.start_offset}-{item.end_offset}" in prompts[0]
            for item in investigation.evidence
        ),
        "two_findings_created": len(investigation.findings) == 2,
        "findings_grounded": all(
            evidence_id in {item.evidence_id for item in investigation.evidence}
            for finding in investigation.findings
            for evidence_id in finding.evidence_ids
        ),
        "confidence_preserved": investigation.findings[0].confidence == 0.91,
    }

    def build_with(raw: object, *, max_findings: int = 50) -> None:
        test_provider = StructuredJsonFindingProvider(
            lambda prompt: raw,  # type: ignore[return-value]
            max_findings=max_findings,
        )
        TechnicalResearchService(provider=test_provider).create_investigation(
            investigation_id="negative-case",
            title="Negative case",
            question="What is stated?",
            sources=[source],
        )

    checks.update(
        {
            "empty_response_rejected": expect_error(lambda: build_with(""), "non-empty"),
            "non_string_response_rejected": expect_error(
                lambda: build_with({"findings": []}), "non-empty JSON text"
            ),
            "invalid_json_rejected": expect_error(
                lambda: build_with("not-json"), "invalid JSON response"
            ),
            "non_object_root_rejected": expect_error(
                lambda: build_with("[]"), "root must be an object"
            ),
            "extra_root_key_rejected": expect_error(
                lambda: build_with('{"findings":[],"meta":{}}'), "extra=['meta']"
            ),
            "missing_findings_rejected": expect_error(
                lambda: build_with("{}"), "missing=['findings']"
            ),
            "findings_type_rejected": expect_error(
                lambda: build_with('{"findings":{}}'), "findings must be an array"
            ),
            "record_type_rejected": expect_error(
                lambda: build_with('{"findings":["bad"]}'), "must be an object"
            ),
            "extra_finding_key_rejected": expect_error(
                lambda: build_with(
                    json.dumps(
                        {
                            "findings": [
                                {
                                    "finding_id": "f001",
                                    "title": "Title",
                                    "summary": "Summary",
                                    "category": "risk",
                                    "evidence_ids": ["source-001:e001"],
                                    "confidence": 0.8,
                                    "unexpected": True,
                                }
                            ]
                        }
                    )
                ),
                "extra=['unexpected']",
            ),
            "unsupported_category_rejected": expect_error(
                lambda: build_with(
                    json.dumps(
                        {
                            "findings": [
                                {
                                    "finding_id": "f001",
                                    "title": "Title",
                                    "summary": "Summary",
                                    "category": "opinion",
                                    "evidence_ids": ["source-001:e001"],
                                    "confidence": 0.8,
                                }
                            ]
                        }
                    )
                ),
                "unsupported category",
            ),
            "empty_evidence_array_rejected": expect_error(
                lambda: build_with(
                    json.dumps(
                        {
                            "findings": [
                                {
                                    "finding_id": "f001",
                                    "title": "Title",
                                    "summary": "Summary",
                                    "category": "risk",
                                    "evidence_ids": [],
                                    "confidence": 0.8,
                                }
                            ]
                        }
                    )
                ),
                "non-empty string array",
            ),
            "boolean_confidence_rejected": expect_error(
                lambda: build_with(
                    json.dumps(
                        {
                            "findings": [
                                {
                                    "finding_id": "f001",
                                    "title": "Title",
                                    "summary": "Summary",
                                    "category": "risk",
                                    "evidence_ids": ["source-001:e001"],
                                    "confidence": True,
                                }
                            ]
                        }
                    )
                ),
                "confidence must be numeric",
            ),
            "invented_evidence_rejected_by_service": expect_error(
                lambda: build_with(
                    json.dumps(
                        {
                            "findings": [
                                {
                                    "finding_id": "f001",
                                    "title": "Invented",
                                    "summary": "Invented evidence reference.",
                                    "category": "risk",
                                    "evidence_ids": ["missing:e999"],
                                    "confidence": 0.8,
                                }
                            ]
                        }
                    )
                ),
                "cites missing evidence",
            ),
            "maximum_findings_enforced": expect_error(
                lambda: build_with(
                    json.dumps(
                        {
                            "findings": [
                                {
                                    "finding_id": f"f{index:03d}",
                                    "title": "Title",
                                    "summary": "Summary",
                                    "category": "risk",
                                    "evidence_ids": ["source-001:e001"],
                                    "confidence": 0.8,
                                }
                                for index in range(2)
                            ]
                        }
                    ),
                    max_findings=1,
                ),
                "exceeds maximum",
            ),
        }
    )

    report = {
        "ok": all(checks.values()),
        "provider_name": service.provider_name,
        "checks": checks,
        "finding_count": len(investigation.findings),
        "prompt": prompts[0],
    }
    (OUT / "structured-provider-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    lines = [
        "# Structured JSON Provider Contract",
        "",
        f"- Overall: {'PASS' if report['ok'] else 'FAIL'}",
        f"- Provider: `{service.provider_name}`",
        f"- Findings: {len(investigation.findings)}",
        "",
        "## Checks",
        "",
    ]
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} `{name}`" for name, passed in checks.items()
    )
    (OUT / "structured-provider-report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
