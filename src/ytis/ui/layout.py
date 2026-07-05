from __future__ import annotations

from nicegui import ui
from ytis.ui.context import sidebar_context_label
from ytis.ui.state import AppState


NAV_GROUPS = [
    (
        "Cockpit",
        [
            ("Dashboard", "/", "dashboard"),
        ],
    ),
    (
        "Sources",
        [
            ("Build Source Pack", "/build", "construction"),
            ("Library", "/library", "folder"),
            ("Inspector", "/inspector", "fact_check"),
        ],
    ),
    (
        "Mission",
        [
            ("Mission Manager", "/missions", "flag"),
            ("Analysis Library", "/analysis-library", "move_to_inbox"),
        ],
    ),
    (
        "Discovery",
        [
            ("Research Radar", "/research-radar", "radar"),
            ("Expert Intelligence", "/expert-intelligence", "psychology"),
        ],
    ),
    (
        "Evidence",
        [
            ("Search", "/search", "search"),
            ("Viewer", "/viewer", "article"),
            ("Evidence Explorer", "/intelligence", "hub"),
        ],
    ),
    (
        "Knowledge",
        [
            ("Knowledge Cards", "/knowledge", "category"),
        ],
    ),
    (
        "Admin",
        [
            ("Repair", "/repair", "healing"),
            ("Health", "/health", "monitor_heart"),
            ("Prompt Builder", "/analyze", "psychology"),
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
        <script>
        (function() {
            function setImportant(el, name, value) {
                try { el.style.setProperty(name, value, 'important'); } catch (e) {}
            }
            window.ytisForceSidebarGeometry = function(collapsed) {
                var sidebarWidth = collapsed ? '56px' : '205px';
                var sidebars = document.querySelectorAll('.ytis-sidebar');
                sidebars.forEach(function(el) {
                    setImportant(el, 'width', sidebarWidth);
                    setImportant(el, 'min-width', sidebarWidth);
                    setImportant(el, 'max-width', sidebarWidth);
                });
                var containers = document.querySelectorAll('.q-page-container');
                containers.forEach(function(el) {
                    setImportant(el, 'padding-left', sidebarWidth);
                });
            };
            window.ytisApplySidebarState = function(collapsed) {
                try {
                    document.documentElement.classList.toggle('ytis-sidebar-collapsed', collapsed);
                    if (document.body) {
                        document.body.classList.toggle('ytis-sidebar-collapsed', collapsed);
                    }
                    localStorage.setItem('ytis_sidebar_collapsed', collapsed ? '1' : '0');
                    var toggles = document.querySelectorAll('.ytis-sidebar-toggle .q-icon');
                    toggles.forEach(function(icon) {
                        icon.textContent = collapsed ? 'menu' : 'menu_open';
                    });
                    var buttons = document.querySelectorAll('.ytis-sidebar-toggle');
                    buttons.forEach(function(button) {
                        button.setAttribute('title', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
                        button.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
                    });
                    window.ytisForceSidebarGeometry(collapsed);
                } catch (e) {}
            };
            window.ytisToggleSidebar = function() {
                var collapsed = !document.documentElement.classList.contains('ytis-sidebar-collapsed');
                window.ytisApplySidebarState(collapsed);
                setTimeout(function() { window.ytisForceSidebarGeometry(collapsed); }, 40);
                setTimeout(function() { window.ytisForceSidebarGeometry(collapsed); }, 180);
            };
            window.ytisInitSidebarState = function() {
                try {
                    var collapsed = localStorage.getItem('ytis_sidebar_collapsed') === '1';
                    window.ytisApplySidebarState(collapsed);
                    setTimeout(function() { window.ytisForceSidebarGeometry(collapsed); }, 40);
                    setTimeout(function() { window.ytisForceSidebarGeometry(collapsed); }, 180);
                } catch (e) {}
            };
            if (localStorage.getItem('ytis_sidebar_collapsed') === '1') {
                document.documentElement.classList.add('ytis-sidebar-collapsed');
            }
            document.addEventListener('DOMContentLoaded', function() {
                window.ytisInitSidebarState();
            });
            setTimeout(function() {
                if (window.ytisInitSidebarState) {
                    window.ytisInitSidebarState();
                }
            }, 0);
        })();
        </script>
        <style>
        html, body, .nicegui-content, .q-page, .q-layout, .q-page-container { scrollbar-gutter: stable; }
        body { background: #0f172a; }
        *, *::before, *::after { box-sizing: border-box; }
        .nicegui-content, .q-page, .q-layout, .q-page-container { min-width: 0; }
        .q-page-container { padding-left: 205px !important; transition: padding-left 160ms ease; }
        html.ytis-sidebar-collapsed .q-page-container,
        body.ytis-sidebar-collapsed .q-page-container { padding-left: 56px !important; }
        .ytis-page {
            width: 100%;
            max-width: 1580px;
            margin: 0 auto;
            padding: 22px 26px;
            color: #e2e8f0;
            min-width: 0;
            overflow-x: hidden;
        }
        .ytis-card { background: #111827; border: 1px solid #1f2937; border-radius: 16px; min-width: 0; overflow-wrap: anywhere; }
        .ytis-mini-card { background: #0b1220; border: 1px solid #1e293b; border-radius: 12px; min-width: 0; overflow-wrap: anywhere; }
        .ytis-metric { background: #111827; border: 1px solid #1f2937; border-radius: 16px; min-height: 108px; min-width: 0; overflow-wrap: anywhere; }
        .ytis-grid-2, .ytis-grid-3, .ytis-grid-4, .ytis-grid-5 { display: grid; width: 100%; gap: 12px; }
        .ytis-grid-2 { grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
        .ytis-grid-3 { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
        .ytis-grid-4 { grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }
        .ytis-grid-5 { grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }
        .ytis-toolbar-row, .ytis-card-row { flex-wrap: wrap; min-width: 0; }
        .ytis-flex-main { flex: 1 1 520px; min-width: 320px; }
        .ytis-flex-side { flex: 1 1 360px; min-width: 300px; }
        @media (max-width: 700px) {
            .ytis-page { padding: 16px 14px; }
            .ytis-grid-2, .ytis-grid-3, .ytis-grid-4, .ytis-grid-5 { grid-template-columns: 1fr; }
        }

        .ytis-sidebar {
            position: fixed !important;
            left: 0 !important;
            top: 44px !important;
            bottom: 0 !important;
            z-index: 2000 !important;
            background: #020617 !important;
            border-right: 1px solid #1e293b;
            width: 205px !important;
            min-width: 205px !important;
            max-width: 205px !important;
            transition: width 160ms ease, min-width 160ms ease, max-width 160ms ease;
            overflow-x: hidden !important;
            overflow-y: auto !important;
        }
        .ytis-sidebar-inner { transition: padding 160ms ease; min-height: 100%; }
        .ytis-brand-row { width: 100%; align-items: flex-start; justify-content: space-between; gap: 6px; min-width: 0; }
        .ytis-brand-text { min-width: 0; flex: 1 1 auto; }
        .ytis-brand-title { font-size: 21px; font-weight: 800; line-height: 1.05; }
        .ytis-brand-subtitle { font-size: 10px; color: #94a3b8; line-height: 1.15; }
        .ytis-sidebar-toggle {
            color: #93c5fd !important;
            min-width: 28px !important;
            width: 28px !important;
            height: 28px !important;
            border-radius: 8px !important;
            flex: 0 0 auto;
        }
        .ytis-sidebar-toggle:hover { background: rgba(59, 130, 246, 0.18) !important; }
        .ytis-nav-expanded { display: flex; }
        .ytis-nav-collapsed { display: none; }
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
            transition: background 160ms ease, padding 160ms ease;
            overflow: hidden;
        }
        .ytis-nav-button .q-btn__content {
            justify-content: flex-start !important;
            text-align: left !important;
            gap: 7px !important;
            min-width: 0;
            flex-wrap: nowrap !important;
        }
        .ytis-nav-button .q-icon {
            font-size: 18px !important;
            margin-right: 3px !important;
            flex: 0 0 auto;
        }
        .ytis-nav-button .block {
            text-align: left !important;
            font-size: 11px !important;
            letter-spacing: .015em;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .ytis-nav-rail-button {
            width: 36px !important;
            min-width: 36px !important;
            max-width: 36px !important;
            height: 34px !important;
            min-height: 34px !important;
            border-radius: 10px !important;
            padding: 0 !important;
            justify-content: center !important;
            margin: 0 auto 3px auto;
        }
        .ytis-nav-rail-button .q-btn__content { justify-content: center !important; gap: 0 !important; }
        .ytis-nav-rail-button .q-icon { font-size: 19px !important; margin: 0 !important; }
        .ytis-nav-active { background: #1d4ed8 !important; color: white !important; }
        .ytis-header { padding-left: 8px; min-height: 36px !important; }
        .ytis-current-project-box {
            border-top: 1px solid #1e293b;
            padding-top: 8px;
            margin-top: 8px;
        }
        html.ytis-sidebar-collapsed .ytis-sidebar,
        body.ytis-sidebar-collapsed .ytis-sidebar {
            width: 56px !important;
            min-width: 56px !important;
            max-width: 56px !important;
        }
        html.ytis-sidebar-collapsed .ytis-sidebar-inner,
        body.ytis-sidebar-collapsed .ytis-sidebar-inner { padding-left: 8px !important; padding-right: 8px !important; }
        html.ytis-sidebar-collapsed .ytis-brand-row,
        body.ytis-sidebar-collapsed .ytis-brand-row { justify-content: center; }
        html.ytis-sidebar-collapsed .ytis-brand-text,
        body.ytis-sidebar-collapsed .ytis-brand-text,
        html.ytis-sidebar-collapsed .ytis-nav-expanded,
        body.ytis-sidebar-collapsed .ytis-nav-expanded,
        html.ytis-sidebar-collapsed .ytis-current-project-box,
        body.ytis-sidebar-collapsed .ytis-current-project-box,
        html.ytis-sidebar-collapsed .ytis-sidebar-separator,
        body.ytis-sidebar-collapsed .ytis-sidebar-separator { display: none !important; }
        html.ytis-sidebar-collapsed .ytis-nav-collapsed,
        body.ytis-sidebar-collapsed .ytis-nav-collapsed { display: flex !important; }


        /* YTIS professional dark theme overrides */
        :root {
            --ytis-bg: #07111f;
            --ytis-bg-deep: #040a14;
            --ytis-surface: #0d1829;
            --ytis-surface-raised: #111f33;
            --ytis-surface-soft: #16263d;
            --ytis-border: #24344d;
            --ytis-border-soft: rgba(148, 163, 184, 0.13);
            --ytis-border-active: #3b82f6;
            --ytis-text: #e5eef9;
            --ytis-text-secondary: #aab8cc;
            --ytis-text-muted: #71829a;
            --ytis-blue: #3b82f6;
            --ytis-blue-soft: rgba(59, 130, 246, 0.16);
            --ytis-blue-hover: #60a5fa;
            --ytis-green: #22c55e;
            --ytis-green-soft: rgba(34, 197, 94, 0.14);
            --ytis-amber: #f59e0b;
            --ytis-amber-soft: rgba(245, 158, 11, 0.15);
            --ytis-red: #ef4444;
        }
        html, body, .q-layout, .q-page-container, .nicegui-content {
            background: radial-gradient(circle at top left, rgba(59, 130, 246, 0.09), transparent 30%), var(--ytis-bg) !important;
            color: var(--ytis-text) !important;
        }
        .ytis-page { color: var(--ytis-text) !important; }
        .ytis-card,
        .ytis-metric {
            background: linear-gradient(180deg, rgba(17, 31, 51, 0.96), rgba(13, 24, 41, 0.96)) !important;
            border: 1px solid var(--ytis-border-soft) !important;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.18) !important;
        }
        .ytis-mini-card {
            background: rgba(13, 24, 41, 0.88) !important;
            border: 1px solid var(--ytis-border-soft) !important;
        }
        .ytis-muted, .text-slate-400 { color: var(--ytis-text-secondary) !important; }
        .text-slate-500, .text-slate-600 { color: var(--ytis-text-muted) !important; }
        .ytis-blue, .text-blue-300, .text-blue-400 { color: var(--ytis-blue-hover) !important; }
        .ytis-green, .text-green-300, .text-green-400 { color: var(--ytis-green) !important; }
        .ytis-log, .q-textarea textarea, .q-input input {
            background: rgba(7, 17, 31, 0.92) !important;
            color: var(--ytis-text) !important;
        }
        .q-field__control:before { border-color: rgba(170, 184, 204, 0.28) !important; }
        .q-field--focused .q-field__control:after { border-color: var(--ytis-blue) !important; }
        .q-btn.bg-primary, .q-btn.text-primary.bg-primary,
        .q-btn[style*="background"] {
            box-shadow: none !important;
        }
        .ytis-sidebar {
            background: linear-gradient(180deg, #07111f 0%, #050b16 100%) !important;
            border-right: 1px solid rgba(148, 163, 184, 0.12) !important;
        }
        .ytis-header {
            background: rgba(4, 10, 20, 0.94) !important;
            border-bottom: 1px solid rgba(148, 163, 184, 0.12) !important;
            backdrop-filter: blur(8px);
        }
        .ytis-brand-title { color: var(--ytis-text) !important; letter-spacing: .01em; }
        .ytis-brand-subtitle { color: var(--ytis-text-secondary) !important; }
        .ytis-nav-group { color: #8290a4 !important; letter-spacing: .11em; }
        .ytis-nav-button,
        .ytis-nav-rail-button {
            color: var(--ytis-text-secondary) !important;
        }
        .ytis-nav-button:hover,
        .ytis-nav-rail-button:hover {
            background: rgba(59, 130, 246, 0.10) !important;
            color: var(--ytis-text) !important;
        }
        .ytis-nav-active {
            background: linear-gradient(90deg, rgba(59, 130, 246, 0.30), rgba(59, 130, 246, 0.16)) !important;
            border: 1px solid rgba(96, 165, 250, 0.28) !important;
            color: #f8fbff !important;
        }
        .ytis-current-project-box {
            border-top: 1px solid rgba(148, 163, 184, 0.12) !important;
        }

        </style>
    """)

    with ui.element("aside").classes("ytis-sidebar text-white"):
        with ui.column().classes("ytis-sidebar-inner w-full gap-1 px-3 py-3"):
            with ui.row().classes("ytis-brand-row"):
                with ui.column().classes("ytis-brand-text gap-0"):
                    ui.label("YTIS").classes("ytis-brand-title")
                    ui.label("YouTube Intelligence System").classes("ytis-brand-subtitle")
                ui.button(
                    icon="menu_open",
                    on_click=lambda: ui.run_javascript("window.ytisToggleSidebar && window.ytisToggleSidebar();"),
                ).props("flat round dense").classes("ytis-sidebar-toggle")
            ui.separator().classes("ytis-sidebar-separator my-2")

            with ui.column().classes("ytis-nav-expanded w-full gap-1"):
                for group_name, items in NAV_GROUPS:
                    ui.label(group_name).classes("ytis-nav-group")
                    for label, path, icon in items:
                        button = ui.button(label, icon=icon, on_click=lambda p=path: ui.navigate.to(p)).props("flat no-caps align=left")
                        button.classes("ytis-nav-button")
                        if _active_for(path, active_path):
                            button.classes(add="ytis-nav-active")

            with ui.column().classes("ytis-nav-collapsed w-full gap-1 items-center"):
                for _group_name, items in NAV_GROUPS:
                    for label, path, icon in items:
                        button = ui.button(icon=icon, on_click=lambda p=path: ui.navigate.to(p)).props("flat round dense")
                        button.classes("ytis-nav-rail-button")
                        button.tooltip(label)
                        if _active_for(path, active_path):
                            button.classes(add="ytis-nav-active")

            with ui.column().classes("ytis-current-project-box w-full gap-1"):
                ui.label("Current project").classes("text-xs text-slate-500")
                ui.label(sidebar_context_label(state)).classes("text-xs text-slate-300 break-all")

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
    from ytis.ui.pages_research_radar import render_research_radar
    from ytis.ui.pages_expert_intelligence import render_expert_intelligence

    try:
        from ytis.ui.pages_inspect import render_inspect as render_inspector
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

    @ui.page("/inspect")
    def inspect_legacy_page() -> None:
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

    @ui.page("/research-radar")
    def research_radar_page() -> None:
        render_research_radar(state)

    @ui.page("/expert-intelligence")
    def expert_intelligence_page() -> None:
        render_expert_intelligence(state)

    @ui.page("/analysis-library")
    def analysis_library_page() -> None:
        render_analysis_inbox(state)

    @ui.page("/analysis-inbox")
    def analysis_inbox_legacy_page() -> None:
        render_analysis_inbox(state)

    @ui.page("/missions")
    def missions_page() -> None:
        render_missions(state)
