from __future__ import annotations

from pathlib import Path
from typing import Any

from nicegui import ui

from ytis.core.project_hygiene import audit_projects
from ytis.ui.components import open_path
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, fmt_int, val


def _status_label(status: str) -> str:
    if status == "clean":
        return "Clean"
    if status == "review":
        return "Review"
    return "Broken"


def _safe_int(value: Any) -> int:
    try:
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return 0


def _compact(value: Any) -> str:
    n = _safe_int(value)
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if abs(n) >= 1_000:
        return f"{n / 1_000:.1f}k".replace(".0k", "k")
    return f"{n:,}"


def _zip_ready(project: dict[str, Any]) -> bool:
    zip_path = project.get("zip_path")
    return bool(zip_path and Path(str(zip_path)).exists())


def _metric(title: str, value: str, caption: str = "", tone: str = "") -> None:
    text_class = "text-2xl font-bold"
    if tone:
        text_class += " " + tone
    with ui.card().classes("ytis-metric p-4"):
        ui.label(title).classes("text-sm text-slate-400")
        ui.label(value).classes(text_class)
        if caption:
            ui.label(caption).classes("text-xs text-slate-500")


def _quick_action(title: str, subtitle: str, icon: str, target: str, color: str = "") -> None:
    with ui.card().classes("ytis-mini-card p-3 w-full"):
        with ui.row().classes("items-center gap-3"):
            ui.icon(icon).classes("text-2xl text-blue-300")
            with ui.column().classes("gap-0 flex-1"):
                ui.label(title).classes("font-bold")
                ui.label(subtitle).classes("text-xs text-slate-400")
            btn = ui.button("Open", icon="arrow_forward", on_click=lambda: ui.navigate.to(target))
            if color:
                btn.props(f"color={color} dense")
            else:
                btn.props("outline dense")


