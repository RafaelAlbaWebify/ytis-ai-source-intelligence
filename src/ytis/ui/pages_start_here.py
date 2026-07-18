from __future__ import annotations

from nicegui import ui

from ytis.ui.layout import NAV_GROUPS, NAV_ITEMS, render_shell
from ytis.ui.state import AppState
from ytis.ui.trace_visual_system import install_trace_visual_system

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


def _kpi(label: str, value: str, detail: str) -> None:
    with ui.element("article").classes("ytis-kpi-card"):
        ui.label(label).classes("ytis-kpi-label")
        ui.label(value).classes("ytis-kpi-value")
        ui.label(detail).classes("text-xs text-slate-500 mt-2")


def _entry_row(
    *,
    icon: str,
    title: str,
    description: str,
    action: str,
    route: str,
    test_id: str,
    status: str,
) -> None:
    with ui.row().classes("w-full items-center gap-4 py-3").style("border-bottom: 1px solid var(--ytis-border)"):
        ui.icon(icon).classes("text-xl text-blue-400")
        with ui.column().classes("gap-0 flex-1 min-w-0"):
            with ui.row().classes("items-center gap-2"):
                ui.label(title).classes("font-bold")
                ui.badge(status, color="blue").props("outline")
            ui.label(description).classes("text-sm text-slate-400")
        ui.button(action, icon="arrow_forward", on_click=lambda: ui.navigate.to(route)).props(
            f"outline no-caps data-testid={test_id}"
        )


def register_start_here_page(*, app_version: str) -> None:
    install_trace_visual_system()
    _register_navigation()
    state = AppState(app_version=app_version)

    @ui.page(_ROUTE)
    def start_here_page() -> None:
        render_shell(state, _ROUTE)
        with ui.column().classes("ytis-page gap-5"):
            with ui.element("section").classes("ytis-operational-header w-full"):
                with ui.column().classes("gap-1"):
                    ui.label("YTIS operational workspace").classes("text-xs font-bold text-blue-400 uppercase tracking-wide")
                    ui.label("Start Here").classes("ytis-page-title")
                    ui.label(
                        "Choose the smallest evidence-led workflow that matches the task. All outputs remain local and subject to human review."
                    ).classes("text-sm text-slate-400")
                ui.button(
                    "Open full workbench",
                    icon="science",
                    on_click=lambda: ui.navigate.to("/technical-research"),
                    color="primary",
                ).props("no-caps")

            with ui.element("section").classes("ytis-kpi-row"):
                _kpi("Operating mode", "Local", "No cloud dependency")
                _kpi("Finding state", "Pending", "Explicit review required")
                _kpi("Evidence model", "Grounded", "Source IDs and offsets")
                _kpi("Reusable output", "Accepted only", "Cards and reviewed reports")

            with ui.card().classes("ytis-card p-0 w-full"):
                with ui.row().classes("w-full justify-between items-start px-5 pt-5 pb-3"):
                    with ui.column().classes("gap-1"):
                        ui.label("Primary workflows").classes("text-lg font-bold")
                        ui.label("Operational entry points ordered from quickest review to complete research.").classes(
                            "text-sm text-slate-400"
                        )
                    ui.badge("4 available", color="blue").props("outline")
                ui.separator()
                with ui.column().classes("w-full px-5 pb-2 gap-0"):
                    _entry_row(
                        icon="play_circle",
                        title="Public-safe demo",
                        description="Inspect a complete source → evidence → finding journey with no setup or persistence.",
                        action="Open demo",
                        route="/demo",
                        test_id="start-demo",
                        status="Quick review",
                    )
                    _entry_row(
                        icon="upload_file",
                        title="Local source import",
                        description="Validate one UTF-8 text or Markdown file and save a reopenable investigation.",
                        action="Import source",
                        route="/local-source-import",
                        test_id="start-import",
                        status="Single source",
                    )
                    _entry_row(
                        icon="science",
                        title="Technical research workbench",
                        description="Build multi-source packs, review grounded findings, create cards and export reports.",
                        action="Open workbench",
                        route="/technical-research",
                        test_id="start-workbench",
                        status="Full workflow",
                    )
                    _entry_row(
                        icon="bookmarks",
                        title="Insight card library",
                        description="Review persisted accepted insights and advisory exact-card relationships.",
                        action="View cards",
                        route="/insight-cards",
                        test_id="start-cards",
                        status="Reusable output",
                    )

            with ui.card().classes("ytis-card p-4 w-full").style(
                "border-left: 4px solid var(--ytis-amber-700) !important; background: var(--ytis-amber-100) !important"
            ):
                ui.label("Human-review boundary").classes("font-bold text-amber-300")
                ui.label(
                    "YTIS never accepts findings automatically. Reusable cards and reviewed reports require accepted, grounded findings."
                ).classes("text-sm text-slate-300").props("data-testid=start-review-boundary")
