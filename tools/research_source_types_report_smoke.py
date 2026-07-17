from __future__ import annotations

import json
from pathlib import Path

from ytis.research import SOURCE_TYPES, SourceDocument, TechnicalResearchService

OUT = Path("artifacts/research-source-types-report")


def expect_error(fn, text: str) -> bool:
    try:
        fn()
    except ValueError as exc:
        return text in str(exc)
    return False


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    service = TechnicalResearchService()
    sources = [
        SourceDocument(
            source_id="source-001",
            title="Architecture article",
            content="The platform supports local evidence packaging.",
            source_type="article-notes",
            origin="https://example.test/article",
        ),
        SourceDocument(
            source_id="source-002",
            title="Role requirements",
            content="A major risk is loss of provenance during consolidation.",
            source_type="job-description",
            origin="role-fixture-2026",
        ),
    ]
    investigation = service.create_investigation(
        investigation_id="typed-source-proof",
        title="Typed source proof",
        question="What is supported and what is risky?",
        sources=sources,
    )
    service.accept_all(investigation)
    markdown_path, json_path = service.generate_reports(investigation, OUT)
    markdown = markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    checks = {
        "vocabulary_contains_required_types": {
            "technical-note",
            "pasted-text",
            "article-notes",
            "document-notes",
            "job-description",
            "transcript",
        }.issubset(set(SOURCE_TYPES)),
        "source_types_normalized": [source.source_type for source in investigation.sources]
        == ["article-notes", "job-description"],
        "origins_preserved": [source.origin for source in investigation.sources]
        == ["https://example.test/article", "role-fixture-2026"],
        "unsupported_type_rejected": expect_error(
            lambda: SourceDocument(
                source_id="bad",
                title="Bad",
                content="content",
                source_type="unknown-source",
                origin="fixture",
            ),
            "unsupported source type",
        ),
        "blank_origin_rejected": expect_error(
            lambda: SourceDocument(
                source_id="bad-origin",
                title="Bad origin",
                content="content",
                source_type="text",
                origin=" ",
            ),
            "origin is required",
        ),
        "markdown_has_source_register": "## Source register" in markdown,
        "markdown_has_source_types": "`article-notes`" in markdown and "`job-description`" in markdown,
        "markdown_has_origins": "https://example.test/article" in markdown and "role-fixture-2026" in markdown,
        "markdown_has_evidence_counts": markdown.count("- Evidence units: 1") == 2,
        "json_has_typed_sources": [source["source_type"] for source in payload["sources"]]
        == ["article-notes", "job-description"],
    }
    report = {"ok": all(checks.values()), "checks": checks}
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "report.md").write_text(
        "# Research source types and report register\n\n"
        + "\n".join(f"- {'PASS' if passed else 'FAIL'} `{name}`" for name, passed in checks.items())
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
