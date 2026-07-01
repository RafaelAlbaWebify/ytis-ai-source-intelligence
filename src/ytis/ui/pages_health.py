from __future__ import annotations

from nicegui import ui

from ytis.core.health import get_health_snapshot
from ytis.ui.components import page_title
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState


def render_health(state: AppState) -> None:
    render_shell(state, "/health")
    health = get_health_snapshot()

    with ui.column().classes("ytis-page gap-4"):
        page_title("Health", "Runtime and local path diagnostics")

        with ui.card().classes("ytis-card p-5 w-full"):
            for key, value in health.items():
                with ui.row().classes("w-full justify-between gap-4 border-b border-slate-800 py-2"):
                    ui.label(str(key)).classes("text-slate-400")
                    ui.label(str(value)).classes("text-right break-all")
