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
    cards_container = ui.column().classes("w-full gap-3")
    relations_container = ui.column().classes("w-full gap-3")

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-start gap-3"):
            with ui.column().classes("gap-0"):
                ui.label("Insight Card Library").classes("text-3xl font-bold")
                ui.label(
                    "Review persisted accepted-finding cards and advisory relationships without automatic merging or deletion."
                ).classes("text-sm text-slate-400")
            refresh_button = ui.button("Refresh", icon="refresh").props("data-testid=refresh-insight-cards")

        with ui.card().classes("ytis-card p-4 w-full"):
            ui.label("Persisted cards").classes("text-xl font-bold")
            cards_container.move()

        with ui.card().classes("ytis-card p-4 w-full"):
            ui.label("Advisory relationships").classes("text-xl font-bold")
            ui.label(
                "Relationships use exact normalized claims or shared evidence IDs only. YTIS does not merge, delete, replace, or claim semantic similarity."
            ).classes("text-sm text-slate-400")
            relations_container.move()

        def refresh() -> None:
            cards_container.clear()
            relations_container.clear()
            try:
                cards = repository.list_cards()
                relations = find_related_cards(cards)
            except Exception as exc:
                with cards_container:
                    ui.label(str(exc)).classes("text-red-300").props("data-testid=insight-card-error")
                return

            with cards_container:
                if not cards:
                    ui.label("No persisted insight cards.").classes("text-sm text-slate-500").props(
                        "data-testid=insight-cards-empty"
                    )
                for index, card in enumerate(cards, start=1):
                    with ui.card().classes("ytis-mini-card p-3 w-full").props(f"data-testid=insight-card-{index}"):
                        ui.label(card.claim).classes("font-bold")
                        ui.label(f"Action: {card.action}").classes("text-sm text-slate-300")
                        ui.label(
                            f"Card {card.card_id} · investigation {card.investigation_id} · finding {card.finding_id}"
                        ).classes("text-xs text-slate-500")
                        ui.label(
                            f"Confidence {card.confidence:.2f} · evidence {', '.join(card.evidence_ids)}"
                        ).classes("text-xs text-blue-300")

            with relations_container:
                if not relations:
                    ui.label("No exact card relationships detected.").classes("text-sm text-slate-500").props(
                        "data-testid=related-cards-empty"
                    )
                for index, relation in enumerate(relations, start=1):
                    with ui.card().classes("ytis-mini-card p-3 w-full border-amber-500/40").props(
                        f"data-testid=related-card-{index}"
                    ):
                        ui.label(" ↔ ".join(relation.card_ids)).classes("font-bold text-amber-300")
                        ui.label(f"Reasons: {', '.join(relation.reasons)}").classes("text-sm text-slate-300")
                        if relation.shared_evidence_ids:
                            ui.label(
                                f"Shared evidence: {', '.join(relation.shared_evidence_ids)}"
                            ).classes("text-xs text-blue-300")

        refresh_button.on_click(refresh)
        refresh()
