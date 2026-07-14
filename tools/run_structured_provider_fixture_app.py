from __future__ import annotations

import json

from nicegui import ui

from ytis.ui.layout import register_pages
from ytis.ui.pages_technical_research_configured import (
    register_configured_technical_research_page,
)

APP_VERSION = "v0.10.2-fixture"


def fixture_generator(prompt: str) -> str:
    required = ["source-001:e001", "source-001:e002", "source-001:e003", "source-001:e004"]
    missing = [evidence_id for evidence_id in required if evidence_id not in prompt]
    if missing:
        raise ValueError(f"fixture prompt missing evidence IDs: {missing}")
    return json.dumps(
        {
            "findings": [
                {
                    "finding_id": "structured-f001",
                    "title": "Local processing capability",
                    "summary": "The source states that local transcript cleaning and validated ZIP packaging are supported.",
                    "category": "capability",
                    "evidence_ids": ["source-001:e001"],
                    "confidence": 0.91,
                },
                {
                    "finding_id": "structured-f002",
                    "title": "Human review constraint",
                    "summary": "The workflow requires human review before findings are published.",
                    "category": "constraint",
                    "evidence_ids": ["source-001:e002"],
                    "confidence": 0.96,
                },
            ]
        }
    )


def main() -> None:
    register_configured_technical_research_page(
        app_version=APP_VERSION,
        structured_generator=fixture_generator,
    )
    register_pages(app_version=APP_VERSION)
    ui.run(
        title="YTIS Structured Provider Fixture",
        host="127.0.0.1",
        port=8080,
        reload=False,
        dark=True,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
