from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from nicegui import ui

from ytis.core.paths import project_root
from ytis.research import (
    REPORT_TEMPLATES,
    JsonInsightCardRepository,
    JsonInvestigationRepository,
    SourceDocument,
    TechnicalResearchService,
    create_insight_card,
    edit_source,
    find_duplicate_sources,
    move_source,
    write_reviewed_report,
)
from ytis.research.models import Investigation
from ytis.ui.layout import NAV_GROUPS, NAV_ITEMS, render_shell
from ytis.ui.state import AppState

_ROUTE = "/technical-research"
_NAV_ITEM = ("Technical Research", _ROUTE, "science")
_SOURCE_TYPE_OPTIONS = {
    "technical-note": "Technical note",
    "pasted-text": "Pasted text",
    "article-notes": "Article notes",
    "document-notes": "Document notes",
    "job-description": "Job description",
    "transcript": "Transcript",
    "text": "Generic text",
}
_REPORT_TEMPLATE_OPTIONS = {
    "source-credibility": "Source credibility and provenance",
    "business-model": "Business model extraction",
    "technical-lessons": "Technical lessons",
    "learning-roadmap": "Learning roadmap",
    "opportunity-analysis": "Opportunity analysis",
}


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
    card_repository = JsonInsightCardRepository(root / "insight_cards")
    active_service = service or TechnicalResearchService()
    reports_root = root / "reports"
    current: dict[str, Investigation | None] = {"value": None}
    source_pack: list[SourceDocument] = []
    editing_source_id: dict[str, str | None] = {"value": None}

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-start gap-3 ytis-toolbar-row"):
            with ui.column().classes("gap-0"):
                ui.label("Technical Research Workbench").classes("text-3xl font-bold")
                ui.label(
                    "Turn public-safe technical sources into evidence-linked findings, review each claim, and export approved conclusions."
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

        source_pack_container = ui.column().classes("w-full gap-2")
        duplicate_container = ui.column().classes("w-full gap-2")

        with ui.card().classes("ytis-card p-4 w-full"):
            ui.label("2. Build the source pack").classes("text-xl font-bold")
            ui.label("Add, edit, and reorder public-safe sources. Source IDs remain stable.").classes("text-sm text-slate-400")
            with ui.grid(columns=2).classes("w-full gap-3"):
                source_title = ui.input("Source title", value="Public-safe technical note").classes("w-full").props("data-testid=source-title")
                source_type = ui.select(
                    _SOURCE_TYPE_OPTIONS,
                    value="technical-note",
                    label="Source type",
                ).classes("w-full").props("data-testid=source-type")
            source_origin = ui.input(
                "Origin or reference",
                value="manual-workbench-entry",
            ).classes("w-full").props("data-testid=source-origin")
            source_text = ui.textarea(
                "Source text",
                value=(
                    "The platform supports local transcript cleaning and validated ZIP packaging. "
                    "The current workflow requires human review before findings are published. "
                    "A major risk is that unsupported claims could appear without evidence links. "
                    "The next step should add structured evidence-linked findings and reports."
                ),
            ).classes("w-full").props("rows=6 data-testid=source-text")
            edit_status = ui.label("Adding a new source.").classes("text-xs text-slate-500").props(
                "data-testid=source-edit-status"
            )

            def clear_draft() -> None:
                editing_source_id["value"] = None
                source_title.value = ""
                source_type.value = "technical-note"
                source_origin.value = "manual-workbench-entry"
                source_text.value = ""
                edit_status.set_text("Adding a new source.")
                save_source_button.set_text("Add source")
                save_source_button.props("icon=add")

            with ui.row().classes("gap-2"):
                save_source_button = ui.button("Add source", icon="add", color="primary").props("data-testid=add-source")
                ui.button("Clear draft", icon="clear", on_click=clear_draft).props("outline data-testid=clear-source-draft")
            ui.separator()
            ui.label("Staged sources").classes("text-sm font-bold")
            source_pack_container.move()
            duplicate_container.move()

        def next_source_id() -> str:
            used: set[int] = set()
            for source in source_pack:
                prefix, separator, suffix = source.source_id.rpartition("-")
                if separator and prefix == "source" and suffix.isdigit():
                    used.add(int(suffix))
            candidate = 1
            while candidate in used:
                candidate += 1
            return f"source-{candidate:03d}"

        def render_duplicate_warnings() -> None:
            duplicate_container.clear()
            groups = find_duplicate_sources(source_pack)
            if not groups:
                return
            with duplicate_container:
                with ui.card().classes("ytis-mini-card p-3 w-full border-amber-500/40").props(
                    "data-testid=duplicate-warning"
                ):
                    ui.label("Possible duplicate sources detected").classes("font-bold text-amber-300")
                    ui.label(
                        "Duplicates are advisory only. YTIS has not removed, merged, or rejected any source."
                    ).classes("text-sm text-slate-400")
                    for index, group in enumerate(groups, start=1):
                        ui.label(
                            f"Group {index}: {', '.join(group.source_ids)} · fingerprint {group.fingerprint[:12]}…"
                        ).classes("text-sm text-slate-300").props(f"data-testid=duplicate-group-{index}")

        def begin_edit(source: SourceDocument) -> None:
            editing_source_id["value"] = source.source_id
            source_title.value = source.title
            source_type.value = source.source_type
            source_origin.value = source.origin
            source_text.value = source.content
            edit_status.set_text(f"Editing {source.source_id}; its ID and position will be preserved.")
            save_source_button.set_text("Update source")
            save_source_button.props("icon=save")

        def render_source_pack() -> None:
            source_pack_container.clear()
            with source_pack_container:
                if not source_pack:
                    ui.label("No sources staged.").classes("text-sm text-slate-500").props("data-testid=source-pack-empty")
                else:
                    for index, source in enumerate(source_pack, start=1):
                        with ui.card().classes("ytis-card p-3 w-full").props(f"data-testid=source-pack-item-{index}"):
                            with ui.row().classes("w-full justify-between items-start gap-3"):
                                with ui.column().classes("gap-1 flex-1"):
                                    ui.label(f"{source.source_id} · {source.title}").classes("font-bold").props(
                                        f"data-testid=source-pack-title-{index}"
                                    )
                                    with ui.row().classes("gap-2"):
                                        ui.badge(source.source_type).props(f"outline data-testid=source-pack-type-{index}")
                                        ui.label(source.origin).classes("text-xs text-slate-500").props(
                                            f"data-testid=source-pack-origin-{index}"
                                        )
                                    ui.label(source.content).classes("text-sm text-slate-400 line-clamp-2")

                                with ui.row().classes("gap-1"):
                                    def move_up(*, source_id: str = source.source_id, position: int = index - 1) -> None:
                                        if position == 0:
                                            return
                                        source_pack[:] = move_source(tuple(source_pack), source_id=source_id, target_index=position - 1)
                                        render_source_pack()

                                    def move_down(*, source_id: str = source.source_id, position: int = index - 1) -> None:
                                        if position >= len(source_pack) - 1:
                                            return
                                        source_pack[:] = move_source(tuple(source_pack), source_id=source_id, target_index=position + 1)
                                        render_source_pack()

                                    def edit_current(*, selected: SourceDocument = source) -> None:
                                        begin_edit(selected)

                                    def remove_source(*, source_id: str = source.source_id) -> None:
                                        source_pack[:] = [item for item in source_pack if item.source_id != source_id]
                                        if editing_source_id["value"] == source_id:
                                            clear_draft()
                                        render_source_pack()

                                    ui.button(icon="arrow_upward", on_click=move_up).props(
                                        f"flat dense {'disable' if index == 1 else ''} data-testid=move-source-up-{index}"
                                    ).tooltip("Move up")
                                    ui.button(icon="arrow_downward", on_click=move_down).props(
                                        f"flat dense {'disable' if index == len(source_pack) else ''} data-testid=move-source-down-{index}"
                                    ).tooltip("Move down")
                                    ui.button(icon="edit", on_click=edit_current).props(
                                        f"flat dense data-testid=edit-source-{index}"
                                    ).tooltip("Edit source")
                                    ui.button(icon="delete", on_click=remove_source).props(
                                        f"flat dense color=negative data-testid=remove-source-{index}"
                                    ).tooltip("Remove source")
            render_duplicate_warnings()

        def draft_source(source_id: str) -> SourceDocument:
            return SourceDocument(
                source_id=source_id,
                title=str(source_title.value or ""),
                content=str(source_text.value or ""),
                source_type=str(source_type.value or "technical-note"),
                origin=str(source_origin.value or ""),
            )

        def save_source() -> None:
            try:
                selected_id = editing_source_id["value"]
                if selected_id is None:
                    source = draft_source(next_source_id())
                    source_pack.append(source)
                    message = f"Added {source.source_id}"
                else:
                    source_pack[:] = edit_source(
                        tuple(source_pack),
                        source_id=selected_id,
                        title=str(source_title.value or ""),
                        content=str(source_text.value or ""),
                        source_type=str(source_type.value or "technical-note"),
                        origin=str(source_origin.value or ""),
                    )
                    message = f"Updated {selected_id}"
                render_source_pack()
                clear_draft()
                ui.notify(message, type="positive")
            except Exception as exc:
                ui.notify(str(exc), type="negative")

        save_source_button.on_click(save_source)
        render_source_pack()

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
                f"{len(investigation.sources)} sources · {len(investigation.evidence)} evidence units · "
                f"{len(investigation.findings)} findings · {accepted} accepted · {rejected} rejected · {pending} pending"
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
                                    f"{evidence.evidence_id} · {evidence.source_id} · chars {evidence.start_offset}-{evidence.end_offset}"
                                ).classes("text-xs text-blue-300")
                                ui.label(evidence.text).classes("text-sm text-slate-300")

                        action_input = ui.input(
                            "Action for reusable insight card",
                            value="Preserve this accepted evidence in the next decision or implementation step.",
                        ).classes("w-full").props(f"data-testid=card-action-{index}")

                        def save_card(
                            *,
                            finding_id: str = finding.finding_id,
                            action_field: Any = action_input,
                        ) -> None:
                            active = current["value"]
                            if active is None:
                                ui.notify("Run or reopen an investigation first", type="warning")
                                return
                            try:
                                card = create_insight_card(
                                    active,
                                    finding_id=finding_id,
                                    action=str(action_field.value or ""),
                                )
                                path = card_repository.save(card)
                                ui.notify(f"Saved insight card {path.name}", type="positive")
                            except Exception as exc:
                                ui.notify(str(exc), type="negative")

                        ui.button("Save insight card", icon="bookmark_add", on_click=save_card).props(
                            f"outline data-testid=save-card-{index}"
                        )
            update_status()

        def analyze() -> None:
            try:
                sources = list(source_pack) or [draft_source("source-001")]
                current["value"] = active_service.create_investigation(
                    investigation_id=str(investigation_id.value or ""),
                    title=str(title.value or ""),
                    question=str(question.value or ""),
                    sources=sources,
                )
                render_findings()
                ui.notify("Evidence-linked findings created from source pack", type="positive")
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

        def export_reviewed_template() -> None:
            investigation = current["value"]
            if investigation is None:
                ui.notify("Run or reopen an investigation first", type="warning")
                return
            try:
                template = str(report_template.value or "").strip()
                if template not in REPORT_TEMPLATES:
                    raise ValueError("Choose a supported reviewed report template")
                output = reports_root / investigation.investigation_id / "reviewed"
                path = write_reviewed_report(investigation, template, output)
                ui.notify(f"Exported reviewed template {path.name}", type="positive")
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
                source_pack.clear()
                source_pack.extend(investigation.sources)
                render_source_pack()
                clear_draft()
                render_findings()
                ui.notify(f"Reopened {selected}", type="positive")
            except Exception as exc:
                ui.notify(str(exc), type="negative")

        with ui.card().classes("ytis-card p-4 w-full"):
            ui.label("3. Analyze and review").classes("text-xl font-bold")
            with ui.row().classes("gap-2 ytis-toolbar-row"):
                ui.button("Analyze source pack", icon="science", on_click=analyze, color="primary").props("data-testid=analyze-source")
                ui.button("Save investigation", icon="save", on_click=save).props("outline data-testid=save-investigation")
                ui.button("Export approved report", icon="download", on_click=export).props("outline data-testid=export-report")
            with ui.row().classes("w-full gap-2 items-end ytis-toolbar-row"):
                report_template = ui.select(
                    _REPORT_TEMPLATE_OPTIONS,
                    value="technical-lessons",
                    label="Reviewed report template",
                ).classes("min-w-[320px]").props("data-testid=report-template")
                ui.button(
                    "Export reviewed template",
                    icon="description",
                    on_click=export_reviewed_template,
                ).props("outline data-testid=export-reviewed-report")

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