def render_projects(state: AppState) -> None:
    render_shell(state, "/library")
    projects = audit_projects(state.load_projects())

    clean_count = sum(1 for p in projects if p.get("_hygiene_status") == "clean")
    review_count = sum(1 for p in projects if p.get("_hygiene_status") == "review")
    broken_count = sum(1 for p in projects if p.get("_hygiene_status") == "broken")
    zip_ready_count = sum(1 for p in projects if _zip_ready(p))
    transcript_count = sum(_safe_int(p.get("transcripts_created")) for p in projects)
    word_count = sum(_safe_int(p.get("total_words")) for p in projects)

    with ui.column().classes("ytis-page gap-3"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("Research Library").classes("text-3xl font-bold")
                ui.label("Source packs, ZIP readiness, transcript corpus, and research entry points").classes("text-sm text-slate-400")
            with ui.row().classes("gap-2"):
                ui.button("Dashboard", icon="dashboard", on_click=lambda: ui.navigate.to("/")).props("outline")
                ui.button("Build Pack", icon="construction", on_click=lambda: ui.navigate.to("/build"), color="primary")
                ui.button("Search", icon="search", on_click=lambda: ui.navigate.to("/search")).props("outline")

        with ui.grid(columns=6).classes("w-full gap-3"):
            _metric("Projects", str(len(projects)), "source packs")
            _metric("ZIP-ready", str(zip_ready_count), "upload packs", "text-green-400" if zip_ready_count else "text-yellow-400")
            _metric("Transcripts", _compact(transcript_count), "clean/source files")
            _metric("Words", _compact(word_count), "research corpus")
            _metric("Review", str(review_count), "needs attention", "text-yellow-400" if review_count else "")
            _metric("Broken", str(broken_count), "blocked packs", "text-red-400" if broken_count else "")

        with ui.expansion("Library workflow actions", icon="hub", value=True).classes("ytis-card w-full text-white").props("dense expand-separator"):
            with ui.grid(columns=5).classes("w-full gap-3 p-3"):
                _quick_action("Build Pack", "capture or refresh YouTube source packs", "construction", "/build", "primary")
                _quick_action("Search Library", "find transcript snippets and evidence", "search", "/search")
                _quick_action("Viewer", "read transcripts and source text", "article", "/viewer")
                _quick_action("Intelligence", "topic matrix, bundles, evidence", "hub", "/intelligence")
                _quick_action("Analysis Library", "browse saved ChatGPT answers", "move_to_inbox", "/analysis-library")

        with ui.card().classes("ytis-card ytis-table-card p-4 w-full"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Source Packs").classes("text-xl font-bold")
                ui.label("Select one row, then open its folder or ZIP.").classes("text-xs text-slate-400")

            if not projects:
                ui.label("No saved projects yet. Build a pack first.").classes("text-slate-400")
                ui.button("Build new pack", icon="rocket_launch", on_click=lambda: ui.navigate.to("/build"), color="primary")
                return

            columns = [
                {"name": "status", "label": "Status", "field": "status", "sortable": True},
                {"name": "name", "label": "Project", "field": "name", "align": "left", "sortable": True},
                {"name": "mode", "label": "Mode", "field": "build_mode", "sortable": True},
                {"name": "videos", "label": "Videos", "field": "videos_found", "sortable": True},
                {"name": "transcripts", "label": "Transcripts", "field": "transcripts_created", "sortable": True},
                {"name": "files", "label": "Files", "field": "file_counts"},
                {"name": "words", "label": "Words", "field": "total_words", "sortable": True},
                {"name": "issues", "label": "Issues", "field": "issues", "align": "left"},
                {"name": "zip", "label": "ZIP", "field": "zip_status"},
            ]

            rows = []
            for p in projects:
                zip_path = val(p, "zip_path", "")
                rows.append({
                    "status": _status_label(str(p.get("_hygiene_status", "broken"))),
                    "name": val(p, "name", "Unnamed"),
                    "build_mode": val(p, "build_mode"),
                    "videos_found": val(p, "videos_found", "0"),
                    "transcripts_created": val(p, "transcripts_created", "0"),
                    "file_counts": f"{p.get('_srt_files', 0)} SRT / {p.get('_txt_files', 0)} TXT",
                    "total_words": fmt_int(p.get("total_words")),
                    "issues": str(p.get("_hygiene_issues", "OK")),
                    "zip_status": "Ready" if _zip_ready(p) else ("Path only" if zip_path else "Missing"),
                    "project_dir": val(p, "project_dir", ""),
                    "zip_path": zip_path,
                })

            table = ui.table(columns=columns, rows=rows, row_key="name", selection="single").classes("w-full")
            table.props("flat bordered dark dense")

            def selected_row() -> dict[str, Any] | None:
                if not table.selected:
                    ui.notify("Select a source pack first", type="warning")
                    return None
                return table.selected[0]

            def open_selected_folder() -> None:
                row = selected_row()
                if row:
                    open_path(row.get("project_dir", ""))

            def open_selected_zip() -> None:
                row = selected_row()
                if not row:
                    return
                zip_path = row.get("zip_path", "")
                if not zip_path:
                    ui.notify("Selected source pack has no ZIP path", type="warning")
                    return
                open_path(zip_path)

            with ui.row().classes("gap-2 mt-3"):
                ui.button("Open selected folder", icon="folder_open", on_click=open_selected_folder).props("outline")
                ui.button("Open selected ZIP", icon="inventory_2", on_click=open_selected_zip).props("outline")
                ui.button("Search library", icon="search", on_click=lambda: ui.navigate.to("/search")).props("outline")
                ui.button("Build new pack", icon="rocket_launch", on_click=lambda: ui.navigate.to("/build"), color="primary")

        with ui.expansion("Library hygiene rules", icon="fact_check", value=False).classes("ytis-card w-full text-white").props("dense expand-separator"):
            with ui.column().classes("p-4 gap-1"):
                ui.label("Clean: project folder, summary, ZIP, SRT/TXT files, and video IDs are consistent.").classes("text-sm text-slate-400")
                ui.label("Review: usable but missing non-critical files such as index, missing report, or combined MD.").classes("text-sm text-slate-400")
                ui.label("Broken: missing folder/ZIP/summary, no transcript files, count mismatch, or duplicate video IDs.").classes("text-sm text-slate-400")
