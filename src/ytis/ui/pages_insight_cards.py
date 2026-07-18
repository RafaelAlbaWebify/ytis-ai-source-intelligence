from __future__ import annotations

import os
from pathlib import Path

from nicegui import ui

from ytis.core.paths import project_root
from ytis.research import JsonInsightCardRepository, find_related_cards
from ytis.ui.layout import NAV_GROUPS, NAV_ITEMS, render_shell
from ytis.ui.state import AppState

_ROUTE = "/insight-cards"
_NAV_ITEM = ("Insight Cards", _ROUTE, "bookmarks")


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


def register_insight_cards_page(*, app_version: str) -> None:
    _register_navigation()
    state = AppState(app_version=app_version)

    @ui.page(_ROUTE)
    def insight_cards_page() -> None:
        render_insight_cards(state)


def render_insight_cards(state: AppState) -> None:
    render_shell(state, _ROUTE)
    repository = JsonInsightCardRepository(_storage_root() / "insight_cards")
    cards_container = ui.column().classes("w-full gap-0")
    relations_container = ui.column().classes("w-full gap-2")
    card_count = ui.label("0").classes("ytis-kpi-value")
    relation_count = ui.label("0").classes("ytis-kpi-value")
    evidence_count = ui.label("0").classes("ytis-kpi-value")

    with ui.column().classes("ytis-page gap-5"):
        with ui.element("section").classes("ytis-operational-header w-full"):
            with ui.column().classes("gap-1"):
                ui.label("Reusable evidence").classes("text-xs font-bold text-blue-400 uppercase tracking-wide")
                ui.label("Insight Card Library").classes("ytis-page-title")
                ui.label(
                    "Review persisted accepted-finding cards and exact advisory relationships without automatic merging or deletion."
                ).classes("text-sm text-slate-400")
            refresh_button = ui.button("Refresh", icon="refresh", color="primary").props(
                "no-caps data-testid=refresh-insight-cards"
            )

        with ui.element("section").classes("ytis-kpi-row"):
            with ui.element("article").classes("ytis-kpi-card"):
                ui.label("Persisted cards").classes("ytis-kpi-label")
                card_count.move()
                ui.label("Accepted findings only").classes("text-xs text-slate-500 mt-2")
            with ui.element("article").classes("ytis-kpi-card"):
                ui.label("Relationships").classes("ytis-kpi-label")
                relation_count.move()
                ui.label("Exact advisory matches").classes("text-xs text-slate-500 mt-2")
            with ui.element("article").classes("ytis-kpi-card"):
                ui.label("Evidence links").classes("ytis-kpi-label")
                evidence_count.move()
                ui.label("Source-qualified references").classes("text-xs text-slate-500 mt-2")
            with ui.element("article").classes("ytis-kpi-card"):
                ui.label("Automation").classes("ytis-kpi-label")
                ui.label("None").classes("ytis-kpi-value")
                ui.label("No automatic merge or delete").classes("text-xs text-slate-500 mt-2")

        with ui.card().classes("ytis-card p-0 w-full"):
            with ui.row().classes("w-full justify-between items-start px-5 pt-5 pb-3"):
                with ui.column().classes("gap-1"):
                    ui.label("Persisted card register").classes("text-lg font-bold")
                    ui.label("Each row retains the originating investigation, finding and exact evidence IDs.").classes(
                        "text-sm text-slate-400"
                    )
                ui.badge("Accepted only", color="green").props("outline")
            ui.separator()
            with ui.column().classes("w-full px-5 pb-2 gap-0"):
                cards_container.move()

        with ui.card().classes("ytis-card p-0 w-full"):
            with ui.row().classes("w-full justify-between items-start px-5 pt-5 pb-3"):
                with ui.column().classes("gap-1"):
                    ui.label("Advisory relationships").classes("text-lg font-bold")
                    ui.label(
                        "Relationships use exact normalized claims or shared evidence IDs only; they do not claim semantic similarity."
                    ).classes("text-sm text-slate-400")
                ui.badge("Non-destructive", color="orange").props("outline")
            ui.separator()
            with ui.column().classes("w-full p-5 gap-2"):
                relations_container.move()

        def refresh() -> None:
            cards_container.clear()
            relations_container.clear()
            try:
                cards = repository.list_cards()
                relations = find_related_cards(cards)
            except Exception as exc:
                with cards_container:
                    ui.label(str(exc)).classes("text-red-300 py-4").props("data-testid=insight-card-error")
                return

            card_count.set_text(str(len(cards)))
            relation_count.set_text(str(len(relations)))
            evidence_count.set_text(str(sum(len(card.evidence_ids) for card in cards)))

            with cards_container:
                if not cards:
                    ui.label("No persisted insight cards.").classes("text-sm text-slate-500 py-5").props(
                        "data-testid=insight-cards-empty"
                    )
                for index, card in enumerate(cards, start=1):
                    with ui.row().classes("w-full items-start gap-4 py-4").style(
                        "border-bottom: 1px solid var(--ytis-border)"
                    ).props(f"data-testid=insight-card-{index}"):
                        ui.icon("bookmark").classes("text-xl text-blue-400")
                        with ui.column().classes("gap-1 flex-1 min-w-0"):
                            with ui.row().classes("w-full justify-between items-start gap-3"):
                                ui.label(card.claim).classes("font-bold")
                                ui.badge(f"{card.confidence:.2f}", color="green").props("outline")
                            ui.label(f"Action: {card.action}").classes("text-sm text-slate-300")
                            ui.label(
                                f"{card.card_id} · investigation {card.investigation_id} · finding {card.finding_id}"
                            ).classes("text-xs text-slate-500")
                            ui.label(f"Evidence: {', '.join(card.evidence_ids)}").classes("text-xs text-blue-300")

            with relations_container:
                if not relations:
                    ui.label("No exact card relationships detected.").classes("text-sm text-slate-500").props(
                        "data-testid=related-cards-empty"
                    )
                for index, relation in enumerate(relations, start=1):
                    with ui.card().classes("ytis-mini-card p-3 w-full").style(
                        "border-left: 4px solid var(--ytis-amber-700) !important"
                    ).props(f"data-testid=related-card-{index}"):
                        ui.label(" ↔ ".join(relation.card_ids)).classes("font-bold text-amber-300")
                        ui.label(f"Reasons: {', '.join(relation.reasons)}").classes("text-sm text-slate-300")
                        if relation.shared_evidence_ids:
                            ui.label(f"Shared evidence: {', '.join(relation.shared_evidence_ids)}").classes(
                                "text-xs text-blue-300"
                            )

        refresh_button.on_click(refresh)
        refresh()
