from __future__ import annotations

from nicegui import ui

from ytis.ui.layout import NAV_GROUPS, NAV_ITEMS, render_shell
from ytis.ui.state import AppState

_ROUTE = "/start"
_NAV_ITEM = ("Start Here", _ROUTE, "rocket_launch")


def _register_navigation() -> None:
    if _NAV_ITEM in NAV_ITEMS:
        return
    for group_name, items in NAV_GROUPS:
        if group_name == "Cockpit":
            items.insert(0, _NAV_ITEM)
            break
    else:
        NAV_GROUPS.insert(0, ("Cockpit", [_NAV_ITEM]))
    NAV_ITEMS.insert(0, _NAV_ITEM)


def register_start_here_page(*, app_version: str) -> None:
    _register_navigation()
    state = AppState(app_version=app_version)

    @ui.page(_ROUTE)
    def start_here_page() -> None:
        render_shell(state, _ROUTE)
        with ui.column().classes("ytis-page gap-4"):
            ui.label("Start Here").classes("text-3xl font-bold")
            ui.label(
                "Choose the smallest YTIS path that matches what you need. The older specialist routes remain available in the sidebar."
            ).classes("text-sm text-slate-400")

            with ui.grid(columns=2).classes("w-full gap-4"):
                with ui.card().classes("ytis-card p-5 w-full"):
                    ui.badge("Fastest overview", color="blue").props("outline")
                    ui.label("Run the public-safe demo").classes("text-xl font-bold")
                    ui.label(
                        "See source → evidence → finding provenance without uploads, credentials, persistence, or provider setup."
                    ).classes("text-sm text-slate-400")
                    ui.button("Open demo", icon="play_arrow", on_click=lambda: ui.navigate.to("/demo")).props(
                        "data-testid=start-demo"
                    )

                with ui.card().classes("ytis-card p-5 w-full"):
                    ui.badge("Local file", color="green").props("outline")
                    ui.label("Import a text or Markdown source").classes("text-xl font-bold")
                    ui.label(
                        "Validate a local UTF-8 file, create an evidence-linked investigation, and save it for review."
                    ).classes("text-sm text-slate-400")
                    ui.button(
                        "Import local source",
                        icon="upload_file",
                        on_click=lambda: ui.navigate.to("/local-source-import"),
                    ).props("data-testid=start-import")

                with ui.card().classes("ytis-card p-5 w-full"):
                    ui.badge("Complete workflow", color="purple").props("outline")
                    ui.label("Open the research workbench").classes("text-xl font-bold")
                    ui.label(
                        "Build multi-source packs, review grounded findings, save cards, and export reviewed reports."
                    ).classes("text-sm text-slate-400")
                    ui.button(
                        "Open workbench",
                        icon="science",
                        on_click=lambda: ui.navigate.to("/technical-research"),
                    ).props("data-testid=start-workbench")

                with ui.card().classes("ytis-card p-5 w-full"):
                    ui.badge("Reusable outputs", color="orange").props("outline")
                    ui.label("Review saved insight cards").classes("text-xl font-bold")
                    ui.label(
                        "Inspect accepted evidence, explicit actions, and advisory exact-card relationships."
                    ).classes("text-sm text-slate-400")
                    ui.button(
                        "Open card library",
                        icon="bookmarks",
                        on_click=lambda: ui.navigate.to("/insight-cards"),
                    ).props("data-testid=start-cards")

            with ui.card().classes("ytis-card p-4 w-full"):
                ui.label("Human-review boundary").classes("font-bold")
                ui.label(
                    "YTIS never accepts findings automatically. Reusable cards and reviewed reports require accepted, grounded findings."
                ).classes("text-sm text-slate-300").props("data-testid=start-review-boundary")
