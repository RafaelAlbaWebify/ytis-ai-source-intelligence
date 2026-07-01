from __future__ import annotations

from pathlib import Path

from nicegui import ui

from ytis.core.project_hygiene import audit_project, audit_projects
from ytis.ui.components import (
    command_metric_row,
    health_card,
    open_path,
    page_title,
    recent_projects_list,
)
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, fmt_int, short_path, val


def _next_action(project: dict, status: str) -> str:
    if not project:
        return "No pack exists yet. Build your first research pack."
    if status == "broken":
        return "The current project has hygiene issues. Open Projects and review the status before relying on it."
    if status == "review":
        return "Pack is usable, but some expected files are missing. Review the project hygiene details."
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
    audited_projects = audit_projects(projects)
    hygiene = audit_project(project) if project else None
    hygiene_status = hygiene.status if hygiene else "none"

    with ui.column().classes("ytis-page gap-4"):
        page_title("Dashboard", "Command center for YouTube research packs")

        with ui.grid(columns=2).classes("w-full gap-4"):
            with ui.card().classes("ytis-card p-5 w-full"):
                with ui.row().classes("w-full justify-between items-center"):
                    ui.label("Current Project").classes("text-xl font-bold")
                    if project:
                        color = "text-green-400" if hygiene_status == "clean" else "text-yellow-400" if hygiene_status == "review" else "text-red-400"
                        ui.label(hygiene_status.upper()).classes(f"text-xs font-bold {color}")
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
                ui.label(_next_action(project, hygiene_status)).classes("text-base text-slate-200")
                ui.separator().classes("bg-slate-700 my-3")

                ui.label("Project Hygiene").classes("font-bold")
                if hygiene:
                    ui.label(hygiene.issue_text()).classes("text-sm text-slate-400")
                    with ui.row().classes("gap-2 mt-2"):
                        ui.button("Open Projects", icon="folder", on_click=lambda: ui.navigate.to("/projects"), color="primary")
                        ui.button("Search", icon="search", on_click=lambda: ui.navigate.to("/search")).props("outline")
                else:
                    ui.label("No hygiene report available yet.").classes("text-slate-400")

                ui.separator().classes("bg-slate-700 my-3")
                ui.label("Quick Search").classes("font-bold")
                quick_query = ui.input("Search this project's transcripts").classes("w-full")
                with ui.row().classes("gap-2"):
                    ui.button("Search", icon="search", on_click=lambda: ui.navigate.to("/search"), color="primary")
                    combined_md = _find_first_combined_md(project)
                    if combined_md:
                        ui.button("Open Combined MD", icon="description", on_click=lambda p=combined_md: open_path(p)).props("outline")
                    else:
                        ui.button("Open Combined MD", icon="description").props("outline disable")
                ui.label("Search page is the deep search area. This box is a dashboard shortcut.").classes("text-xs text-slate-500")

        with ui.grid(columns=3).classes("w-full gap-4"):
            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Project Library Status").classes("text-xl font-bold")
                clean_count = sum(1 for p in audited_projects if p.get("_hygiene_status") == "clean")
                review_count = sum(1 for p in audited_projects if p.get("_hygiene_status") == "review")
                broken_count = sum(1 for p in audited_projects if p.get("_hygiene_status") == "broken")
                rows = [
                    ("Projects", str(len(audited_projects))),
                    ("Clean", str(clean_count)),
                    ("Review", str(review_count)),
                    ("Broken", str(broken_count)),
                ]
                for key, value in rows:
                    with ui.row().classes("w-full justify-between gap-3 border-b border-slate-800 py-1"):
                        ui.label(key).classes("text-sm text-slate-400")
                        ui.label(value).classes("text-sm font-bold")

            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Analysis Shortcuts").classes("text-xl font-bold")
                ui.button("Generate upload prompt", icon="content_copy", on_click=lambda: ui.navigate.to("/analyze")).props("outline").classes("w-full")
                ui.button("Business lessons prompt", icon="psychology", on_click=lambda: ui.navigate.to("/analyze")).props("outline").classes("w-full")
                ui.button("Workflow extraction prompt", icon="account_tree", on_click=lambda: ui.navigate.to("/analyze")).props("outline").classes("w-full")
                ui.label("Prompt generator is now available in Analyze.").classes("text-xs text-blue-300 mt-2")

            health_card(state.app_version, compact=True)

        recent_projects_list(projects, limit=5)
