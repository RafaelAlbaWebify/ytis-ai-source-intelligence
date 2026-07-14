from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nicegui import ui

from ytis.core.paths import project_root
from ytis.research import JsonInvestigationRepository, SourceDocument, TechnicalResearchService
from ytis.research.models import Investigation
from ytis.ui.layout import NAV_GROUPS, NAV_ITEMS, render_shell
from ytis.ui.state import AppState

_ROUTE = "/technical-research"
_NAV_ITEM = ("Technical Research", _ROUTE, "science")


def _storage_root() -> Path:
    configured = os.environ.get("YTIS_RESEARCH_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return project_root() / "technical_research"


def _register_navigation() -> None:
    if _NAV_ITEM in NAV_ITEMS:
        return
    for group_name, items in NAV_GROUPS:
        if group_name == "Evidence":
            items.insert(0, _NAV_ITEM)
            break
    else:
        NAV_GROUPS.append(("Evidence", [_NAV_ITEM]))
    NAV_ITEMS.insert(next((i for i, item in enumerate(NAV_ITEMS) if item[1] == "/search"), len(NAV_ITEMS)), _NAV_ITEM)


def register_technical_research_page(*, app_version: str) -> None:
    _register_navigation()
    state = AppState(app_version=app_version)

    @ui.page(_ROUTE)
    def technical_research_page() -> None:
        render_technical_research(state)


def render_technical_research(
    state: AppState,
    *,
    service: TechnicalResearchService | None = None,
    provider_label: str | None = None,
) -> None:
    render_shell(state, _ROUTE)
    root = _storage_root()
    repository = JsonInvestigationRepository(root / "investigations")
    active_service = service or TechnicalResearchService()
    reports_root = root / "reports"
    current: dict[str, Investigation | None] = {"value": None}

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-start gap-3 ytis-toolbar-row"):
            with ui.column().classes("gap-0"):
                ui.label("Technical Research Workbench").classes("text-3xl font-bold")
                ui.label(
                    "Turn public-safe technical text into evidence-linked findings, review each claim, and export approved conclusions."
                ).classes("text-sm text-slate-400")
            ui.badge(provider_label or active_service.provider_name, color="blue").props(
                "outline data-testid=active-provider"
            )

        with ui.card().classes("ytis-card p-4 w-full"):
            ui.label("1. Define the investigation").classes("text-xl font-bold")
            with ui.grid(columns=2).classes("w-full gap-3"):
                investigation_id = ui.input(
                    "Investigation ID",
                    value="technical-research-001",
                    validation={"Use letters, numbers, dots, underscores, or hyphens": lambda value: bool(value and all(c.isalnum() or c in "._-" for c in value))},
                ).classes("w-full").props("data-testid=investigation-id")
                title = ui.input("Title", value="Technical source investigation").classes("w-full").props("data-testid=investigation-title")
            question = ui.input(
                "Research question",
                value="What capabilities, constraints, risks, and recommendations are stated?",
            ).classes("w-full").props("data-testid=research-question")

        with ui.card().classes("ytis-card p-4 w-full"):
            ui.label("2. Add a technical source").classes("text-xl font-bold")
            source_title = ui.input("Source title", value="Public-safe technical note").classes("w-full").props("data-testid=source-title")
            source_text = ui.textarea(
                "Source text",
                value=(
                    "The platform supports local transcript cleaning and validated ZIP packaging. "
                    "The current workflow requires human review before findings are published. "
                    "A major risk is that unsupported claims could appear without evidence links. "
                    "The next step should add structured evidence-linked findings and reports."
                ),
            ).classes("w-full").props("rows=8 data-testid=source-text")

        status = ui.label("No investigation loaded.").classes("text-sm text-slate-400")
        findings_container = ui.column().classes("w-full gap-3")

        def review_counts(investigation: Investigation) -> tuple[int, int, int]:
            statuses = [investigation.review_status(item.finding_id) for item in investigation.findings]
            return statuses.count("accepted"), statuses.count("rejected"), statuses.count("pending")

        def update_status() -> None:
            investigation = current["value"]
            if investigation is None:
                status.set_text("No investigation loaded.")
                return
            accepted, rejected, pending = review_counts(investigation)
            status.set_text(
                f"{len(investigation.evidence)} evidence units · {len(investigation.findings)} findings · "
                f"{accepted} accepted · {rejected} rejected · {pending} pending"
            )

        def render_findings() -> None:
            findings_container.clear()
            investigation = current["value"]
            with findings_container:
                if investigation is None:
                    with ui.card().classes("ytis-card p-4 w-full"):
                        ui.label("Run or reopen an investigation to review findings.").classes("text-slate-400")
                    return
                evidence_by_id = {item.evidence_id: item for item in investigation.evidence}
                for index, finding in enumerate(investigation.findings, start=1):
                    with ui.card().classes("ytis-card p-4 w-full").props(f"data-testid=finding-{index}"):
                        with ui.row().classes("w-full justify-between items-start gap-3"):
                            with ui.column().classes("gap-1 flex-1"):
                                ui.label(finding.title).classes("text-lg font-bold")
                                with ui.row().classes("gap-2"):
                                    ui.badge(finding.category).props("outline")
                                    ui.badge(f"confidence {finding.confidence:.2f}").props("outline")
                                    review_badge = ui.badge(investigation.review_status(finding.finding_id)).props("outline")
                                ui.label(finding.summary).classes("text-sm text-slate-300")
                            with ui.row().classes("gap-2"):
                                def set_review(review_status: str, *, finding_id: str = finding.finding_id, badge: Any = review_badge) -> None:
                                    active = current["value"]
                                    if active is None:
                                        return
                                    active_service.review_finding(active, finding_id=finding_id, status=review_status)
                                    badge.set_text(review_status)
                                    update_status()

                                ui.button("Accept", icon="check", on_click=lambda _e, fn=set_review: fn("accepted")).props(
                                    f"outline dense data-testid=accept-{index}"
                                )
                                ui.button("Reject", icon="close", on_click=lambda _e, fn=set_review: fn("rejected")).props(
                                    f"outline dense color=negative data-testid=reject-{index}"
                                )
                        with ui.expansion("Evidence", icon="format_quote", value=True).classes("w-full"):
                            for evidence_id in finding.evidence_ids:
                                evidence = evidence_by_id[evidence_id]
                                ui.label(
                                    f"{evidence.evidence_id} · {evidence.source_id} · chars "
                                    f"{evidence.start_offset}-{evidence.end_offset}"
                                ).classes("text-xs text-blue-300")
                                ui.label(evidence.text).classes("text-sm text-slate-300")
            update_status()

        def analyze() -> None:
            try:
                source = SourceDocument(
                    source_id="source-001",
                    title=str(source_title.value or ""),
                    content=str(source_text.value or ""),
                    origin="technical-research-workbench",
                )
                current["value"] = active_service.create_investigation(
                    investigation_id=str(investigation_id.value or ""),
                    title=str(title.value or ""),
                    question=str(question.value or ""),
                    sources=[source],
                )
                render_findings()
                ui.notify("Evidence-linked findings created", type="positive")
            except Exception as exc:
                ui.notify(str(exc), type="negative")

        def save() -> None:
            investigation = current["value"]
            if investigation is None:
                ui.notify("Run or reopen an investigation first", type="warning")
                return
            try:
                path = repository.save(investigation)
                saved_select.options = repository.list_ids()
                saved_select.update()
                saved_select.value = investigation.investigation_id
                ui.notify(f"Saved {path.name}", type="positive")
            except Exception as exc:
                ui.notify(str(exc), type="negative")

        def export() -> None:
            investigation = current["value"]
            if investigation is None:
                ui.notify("Run or reopen an investigation first", type="warning")
                return
            try:
                output = reports_root / investigation.investigation_id
                markdown_path, json_path = active_service.generate_reports(investigation, output)
                ui.notify(f"Exported {markdown_path.name} and {json_path.name}", type="positive")
            except Exception as exc:
                ui.notify(str(exc), type="negative")

        def reopen() -> None:
            selected = str(saved_select.value or "").strip()
            if not selected:
                ui.notify("Choose a saved investigation", type="warning")
                return
            try:
                investigation = repository.load(selected)
                current["value"] = investigation
                investigation_id.value = investigation.investigation_id
                title.value = investigation.title
                question.value = investigation.question
                source_title.value = investigation.sources[0].title if investigation.sources else ""
                source_text.value = investigation.sources[0].content if investigation.sources else ""
                render_findings()
                ui.notify(f"Reopened {selected}", type="positive")
            except Exception as exc:
                ui.notify(str(exc), type="negative")

        with ui.card().classes("ytis-card p-4 w-full"):
            ui.label("3. Analyze and review").classes("text-xl font-bold")
            with ui.row().classes("gap-2 ytis-toolbar-row"):
                ui.button("Analyze source", icon="science", on_click=analyze, color="primary").props("data-testid=analyze-source")
                ui.button("Save investigation", icon="save", on_click=save).props("outline data-testid=save-investigation")
                ui.button("Export approved report", icon="download", on_click=export).props("outline data-testid=export-report")

        render_findings()

        with ui.card().classes("ytis-card p-4 w-full"):
            ui.label("4. Reopen saved work").classes("text-xl font-bold")
            with ui.row().classes("w-full gap-2 items-end ytis-toolbar-row"):
                saved_select = ui.select(
                    repository.list_ids(),
                    label="Saved investigation",
                ).classes("min-w-[320px]").props("data-testid=saved-investigation")
                ui.button("Reopen", icon="folder_open", on_click=reopen).props("outline data-testid=reopen-investigation")
            ui.label(f"Local storage: {root}").classes("text-xs text-slate-500")
