from __future__ import annotations

import os
from pathlib import Path

from nicegui import ui

from ytis.core.paths import project_root
from ytis.research import JsonInvestigationRepository, TechnicalResearchService, import_local_source
from ytis.ui.layout import NAV_GROUPS, NAV_ITEMS, render_shell
from ytis.ui.state import AppState

_ROUTE = "/local-source-import"
_NAV_ITEM = ("Local Source Import", _ROUTE, "upload_file")
_SOURCE_TYPE_OPTIONS = {
    "technical-note": "Technical note",
    "pasted-text": "Pasted text",
    "article-notes": "Article notes",
    "document-notes": "Document notes",
    "job-description": "Job description",
    "transcript": "Transcript",
    "text": "Generic text",
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
            items.append(_NAV_ITEM)
            break
    else:
        NAV_GROUPS.append(("Evidence", [_NAV_ITEM]))
    NAV_ITEMS.append(_NAV_ITEM)


def register_local_source_import_page(*, app_version: str) -> None:
    _register_navigation()
    state = AppState(app_version=app_version)

    @ui.page(_ROUTE)
    def local_source_import_page() -> None:
        render_local_source_import(state)


def render_local_source_import(state: AppState) -> None:
    render_shell(state, _ROUTE)
    root = _storage_root()
    repository = JsonInvestigationRepository(root / "investigations")
    service = TechnicalResearchService()

    with ui.column().classes("ytis-page gap-5"):
        with ui.element("section").classes("ytis-operational-header w-full"):
            with ui.column().classes("gap-1"):
                ui.label("Source ingestion").classes("text-xs font-bold text-blue-400 uppercase tracking-wide")
                ui.label("Local Source Import").classes("ytis-page-title")
                ui.label(
                    "Validate one local UTF-8 text or Markdown file, generate grounded findings, and save a reopenable investigation."
                ).classes("text-sm text-slate-400")
            ui.button(
                "Open research workbench",
                icon="science",
                on_click=lambda: ui.navigate.to("/technical-research"),
            ).props("outline no-caps")

        with ui.element("section").classes("ytis-kpi-row"):
            for label, value, detail in (
                ("Supported formats", "3", ".txt · .md · .markdown"),
                ("Encoding", "UTF-8", "Invalid text is rejected"),
                ("Execution", "Local", "No network source fetching"),
                ("Review state", "Pending", "No automatic acceptance"),
            ):
                with ui.element("article").classes("ytis-kpi-card"):
                    ui.label(label).classes("ytis-kpi-label")
                    ui.label(value).classes("ytis-kpi-value")
                    ui.label(detail).classes("text-xs text-slate-500 mt-2")

        with ui.card().classes("ytis-card p-0 w-full"):
            with ui.row().classes("w-full justify-between items-start px-5 pt-5 pb-3"):
                with ui.column().classes("gap-1"):
                    ui.label("Import configuration").classes("text-lg font-bold")
                    ui.label("File identity and investigation metadata remain explicit and reviewable.").classes(
                        "text-sm text-slate-400"
                    )
                ui.badge("Local-only", color="green").props("outline")
            ui.separator()
            with ui.column().classes("w-full gap-4 p-5"):
                path_input = ui.input("Local file path").classes("w-full").props("data-testid=local-import-path")
                with ui.grid(columns=3).classes("w-full gap-3"):
                    source_id = ui.input("Source ID", value="source-001").classes("w-full").props(
                        "data-testid=local-import-source-id"
                    )
                    source_type = ui.select(
                        _SOURCE_TYPE_OPTIONS,
                        value="document-notes",
                        label="Source type",
                    ).classes("w-full").props("data-testid=local-import-source-type")
                    source_title = ui.input("Source title (optional)").classes("w-full").props(
                        "data-testid=local-import-source-title"
                    )
                ui.separator()
                with ui.grid(columns=2).classes("w-full gap-3"):
                    investigation_id = ui.input("Investigation ID", value="local-import-001").classes("w-full").props(
                        "data-testid=local-import-investigation-id"
                    )
                    investigation_title = ui.input("Investigation title", value="Imported local source").classes(
                        "w-full"
                    ).props("data-testid=local-import-investigation-title")
                question = ui.input(
                    "Research question",
                    value="What capabilities, constraints, risks, and recommendations are stated?",
                ).classes("w-full").props("data-testid=local-import-question")

        result = ui.column().classes("w-full gap-2")

        def import_and_save() -> None:
            try:
                source = import_local_source(
                    Path(str(path_input.value or "")).expanduser(),
                    source_id=str(source_id.value or ""),
                    source_type=str(source_type.value or "document-notes"),
                    title=str(source_title.value or "") or None,
                )
                investigation = service.create_investigation(
                    investigation_id=str(investigation_id.value or ""),
                    title=str(investigation_title.value or ""),
                    question=str(question.value or ""),
                    sources=[source],
                )
                saved_path = repository.save(investigation)
                result.clear()
                with result:
                    with ui.card().classes("ytis-card p-4 w-full").props("data-testid=local-import-result"):
                        with ui.row().classes("w-full justify-between items-start"):
                            with ui.column().classes("gap-1"):
                                ui.label(f"Saved {investigation.investigation_id}").classes("text-lg font-bold text-green-300")
                                ui.label(f"{source.source_id} · {source.title}").classes("text-sm")
                            ui.badge("Pending review", color="orange").props("outline")
                        ui.separator()
                        with ui.grid(columns=3).classes("w-full gap-3"):
                            ui.label(f"Type: {source.source_type}").classes("text-sm")
                            ui.label(f"Evidence: {len(investigation.evidence)}").classes("text-sm")
                            ui.label(f"Findings: {len(investigation.findings)}").classes("text-sm")
                        ui.label(f"Origin: {source.origin}").classes("text-xs text-slate-400")
                        ui.label(f"Saved to {saved_path}").classes("text-xs text-slate-500")
                        ui.link("Open Technical Research Workbench", "/technical-research").props(
                            "data-testid=open-technical-research"
                        )
                ui.notify("Local source imported and investigation saved", type="positive")
            except Exception as exc:
                ui.notify(str(exc), type="negative")

        with ui.row().classes("w-full justify-between items-center gap-3"):
            ui.label(
                "The importer rejects missing files, directories, unsupported extensions, invalid UTF-8, oversized files, path escapes, and direct symlinks."
            ).classes("text-xs text-slate-500 max-w-3xl")
            ui.button("Import, analyze, and save", icon="upload_file", on_click=import_and_save, color="primary").props(
                "no-caps data-testid=run-local-import"
            )
        result.move()
