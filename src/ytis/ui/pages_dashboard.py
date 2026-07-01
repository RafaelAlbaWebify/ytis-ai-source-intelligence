from __future__ import annotations

from pathlib import Path

from nicegui import ui

from ytis.ui.components import (
    command_metric_row,
    health_card,
    open_path,
    page_title,
    recent_projects_list,
)
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, fmt_int, short_path, val


def _next_action(project: dict) -> str:
    if not project:
        return "No pack exists yet. Build your first research pack."
    if not project.get("zip_path"):
        return "Project exists, but the ZIP is missing. Repackage or rebuild it."
    missing = str(project.get("missing_subtitles", "0"))
    if missing not in {"0", "-", ""}:
        return f"Pack is ready, but {missing} subtitles are missing. Review the missing report."
    return "Pack is ready. Next: search transcripts, inspect the ZIP, or upload the pack for analysis."


def _find_first_combined_md(project: dict) -> Path | None:
    project_dir = Path(str(project.get("project_dir", "")))
    if not project_dir.exists():
        return None
    candidates = [
        project_dir / "ALL_TRANSCRIPTS_COMBINED.md",
        project_dir / "combined_transcripts.md",
        project_dir / "channel_transcripts.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    found = list(project_dir.glob("*.md"))
    return found[0] if found else None


def render_dashboard(state: AppState) -> None:
    render_shell(state, "/")
    project = state.load_latest_project()
    projects = state.load_projects()

    with ui.column().classes("ytis-page gap-4"):
        page_title("Dashboard", "Command center for YouTube research packs")

        with ui.grid(columns=2).classes("w-full gap-4"):
            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Current Project").classes("text-xl font-bold")
                if not project:
                    ui.label("No current project yet.").classes("text-slate-400")
                    ui.button("Build first pack", icon="rocket_launch", on_click=lambda: ui.navigate.to("/build"), color="primary")
                else:
                    with ui.row().classes("w-full justify-between items-start gap-4"):
                        with ui.column().classes("gap-1"):
                            ui.label(val(project, "name", "Unnamed")).classes("text-2xl font-bold")
                            ui.label(val(project, "url")).classes("text-xs text-blue-300 break-all")
                            ui.label(f"Mode: {val(project, 'build_mode', '-')}").classes("text-sm text-slate-300")
                            ui.label(f"Built: {val(project, 'built_at', val(project, 'last_updated_at', '-'))}").classes("text-xs text-slate-500")
                        with ui.column().classes("gap-2"):
                            if project.get("zip_path"):
                                ui.button("Open ZIP", icon="inventory_2", on_click=lambda p=project: open_path(str(p["zip_path"]))).props("outline").classes("w-full")
                            if project.get("project_dir"):
                                ui.button("Open Folder", icon="folder_open", on_click=lambda p=project: open_path(str(p["project_dir"]))).props("outline").classes("w-full")
                            ui.button("Rebuild / Refresh", icon="rocket_launch", on_click=lambda: ui.navigate.to("/build"), color="primary").classes("w-full")

                    ui.separator().classes("bg-slate-700 my-3")
                    command_metric_row(project)

            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Next Action").classes("text-xl font-bold")
                ui.label(_next_action(project)).classes("text-base text-slate-200")
                ui.separator().classes("bg-slate-700 my-3")
                ui.label("Quick Search").classes("font-bold")
                quick_query = ui.input("Search this project's transcripts").classes("w-full")
                with ui.row().classes("gap-2"):
                    def go_search() -> None:
                        # Query is not passed yet; Search page opens ready for the selected project.
                        ui.navigate.to("/search")
                    ui.button("Search", icon="search", on_click=go_search, color="primary")
                    combined_md = _find_first_combined_md(project)
                    if combined_md:
                        ui.button("Open Combined MD", icon="description", on_click=lambda p=combined_md: open_path(p)).props("outline")
                    else:
                        ui.button("Open Combined MD", icon="description").props("outline disable")
                ui.label("Search page is still the deep search area. This box is a dashboard shortcut.").classes("text-xs text-slate-500")

        with ui.grid(columns=3).classes("w-full gap-4"):
            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Pack Status").classes("text-xl font-bold")
                if project:
                    rows = [
                        ("Project folder", short_path(project.get("project_dir", "-"), 56)),
                        ("ZIP path", short_path(project.get("zip_path", "-"), 56)),
                        ("Language", val(project, "language", "-")),
                        ("Words", fmt_int(project.get("total_words"))),
                    ]
                    for key, value in rows:
                        with ui.row().classes("w-full justify-between gap-3 border-b border-slate-800 py-1"):
                            ui.label(key).classes("text-sm text-slate-400")
                            ui.label(value).classes("text-sm text-right break-all")
                else:
                    ui.label("No status available.").classes("text-slate-400")

            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Analysis Shortcuts").classes("text-xl font-bold")
                ui.button("Generate upload prompt", icon="content_copy").props("outline disable").classes("w-full")
                ui.button("Business lessons prompt", icon="psychology").props("outline disable").classes("w-full")
                ui.button("Workflow extraction prompt", icon="account_tree").props("outline disable").classes("w-full")
                ui.label("Prompt generation is planned for v0.3.5.").classes("text-xs text-blue-300 mt-2")

            health_card(state.app_version, compact=True)

        recent_projects_list(projects, limit=5)
