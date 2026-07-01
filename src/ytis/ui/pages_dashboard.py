from __future__ import annotations

from nicegui import ui

from ytis.ui.components import health_card, page_title, project_summary_card, recent_projects_list
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState


def render_dashboard(state: AppState) -> None:
    render_shell(state, "/")
    project = state.load_latest_project()
    projects = state.load_projects()

    with ui.column().classes("ytis-page gap-4"):
        page_title("Dashboard", "Current status and recent YouTube research packs")
        project_summary_card(project, "Latest Build")
        with ui.grid(columns=2).classes("w-full gap-4"):
            recent_projects_list(projects, limit=5)
            health_card(state.app_version)
