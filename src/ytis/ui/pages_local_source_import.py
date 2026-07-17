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

    with ui.column().classes("ytis-page gap-4"):
        ui.label("Local Source Import").classes("text-3xl font-bold")
        ui.label(
            "Import one local UTF-8 text or Markdown file through the hardened source boundary, analyze it deterministically, and save the investigation for reopening in the main workbench."
        ).classes("text-sm text-slate-400")

        with ui.card().classes("ytis-card p-4 w-full"):
            ui.label("File and source metadata").classes("text-xl font-bold")
            path_input = ui.input("Local file path").classes("w-full").props("data-testid=local-import-path")
            with ui.grid(columns=2).classes("w-full gap-3"):
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

        with ui.card().classes("ytis-card p-4 w-full"):
            ui.label("Investigation metadata").classes("text-xl font-bold")
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
                        ui.label(f"Saved {investigation.investigation_id}").classes("text-lg font-bold text-green-300")
                        ui.label(f"Source: {source.source_id} · {source.title}").classes("text-sm")
                        ui.label(f"Type: {source.source_type}").classes("text-sm")
                        ui.label(f"Origin: {source.origin}").classes("text-xs text-slate-400")
                        ui.label(
                            f"{len(investigation.evidence)} evidence units · {len(investigation.findings)} pending findings"
                        ).classes("text-sm text-slate-300")
                        ui.label(f"Saved to {saved_path}").classes("text-xs text-slate-500")
                        ui.link("Open Technical Research Workbench", "/technical-research").props(
                            "data-testid=open-technical-research"
                        )
                ui.notify("Local source imported and investigation saved", type="positive")
            except Exception as exc:
                ui.notify(str(exc), type="negative")

        ui.button("Import, analyze, and save", icon="upload_file", on_click=import_and_save, color="primary").props(
            "data-testid=run-local-import"
        )
        ui.label(
            "Supported files: .txt, .md, and .markdown. The importer rejects missing files, directories, unsupported extensions, invalid UTF-8, oversized files, path escapes, and direct symlinks."
        ).classes("text-xs text-slate-500")
        result.move()
