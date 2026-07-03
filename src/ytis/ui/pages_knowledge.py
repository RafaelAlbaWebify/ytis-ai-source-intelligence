from __future__ import annotations

from pathlib import Path
import traceback

from nicegui import ui

from ytis.core.analysis_inbox import list_analyses, read_analysis
from ytis.core.knowledge_cards import (
    CARD_STATUS,
    CARD_TYPES,
    build_card_content_from_analysis,
    card_stats,
    create_template_cards,
    export_cards_zip,
    filter_cards,
    get_template_by_title,
    list_cards,
    read_card,
    save_card,
    template_titles,
    update_card_status,
    upgrade_template_cards,
)
from ytis.ui.components import open_path
from ytis.ui.context import current_mission_data, current_mission_id
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState


def _project_root(state: AppState) -> Path:
    return Path(getattr(state, "project_root_path", None) or getattr(state, "project_root", "") or Path.cwd())


def _downloads_dir(state: AppState) -> Path:
    value = getattr(state, "downloads_dir", None)
    return Path(value) if value else Path.home() / "Downloads"


def _metric(title: str, value: str, caption: str = "") -> None:
    with ui.card().classes("ytis-metric p-4"):
        ui.label(title).classes("text-sm text-slate-400")
        ui.label(value).classes("text-2xl font-bold")
        if caption:
            ui.label(caption).classes("text-xs text-slate-500")


def _analysis_options(records, include_none: bool = True) -> dict[str, str]:
    options = {"No source analysis": ""} if include_none else {}
    for record in records:
        label = f"{record.title} | {record.created_at}"
        options[label] = record.record_id
    return options


def _records_for_current_mission(state: AppState, records) -> list:
    mission_id = current_mission_id(state)
    mission = current_mission_data(state)
    mission_name = str(mission.get("name") or "").strip()
    if mission_id:
        matches = [record for record in records if record.mission_id == mission_id]
        if matches:
            return matches
    if mission_name:
        matches = [record for record in records if record.mission_name == mission_name]
        if matches:
            return matches
    return []


def _default_analysis_label(options: dict[str, str]) -> str:
    for label, record_id in options.items():
        if record_id:
            return label
    return "No source analysis"


def _find_analysis_by_id(records, record_id: str):
    for record in records:
        if record.record_id == record_id:
            return record
    return None


