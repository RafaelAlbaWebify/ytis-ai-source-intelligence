from __future__ import annotations

from nicegui import ui

from ytis.ui.state import AppState
from ytis.ui.theme import apply_theme


NAV_ITEMS = [
    ("Dashboard", "/", "dashboard"),
    ("Build Pack", "/build", "rocket_launch"),
    ("Projects", "/projects", "folder"),
    ("Search", "/search", "search"),
    ("Analyze", "/analyze", "psychology"),
    ("Inspect", "/inspect", "inventory_2"),
    ("Health", "/health", "health_and_safety"),
]


def render_shell(state: AppState, active: str) -> None:
    apply_theme()

    with ui.left_drawer(value=True).classes("bg-[#081321] text-white border-r border-slate-800"):
        with ui.column().classes("w-full p-4 gap-3"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("smart_display").classes("text-4xl text-red-500")
                with ui.column().classes("gap-0"):
                    ui.label("YTIS").classes("text-3xl font-bold text-blue-400")
                    ui.label("YouTube Intelligence System").classes("text-xs text-slate-300")
                    ui.label(state.app_version).classes("text-xs text-slate-500")

            ui.separator().classes("bg-slate-700")

            for label, path, icon in NAV_ITEMS:
                button = ui.button(label, icon=icon, on_click=lambda p=path: ui.navigate.to(p)).classes("w-full justify-start")
                if path != active:
                    button.props("outline")
                else:
                    button.props("color=primary")

            ui.space()

            latest = state.current_project or state.load_latest_project()
            with ui.card().classes("ytis-mini-card p-3 w-full"):
                ui.label("CURRENT PROJECT").classes("text-[11px] text-slate-400")
                if latest:
                    ui.label(str(latest.get("name", "Unnamed"))).classes("font-bold")
                    ui.label(str(latest.get("build_mode", "-")) + " mode").classes("text-xs text-blue-300")
                    with ui.row().classes("justify-between"):
                        ui.label("Transcripts").classes("text-xs text-slate-400")
                        ui.label(str(latest.get("transcripts_created", "0"))).classes("text-xs")
                    with ui.row().classes("justify-between"):
                        ui.label("ZIP").classes("text-xs text-slate-400")
                        ui.label("Ready" if latest.get("zip_path") else "Missing").classes("text-xs text-green-400")
                else:
                    ui.label("No project yet").classes("text-sm text-slate-400")

    with ui.header().classes("bg-[#07111f] text-white border-b border-slate-800"):
        with ui.row().classes("w-full items-center justify-between px-4"):
            ui.label("YTIS").classes("font-bold text-blue-300")
            ui.button("New Research Pack", icon="add", on_click=lambda: ui.navigate.to("/build"), color="primary").props("dense")


def register_pages(app_version: str) -> None:
    from ytis.ui.pages_analyze import render_analyze
    from ytis.ui.pages_build import render_build
    from ytis.ui.pages_dashboard import render_dashboard
    from ytis.ui.pages_health import render_health
    from ytis.ui.pages_inspect import render_inspect
    from ytis.ui.pages_projects import render_projects
    from ytis.ui.pages_search import render_search

    state = AppState(app_version=app_version)

    @ui.page("/")
    def dashboard_page() -> None:
        render_dashboard(state)

    @ui.page("/build")
    def build_page() -> None:
        render_build(state)

    @ui.page("/projects")
    def projects_page() -> None:
        render_projects(state)

    @ui.page("/search")
    def search_page() -> None:
        render_search(state)

    @ui.page("/analyze")
    def analyze_page() -> None:
        render_analyze(state)

    @ui.page("/inspect")
    def inspect_page() -> None:
        render_inspect(state)

    @ui.page("/health")
    def health_page() -> None:
        render_health(state)
