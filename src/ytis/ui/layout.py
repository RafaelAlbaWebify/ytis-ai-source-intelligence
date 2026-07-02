from __future__ import annotations

from nicegui import ui
from ytis.ui.state import AppState


NAV_GROUPS = [
    (
        "Core",
        [
            ("Dashboard", "/", "dashboard"),
            ("Build", "/build", "construction"),
            ("Missions", "/missions", "flag"),
            ("Library", "/library", "folder"),
        ],
    ),
    (
        "Research",
        [
            ("Search", "/search", "search"),
            ("Viewer", "/viewer", "article"),
            ("Intelligence", "/intelligence", "hub"),
            ("Knowledge Cards", "/knowledge", "category"),
            ("Analysis Library", "/analysis-library", "move_to_inbox"),
        ],
    ),
    (
        "Admin",
        [
            ("Inspector", "/inspector", "fact_check"),
            ("Repair", "/repair", "healing"),
            ("Health", "/health", "monitor_heart"),
            ("Analyze", "/analyze", "psychology"),
        ],
    ),
]

NAV_ITEMS = [item for _, items in NAV_GROUPS for item in items]

ROUTE_ALIASES = {
    "/projects": "/library",
    "/analysis-inbox": "/analysis-library",
}


def _canonical_path(path: str) -> str:
    return ROUTE_ALIASES.get(path, path)


def _active_for(path: str, active_path: str) -> bool:
    active = _canonical_path(active_path)
    target = _canonical_path(path)
    if target == "/":
        return active == "/"
    return active == target


def render_shell(state: AppState, active_path: str) -> None:
    ui.add_head_html("""
        <style>
        body { background: #0f172a; }
        .ytis-page {
            width: 100%;
            max-width: 1580px;
            margin: 0 auto;
            padding: 22px 26px;
            color: #e2e8f0;
        }
        .ytis-card { background: #111827; border: 1px solid #1f2937; border-radius: 16px; }
        .ytis-mini-card { background: #0b1220; border: 1px solid #1e293b; border-radius: 12px; }
        .ytis-metric { background: #111827; border: 1px solid #1f2937; border-radius: 16px; min-height: 108px; }

        .ytis-sidebar {
            background: #020617;
            border-right: 1px solid #1e293b;
            width: 205px !important;
            min-width: 205px !important;
            max-width: 205px !important;
        }
        .ytis-sidebar .q-drawer { width: 205px !important; }
        .ytis-brand-title { font-size: 21px; font-weight: 800; line-height: 1.05; }
        .ytis-brand-subtitle { font-size: 10px; color: #94a3b8; line-height: 1.15; }
        .ytis-nav-group {
            margin-top: 6px;
            margin-bottom: 2px;
            padding-left: 2px;
            color: #64748b;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: .09em;
            text-transform: uppercase;
        }
        .ytis-nav-button {
            width: 100%;
            justify-content: flex-start !important;
            text-align: left !important;
            padding-left: 8px !important;
            padding-right: 6px !important;
            min-height: 30px !important;
            border-radius: 8px !important;
        }
        .ytis-nav-button .q-btn__content {
            justify-content: flex-start !important;
            text-align: left !important;
            gap: 7px !important;
        }
        .ytis-nav-button .q-icon {
            font-size: 18px !important;
            margin-right: 3px !important;
        }
        .ytis-nav-button .block {
            text-align: left !important;
            font-size: 11px !important;
            letter-spacing: .015em;
        }
        .ytis-nav-active { background: #1d4ed8 !important; color: white !important; }
        .ytis-header { padding-left: 8px; min-height: 36px !important; }
        .ytis-current-project-box {
            border-top: 1px solid #1e293b;
            padding-top: 8px;
            margin-top: 8px;
        }
        </style>
    """)

    with ui.left_drawer(value=True).classes("ytis-sidebar text-white").props("width=205"):
        with ui.column().classes("w-full gap-1 px-3 py-3"):
            ui.label("YTIS").classes("ytis-brand-title")
            ui.label("YouTube Intelligence System").classes("ytis-brand-subtitle")
            ui.separator().classes("my-2")

            for group_name, items in NAV_GROUPS:
                ui.label(group_name).classes("ytis-nav-group")
                for label, path, icon in items:
                    button = ui.button(label, icon=icon, on_click=lambda p=path: ui.navigate.to(p)).props("flat no-caps align=left")
                    button.classes("ytis-nav-button")
                    if _active_for(path, active_path):
                        button.classes(add="ytis-nav-active")

            with ui.column().classes("ytis-current-project-box w-full gap-1"):
                ui.label("Current project").classes("text-xs text-slate-500")
                ui.label(getattr(state, "current_project_name", "") or "No active project").classes("text-xs text-slate-300")

    with ui.header().classes("bg-slate-950 text-white border-b border-slate-800 ytis-header"):
        with ui.row().classes("w-full justify-between items-center"):
            ui.label("YTIS Local Research OS").classes("font-bold text-sm")
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
    from ytis.ui.pages_missions import render_missions
    from ytis.ui.pages_knowledge import render_knowledge

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

    @ui.page("/library")
    def library_page() -> None:
        render_projects(state)

    @ui.page("/projects")
    def projects_legacy_page() -> None:
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

    @ui.page("/knowledge")
    def knowledge_page() -> None:
        render_knowledge(state)

    @ui.page("/analysis-library")
    def analysis_library_page() -> None:
        render_analysis_inbox(state)

    @ui.page("/analysis-inbox")
    def analysis_inbox_legacy_page() -> None:
        render_analysis_inbox(state)

    @ui.page("/missions")
    def missions_page() -> None:
        render_missions(state)