def _render_knowledge_body(state: AppState) -> None:
    project_root = _project_root(state)
    downloads_dir = _downloads_dir(state)

    cards = list_cards(project_root)
    analyses = list_analyses(project_root)
    current_mission = current_mission_data(state)
    current_mission_records = _records_for_current_mission(state, analyses)
    mission_source_records = current_mission_records or analyses
    mission_id = str(current_mission.get("mission_id") or "")
    mission_name = str(current_mission.get("name") or "")
    mission_projects = current_mission.get("projects") or []
    if isinstance(mission_projects, str):
        mission_projects = [mission_projects]
    stats = card_stats(cards)

    with ui.column().classes("ytis-page gap-3"):
        with ui.row().classes("w-full justify-between items-center ytis-toolbar-row gap-3"):
            with ui.column().classes("gap-0"):
                ui.label("Knowledge Cards").classes("text-3xl font-bold")
                ui.label("Reusable service ideas, workflows, warnings, validation tasks, scripts, and evidence notes").classes("text-sm text-slate-400")
            with ui.row().classes("gap-2 flex-wrap"):
                ui.button("Dashboard", icon="dashboard", on_click=lambda: ui.navigate.to("/")).props("outline")
                ui.button("Analysis Library", icon="move_to_inbox", on_click=lambda: ui.navigate.to("/analysis-library")).props("outline")
                ui.button("Export Cards", icon="archive", on_click=lambda: open_path(export_cards_zip(list_cards(project_root), downloads_dir)), color="primary")

        with ui.grid().classes("ytis-grid-5"):
            _metric("Cards", str(stats["cards"]), "total")
            _metric("Types", str(stats["types"]), "card categories")
            _metric("Tags", str(stats["tags"]), "reuse labels")
            _metric("Draft", str(stats["draft"]), "needs cleanup")
            _metric("Validate", str(stats["validate"]), "needs test")
            _metric("Use", str(stats["use"]), "ready")

        refresh_ref = {"fn": None}

        with ui.expansion("Create Knowledge Card", icon="add_circle", value=True).classes("ytis-card w-full text-white").props("dense expand-separator"):
            with ui.column().classes("p-4 gap-3"):
                with ui.grid(columns=4).classes("w-full gap-3"):
                    title_input = ui.input("Title", value="Lost Lead Recovery Audit").classes("w-full")
                    type_select = ui.select(CARD_TYPES, value="Service idea", label="Type").classes("w-full")
                    status_select = ui.select(CARD_STATUS, value="Draft", label="Status").classes("w-full")
                    tags_input = ui.input("Tags", value="Webify, offer, validation").classes("w-full")
                source_options = _analysis_options(mission_source_records)
                source_labels = list(source_options.keys())
                source_select = ui.select(options=source_labels, value=_default_analysis_label(source_options), label="Source analysis").classes("w-full")
                content_box = ui.textarea(
                    "Card content",
                    value=(
                        "Purpose:\n\n"
                        "When to use:\n\n"
                        "Target business:\n\n"
                        "Evidence/source:\n\n"
                        "Operational checklist:\n\n"
                        "Boundaries / what not to promise:\n\n"
                        "Deliverable:\n\n"
                        "Validation or pricing hypothesis:\n\n"
                        "Next action:\n"
                    ),
                ).classes("w-full").props("rows=10")
                status_label = ui.label("Ready").classes("text-xs text-slate-400")

                def selected_analysis():
                    selected_label = source_select.value or "No source analysis"
                    selected_id = source_options.get(selected_label, "")
                    for record in analyses:
                        if record.record_id == selected_id:
                            return record
                    return None

                def prefill_from_analysis() -> None:
                    record = selected_analysis()
                    if not record:
                        ui.notify("Select a source analysis first", type="warning")
                        return
                    title_input.value = record.title
                    tags_input.value = ", ".join([v for v in [record.focus_preset, record.topic, record.mission_name] if v]).strip(", ")
                    content_box.value = (
                        "## Purpose\n"
                        "Capture a reusable point from this analysis.\n\n"
                        "## Source context\n"
                        f"Source analysis: {record.title}\n\n"
                        f"Mission: {record.mission_name or '-'}\n"
                        f"Topic: {record.topic or '-'}\n"
                        f"Focus: {record.focus_preset or '-'}\n\n"
                        "## Evidence / summary\n"
                        f"{record.summary}\n\n"
                        "## Reusable point\n\n"
                        "## Boundaries / uncertainty\n\n"
                        "## Next action\n"
                    )
                    title_input.update()
                    tags_input.update()
                    content_box.update()
                    ui.notify("Card prefilled from analysis", type="positive")

                template_select = ui.select(template_titles(), value="Lost Lead Recovery Audit", label="Quick Webify template").classes("w-full")

                def selected_template():
                    template = get_template_by_title(template_select.value or "")
                    if not template:
                        ui.notify("Select a template first", type="warning")
                    return template

                def load_template_into_editor() -> None:
                    template = selected_template()
                    if not template:
                        return
                    title_input.value = template.title
                    type_select.value = template.card_type
                    status_select.value = template.status
                    tags_input.value = ", ".join(template.tags)
                    content_box.value = template.content
                    for element in [title_input, type_select, status_select, tags_input, content_box]:
                        element.update()
                    ui.notify("Template loaded into editor", type="positive")

                def create_selected_template() -> None:
                    template = selected_template()
                    if not template:
                        return
                    record = selected_analysis()
                    created, skipped = create_template_cards(
                        project_root=project_root,
                        templates=[template],
                        mission_id=mission_id,
                        mission_name=mission_name,
                        source_analysis_id=record.record_id if record else "",
                        source_analysis_title=record.title if record else "",
                    )
                    if created:
                        ui.notify("Template card created", type="positive")
                    else:
                        ui.notify("Template already exists: " + ", ".join(skipped), type="warning")
                    if refresh_ref["fn"]:
                        refresh_ref["fn"]()

                def create_webify_starter_set() -> None:
                    record = selected_analysis()
                    created, skipped = create_template_cards(
                        project_root=project_root,
                        mission_id=mission_id,
                        mission_name=mission_name,
                        source_analysis_id=record.record_id if record else "",
                        source_analysis_title=record.title if record else "",
                    )
                    message = f"Created {len(created)} Webify card(s)"
                    if skipped:
                        message += f"; skipped {len(skipped)} existing"
                    ui.notify(message, type="positive" if created else "warning")
                    if refresh_ref["fn"]:
                        refresh_ref["fn"]()

                def upgrade_existing_webify_cards() -> None:
                    record = selected_analysis()
                    upgraded, missing = upgrade_template_cards(
                        project_root=project_root,
                        mission_id=mission_id,
                        mission_name=mission_name,
                        source_analysis_id=record.record_id if record else "",
                        source_analysis_title=record.title if record else "",
                    )
                    message = f"Upgraded {len(upgraded)} Webify card(s)"
                    if missing:
                        message += f"; {len(missing)} not found"
                    ui.notify(message, type="positive" if upgraded else "warning")
                    if refresh_ref["fn"]:
                        refresh_ref["fn"]()

                def create_card_from_selected_analysis() -> None:
                    record = selected_analysis()
                    if not record:
                        ui.notify("Select a source analysis first", type="warning")
                        return
                    analysis_text = read_analysis(record)
                    card = save_card(
                        project_root=project_root,
                        title=f"Reusable card from {record.title}",
                        card_type="Evidence note",
                        content=build_card_content_from_analysis(record, analysis_text),
                        tags=["Webify", "mission answer", record.topic, record.focus_preset],
                        status="Review",
                        mission_id=record.mission_id,
                        mission_name=record.mission_name,
                        source_analysis_id=record.record_id,
                        source_analysis_title=record.title,
                    )
                    ui.notify("Analysis card created", type="positive")
                    status_label.text = f"Created: {card.card_id}"
                    status_label.update()
                    if refresh_ref["fn"]:
                        refresh_ref["fn"]()

                with ui.card().classes("ytis-mini-card p-3 w-full"):
                    ui.label("Current mission extraction workflow").classes("font-bold")
                    if mission_name:
                        ui.label(f"Mission: {mission_name} | Projects: {', '.join(mission_projects) if mission_projects else '-'} | Source answers: {len(current_mission_records)}").classes("text-xs text-slate-400")
                    ui.label("Use this after a mission is complete: create reusable cards, then mark each card Validate or Use.").classes("text-sm text-slate-300")
                    with ui.row().classes("gap-2 flex-wrap"):
                        ui.button("Create Suggested Webify Cards", icon="auto_awesome", on_click=create_webify_starter_set, color="primary")
                        ui.button("Upgrade Existing Webify Cards", icon="upgrade", on_click=upgrade_existing_webify_cards).props("outline")
                        ui.button("Create Card From Source Answer", icon="note_add", on_click=create_card_from_selected_analysis).props("outline")
                        ui.button("Load Template Into Editor", icon="edit_note", on_click=load_template_into_editor).props("outline")
                        ui.button("Create Selected Template", icon="add_card", on_click=create_selected_template).props("outline")

                def do_create() -> None:
                    record = selected_analysis()
                    card = save_card(
                        project_root=project_root,
                        title=title_input.value or "Untitled card",
                        card_type=type_select.value or "Other",
                        content=content_box.value or "",
                        tags=tags_input.value or "",
                        status=status_select.value or "Draft",
                        mission_id=record.mission_id if record else "",
                        mission_name=record.mission_name if record else "",
                        source_analysis_id=record.record_id if record else "",
                        source_analysis_title=record.title if record else "",
                    )
                    status_label.text = f"Created: {card.card_id}"
                    status_label.classes(remove="text-slate-400")
                    status_label.classes(add="text-green-400")
                    status_label.update()
                    ui.notify("Knowledge card created", type="positive")
                    if refresh_ref["fn"]:
                        refresh_ref["fn"]()

                with ui.row().classes("gap-2 flex-wrap"):
                    ui.button("Prefill from Analysis", icon="auto_fix_high", on_click=prefill_from_analysis).props("outline")
                    ui.button("Create Card", icon="save", on_click=do_create, color="primary")
                    ui.button("Open Cards Folder", icon="folder_open", on_click=lambda: open_path(project_root / "knowledge_cards")).props("outline")

        with ui.card().classes("ytis-card p-4 w-full"):
            with ui.row().classes("w-full justify-between items-end gap-3 ytis-card-row"):
                ui.label("Card Library").classes("text-xl font-bold")
                type_filter = ui.select(["All types"] + CARD_TYPES, value="All types", label="Type").classes("w-52 min-w-[180px]")
                status_filter = ui.select(["All status"] + CARD_STATUS, value="All status", label="Status").classes("w-52 min-w-[180px]")
                text_filter = ui.input("Search cards").classes("flex-1 min-w-[220px]")

            table_holder = ui.column().classes("w-full gap-2 mt-3")

            def refresh_table() -> None:
                table_holder.clear()
                current_cards = filter_cards(
                    list_cards(project_root),
                    card_type=type_filter.value or "All types",
                    status=status_filter.value or "All status",
                    text=text_filter.value or "",
                )
                rows = [
                    {
                        "title": card.title,
                        "type": card.card_type,
                        "status": card.status,
                        "tags": ", ".join(card.tags),
                        "mission": card.mission_name,
                        "source": card.source_analysis_title,
                        "created": card.created_at,
                        "summary": card.summary,
                        "card_id": card.card_id,
                    }
                    for card in current_cards
                ]
                with table_holder:
                    if not rows:
                        ui.label("No cards match the current filters.").classes("text-slate-400")
                        return
                    columns = [
                        {"name": "title", "label": "Title", "field": "title", "align": "left", "sortable": True},
                        {"name": "type", "label": "Type", "field": "type", "sortable": True},
                        {"name": "status", "label": "Status", "field": "status", "sortable": True},
                        {"name": "tags", "label": "Tags", "field": "tags", "align": "left"},
                        {"name": "mission", "label": "Mission", "field": "mission", "align": "left"},
                        {"name": "created", "label": "Created", "field": "created", "sortable": True},
                    ]
                    table = ui.table(columns=columns, rows=rows, row_key="card_id", selection="single").classes("w-full")
                    table.props("flat bordered dark dense")

                    def selected_card():
                        if not table.selected:
                            ui.notify("Select a card first", type="warning")
                            return None
                        selected_id = table.selected[0].get("card_id")
                        for card in list_cards(project_root):
                            if card.card_id == selected_id:
                                return card
                        ui.notify("Selected card not found", type="warning")
                        return None

                    def open_selected_card() -> None:
                        card = selected_card()
                        if card:
                            open_path(card.card_path)

                    def open_selected_folder() -> None:
                        card = selected_card()
                        if card:
                            open_path(card.folder)

                    def show_selected_card() -> None:
                        card = selected_card()
                        if not card:
                            return
                        with ui.dialog() as dialog, ui.card().classes("bg-slate-900 text-white").style("width: 900px; max-width: 95vw;"):
                            ui.label(card.title).classes("text-xl font-bold")
                            ui.label(f"{card.card_type} | {card.status} | {', '.join(card.tags) if card.tags else '-'}").classes("text-sm text-slate-400")
                            box = ui.textarea(value=read_card(card)).classes("w-full").props("rows=24")
                            box.style("font-family: Consolas, monospace; font-size: 12px;")
                            with ui.row().classes("justify-end w-full"):
                                ui.button("Close", on_click=dialog.close).props("outline")
                                ui.button("Open File", icon="article", on_click=lambda: open_path(card.card_path), color="primary")
                        dialog.open()

                    def set_status(status: str) -> None:
                        card = selected_card()
                        if card:
                            update_card_status(card, status)
                            ui.notify(f"Status updated: {status}", type="positive")
                            refresh_table()

                    with ui.row().classes("gap-2 flex-wrap"):
                        ui.button("View Card", icon="visibility", on_click=show_selected_card).props("outline")
                        ui.button("Open File", icon="article", on_click=open_selected_card).props("outline")
                        ui.button("Open Folder", icon="folder", on_click=open_selected_folder).props("outline")
                        ui.button("Mark Validate", icon="science", on_click=lambda: set_status("Validate")).props("outline")
                        ui.button("Mark Use", icon="check_circle", on_click=lambda: set_status("Use")).props("outline")
                        ui.button("Archive", icon="archive", on_click=lambda: set_status("Archived")).props("outline")

            refresh_ref["fn"] = refresh_table
            type_filter.on("update:model-value", lambda e: refresh_table())
            status_filter.on("update:model-value", lambda e: refresh_table())
            text_filter.on("update:model-value", lambda e: refresh_table())
            refresh_table()



def _render_knowledge_error(exc: Exception) -> None:
    with ui.column().classes("ytis-page gap-3"):
        ui.label("Knowledge Cards safe mode").classes("text-3xl font-bold")
        ui.label("The Knowledge Cards page failed to render, but YTIS is still usable.").classes("text-orange-300")
        with ui.row().classes("gap-2"):
            ui.button("Dashboard", icon="dashboard", on_click=lambda: ui.navigate.to("/"), color="primary")
            ui.button("Analysis Library", icon="move_to_inbox", on_click=lambda: ui.navigate.to("/analysis-library")).props("outline")
            ui.button("Library", icon="folder", on_click=lambda: ui.navigate.to("/library")).props("outline")
        ui.label("Error").classes("text-xl font-bold")
        ui.code(str(exc)).classes("w-full")
        ui.label("Traceback").classes("text-xl font-bold")
        ui.code(traceback.format_exc()).classes("w-full")


def render_knowledge(state: AppState) -> None:
    render_shell(state, "/knowledge")
    try:
        _render_knowledge_body(state)
    except Exception as exc:
        _render_knowledge_error(exc)
