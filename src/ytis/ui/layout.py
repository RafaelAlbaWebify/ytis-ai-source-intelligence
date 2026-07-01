from __future__ import annotations

from nicegui import ui
from ytis.ui.state import AppState

NAV_ITEMS = [
    ("Dashboard", "/", "dashboard"),
    ("Build", "/build", "construction"),
    ("Projects", "/projects", "folder"),
    ("Search", "/search", "search"),
    ("Viewer", "/viewer", "article"),
    ("Inspector", "/inspector", "fact_check"),
    ("Repair", "/repair", "healing"),
    ("Health", "/health", "monitor_heart"),
    ("Analyze", "/analyze", "psychology"),
    ("Intelligence", "/intelligence", "hub"),
    ("Analysis Inbox", "/analysis-inbox", "move_to_inbox"),
]

def render_shell(state: AppState, active_path: str) -> None:
    ui.add_head_html("""
        <style>
        body { background: #0f172a; }
        .ytis-page { width: 100%; max-width: 1500px; margin: 0 auto; padding: 24px; color: #e2e8f0; }
        .ytis-card { background: #111827; border: 1px solid #1f2937; border-radius: 16px; }
        .ytis-mini-card { background: #0b1220; border: 1px solid #1e293b; border-radius: 12px; }
        .ytis-metric { background: #111827; border: 1px solid #1f2937; border-radius: 16px; min-height: 108px; }
        .ytis-sidebar { background: #020617; border-right: 1px solid #1e293b; }
        .ytis-nav-active { background: #1d4ed8 !important; color: white !important; }
        .ytis-nav-button { width: 100%; justify-content: flex-start; }
        </style>
    """)
    with ui.left_drawer(value=True).classes("ytis-sidebar text-white"):
        with ui.column().classes("w-full gap-3 p-3"):
            ui.label("YTIS").classes("text-2xl font-bold")
            ui.label("YouTube Intelligence System").classes("text-xs text-slate-400")
            ui.separator()
            for label, path, icon in NAV_ITEMS:
                button = ui.button(label, icon=icon, on_click=lambda p=path: ui.navigate.to(p)).props("flat")
                button.classes("ytis-nav-button")
                if path == active_path:
                    button.classes(add="ytis-nav-active")
            ui.separator()
            ui.label("Current project").classes("text-xs text-slate-500")
            ui.label(getattr(state, "current_project_name", "") or "No active project").classes("text-sm text-slate-300")
    with ui.header().classes("bg-slate-950 text-white border-b border-slate-800"):
        with ui.row().classes("w-full justify-between items-center"):
            ui.label("YTIS Local Research OS").classes("font-bold")
            ui.label(getattr(state, "app_version", "")).classes("text-xs text-slate-400")

def register_pages(app_version: str = "") -> None:
    try:
        state = AppState(app_version=app_version)
    except TypeError:
        state = AppState()
        state.app_version = app_version

    from ytis.ui.pages_dashboard import render_dashboard
    from ytis.ui.pages_build import render_build
    from ytis.ui.pages_projects import render_projects
    from ytis.ui.pages_search import render_search
    from ytis.ui.pages_health import render_health
    from ytis.ui.pages_analyze import render_analyze
    from ytis.ui.pages_analysis_inbox import render_analysis_inbox

    try:
        from ytis.ui.pages_inspector import render_inspector
    except Exception:
        render_inspector = None
    try:
        from ytis.ui.pages_repair import render_repair
    except Exception:
        render_repair = None
    try:
        from ytis.ui.pages_viewer import render_viewer
    except Exception:
        render_viewer = None
    try:
        from ytis.ui.pages_intelligence import render_intelligence
    except Exception:
        render_intelligence = None

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
    @ui.page("/health")
    def health_page() -> None:
        render_health(state)
    @ui.page("/analyze")
    def analyze_page() -> None:
        render_analyze(state)
    @ui.page("/inspector")
    def inspector_page() -> None:
        if render_inspector:
            render_inspector(state)
        else:
            render_shell(state, "/inspector")
            ui.label("Inspector module not available").classes("ytis-page text-red-300")
    @ui.page("/repair")
    def repair_page() -> None:
        if render_repair:
            render_repair(state)
        else:
            render_shell(state, "/repair")
            ui.label("Repair module not available").classes("ytis-page text-red-300")
    @ui.page("/viewer")
    def viewer_page() -> None:
        if render_viewer:
            render_viewer(state)
        else:
            render_shell(state, "/viewer")
            ui.label("Viewer module not available").classes("ytis-page text-red-300")
    @ui.page("/intelligence")
    def intelligence_page() -> None:
        if render_intelligence:
            render_intelligence(state)
        else:
            render_shell(state, "/intelligence")
            ui.label("Intelligence module not available").classes("ytis-page text-red-300")
    @ui.page("/analysis-inbox")
    def analysis_inbox_page() -> None:
        render_analysis_inbox(state)
