from __future__ import annotations

from nicegui import ui

from ytis.research import SourceDocument, TechnicalResearchService
from ytis.ui.layout import NAV_GROUPS, NAV_ITEMS, render_shell
from ytis.ui.state import AppState

_ROUTE = "/demo"
_NAV_ITEM = ("Demo", _ROUTE, "play_circle")


def _register_navigation() -> None:
    if _NAV_ITEM in NAV_ITEMS:
        return
    for group_name, items in NAV_GROUPS:
        if group_name == "Cockpit":
            items.append(_NAV_ITEM)
            break
    NAV_ITEMS.insert(1, _NAV_ITEM)


def register_demo_page(*, app_version: str) -> None:
    _register_navigation()
    state = AppState(app_version=app_version)

    @ui.page(_ROUTE)
    def demo_page() -> None:
        render_demo(state)


def render_demo(state: AppState) -> None:
    render_shell(state, _ROUTE)
    service = TechnicalResearchService()
    source = SourceDocument(
        source_id="demo-source-001",
        title="Public-safe YTIS architecture note",
        origin="built-in-demo-fixture",
        content=(
            "The platform supports local evidence-linked research workflows. "
            "The current process requires human review before conclusions are reused. "
            "A major risk is losing provenance when claims are copied without evidence IDs. "
            "The next step should preserve source-qualified evidence in every reusable output."
        ),
    )
    results = ui.column().classes("w-full gap-3")

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-start gap-3 ytis-toolbar-row"):
            with ui.column().classes("gap-0"):
                ui.label("YTIS Demo Journey").classes("text-3xl font-bold")
                ui.label(
                    "A focused, local-only demonstration of source → evidence → findings → human review."
                ).classes("text-sm text-slate-400")
            ui.badge("Deterministic offline demo", color="blue").props("outline data-testid=demo-provider")

        with ui.card().classes("ytis-card p-4 w-full"):
            ui.label("Public-safe source").classes("text-xl font-bold")
            ui.label(source.title).classes("font-bold").props("data-testid=demo-source-title")
            ui.label(source.content).classes("text-sm text-slate-300").props("data-testid=demo-source-text")
            ui.label("No network access, uploads, credentials, or persistence are used.").classes(
                "text-xs text-slate-500"
            )

        with ui.card().classes("ytis-card p-4 w-full"):
            ui.label("Run the evidence-linked analysis").classes("text-xl font-bold")
            ui.label(
                "Generated findings remain proposals until a person reviews them."
            ).classes("text-sm text-amber-300").props("data-testid=demo-review-warning")

            def analyze() -> None:
                investigation = service.create_investigation(
                    investigation_id="public-demo",
                    title="YTIS public demo",
                    question="What capabilities, constraints, risks, and recommendations are stated?",
                    sources=[source],
                )
                evidence_by_id = {item.evidence_id: item for item in investigation.evidence}
                results.clear()
                with results:
                    ui.label(
                        f"{len(investigation.evidence)} evidence units · {len(investigation.findings)} findings"
                    ).classes("text-sm text-slate-400").props("data-testid=demo-summary")
                    for index, finding in enumerate(investigation.findings, start=1):
                        with ui.card().classes("ytis-card p-4 w-full").props(f"data-testid=demo-finding-{index}"):
                            ui.label(finding.title).classes("text-lg font-bold")
                            with ui.row().classes("gap-2"):
                                ui.badge(finding.category).props("outline")
                                ui.badge(f"confidence {finding.confidence:.2f}").props("outline")
                                ui.badge("pending human review").props("outline color=warning")
                            ui.label(finding.summary).classes("text-sm text-slate-300")
                            for evidence_id in finding.evidence_ids:
                                evidence = evidence_by_id[evidence_id]
                                ui.label(
                                    f"{evidence.evidence_id} · {evidence.source_id} · chars "
                                    f"{evidence.start_offset}-{evidence.end_offset}"
                                ).classes("text-xs text-blue-300")
                                ui.label(evidence.text).classes("text-sm text-slate-400")

            ui.button("Analyze demo source", icon="science", on_click=analyze, color="primary").props(
                "data-testid=run-demo"
            )

        results.move()
        with results:
            ui.label("Select Analyze to generate the deterministic demo findings.").classes(
                "text-sm text-slate-500"
            ).props("data-testid=demo-empty")
