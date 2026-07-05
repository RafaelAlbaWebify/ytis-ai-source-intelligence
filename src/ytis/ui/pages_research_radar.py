from __future__ import annotations

from nicegui import ui

from ytis.core.expert_intelligence import (
    RESEARCH_GOALS,
    add_custom_query,
    append_campaign_to_queue,
    delete_query,
    export_research_queue,
    generate_search_campaign,
    load_research_queue,
    update_query_status,
)
from ytis.ui.components import open_path
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState

QUEUE_STATUSES = [
    "To search",
    "Searched",
    "Good source found",
    "Transcript captured",
    "Analyzed",
    "Rejected",
    "Converted to mission",
]

PRIORITIES = ["High", "Medium", "Low"]


def _root(state: AppState):
    return state.project_root_path


def render_research_radar(state: AppState) -> None:
    render_shell(state, "/research-radar")
    root = _root(state)
    current_campaign: dict = {}

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center ytis-toolbar-row"):
            with ui.column().classes("gap-0"):
                ui.label("Research Radar").classes("text-3xl font-bold")
                ui.label("Generate intentional YouTube search campaigns and track what to search next.").classes("text-sm text-slate-300")
            with ui.row().classes("gap-2 flex-wrap"):
                ui.button("Expert Intelligence", icon="psychology", on_click=lambda: ui.navigate.to("/expert-intelligence")).props("outline")
                ui.button("Analyze", icon="upload_file", on_click=lambda: ui.navigate.to("/analyze"), color="primary")

        with ui.grid().classes("ytis-grid-4"):
            queue_rows = load_research_queue(root)
            ui_card_metric("Saved queries", str(len(queue_rows)), "research queue")
            ui_card_metric("To search", str(sum(1 for row in queue_rows if row.get("status") == "To search")), "next discovery")
            ui_card_metric("Good sources", str(sum(1 for row in queue_rows if row.get("status") == "Good source found")), "candidate videos")
            ui_card_metric("Captured", str(sum(1 for row in queue_rows if row.get("status") == "Transcript captured")), "ready for YTIS")

        with ui.card().classes("ytis-card p-5 w-full"):
            ui.label("Search Campaign Generator").classes("text-xl font-bold")
            ui.label("Use this before opening YouTube. Each query has a purpose, source-quality checklist, and anti-hype filter.").classes("text-sm text-slate-400")
            with ui.grid().classes("ytis-grid-3 mt-2"):
                goal = ui.select(list(RESEARCH_GOALS.keys()), value="Career Learning", label="Research goal").classes("w-full")
                topic = ui.input("Topic / niche / role", value="Application Support Engineer").classes("w-full")
                notes = ui.input("Extra focus", placeholder="Example: practical logs, SQL, APIs, incident examples, not guru content").classes("w-full")
            with ui.row().classes("gap-2 flex-wrap mt-2"):
                generate_button = ui.button("Generate Campaign", icon="radar", color="primary")
                save_campaign_button = ui.button("Save Generated Queries", icon="playlist_add").props("outline")
                copy_queries_button = ui.button("Copy Queries", icon="content_copy").props("outline")
                save_campaign_button.disable()
                copy_queries_button.disable()
            campaign_status = ui.label("No campaign generated yet.").classes("text-xs text-slate-400 mt-2")
            campaign_container = ui.column().classes("w-full gap-2 mt-3")

        with ui.card().classes("ytis-card p-5 w-full"):
            ui.label("Manual Query").classes("text-xl font-bold")
            with ui.grid().classes("ytis-grid-4"):
                custom_query = ui.input("Query", placeholder="Example: software support engineer production incident SQL logs").classes("w-full")
                custom_goal = ui.select(list(RESEARCH_GOALS.keys()), value="Career Learning", label="Goal").classes("w-full")
                custom_priority = ui.select(PRIORITIES, value="High", label="Priority").classes("w-full")
                custom_notes = ui.input("Notes", placeholder="Why this matters").classes("w-full")
            with ui.row().classes("gap-2 flex-wrap mt-2"):
                add_query_button = ui.button("Add Query", icon="add", color="primary")
                export_button = ui.button("Export Research Queue", icon="archive").props("outline")

        with ui.card().classes("ytis-card p-5 w-full"):
            with ui.row().classes("w-full justify-between items-center ytis-toolbar-row"):
                ui.label("Research Queue").classes("text-xl font-bold")
                refresh_button = ui.button("Refresh", icon="refresh").props("outline dense")
            queue_container = ui.column().classes("w-full gap-2 mt-2")

        def render_campaign(campaign: dict) -> None:
            campaign_container.clear()
            with campaign_container:
                if not campaign:
                    ui.label("Generate a campaign to preview queries.").classes("text-slate-400")
                    return
                ui.label(f"Intent: {campaign.get('intent', '-')}").classes("text-sm text-blue-300")
                for row in campaign.get("queries", []):
                    with ui.card().classes("ytis-mini-card p-4 w-full"):
                        with ui.row().classes("w-full justify-between items-start gap-3 ytis-card-row"):
                            with ui.column().classes("gap-1"):
                                ui.label(row.get("query", "-")).classes("font-bold text-base")
                                ui.label(f"Purpose: {row.get('purpose', '-')}").classes("text-sm text-slate-300")
                                ui.label("Look for: " + "; ".join(row.get("what_to_look_for", [])[:5])).classes("text-xs text-slate-400")
                            with ui.column().classes("gap-1 items-end"):
                                ui.badge(row.get("goal", "-"), color="blue")
                                ui.badge(row.get("priority", "-"), color="orange")

        def generate() -> None:
            nonlocal current_campaign
            current_campaign = generate_search_campaign(goal.value or "Career Learning", topic.value or "", notes.value or "")
            render_campaign(current_campaign)
            save_campaign_button.enable()
            copy_queries_button.enable()
            campaign_status.text = f"Generated {len(current_campaign.get('queries', []))} queries for {current_campaign.get('topic', '-')}."
            campaign_status.update()

        def save_campaign() -> None:
            if not current_campaign:
                ui.notify("Generate a campaign first", type="warning")
                return
            added = append_campaign_to_queue(root, current_campaign)
            ui.notify(f"Saved {added} new queries", type="positive")
            render_queue()

        def copy_queries() -> None:
            if not current_campaign:
                ui.notify("Generate a campaign first", type="warning")
                return
            text = "\n".join(row.get("query", "") for row in current_campaign.get("queries", []))
            safe = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
            ui.run_javascript(f"navigator.clipboard.writeText(`{safe}`)")
            ui.notify("Queries copied", type="positive")

        def add_custom() -> None:
            if not (custom_query.value or "").strip():
                ui.notify("Enter a query first", type="warning")
                return
            add_custom_query(root, custom_query.value, custom_goal.value or "Career Learning", custom_priority.value or "High", custom_notes.value or "")
            custom_query.value = ""
            custom_query.update()
            ui.notify("Query added", type="positive")
            render_queue()

        def export_queue() -> None:
            path = export_research_queue(root, state.downloads_dir)
            ui.notify(f"Exported: {path}", type="positive")
            open_path(path)

        def render_queue() -> None:
            queue_container.clear()
            rows = load_research_queue(root)
            with queue_container:
                if not rows:
                    ui.label("No saved queries yet. Generate a campaign or add a manual query.").classes("text-slate-400")
                    return
                for row in list(reversed(rows))[:30]:
                    with ui.card().classes("ytis-mini-card p-4 w-full"):
                        with ui.row().classes("w-full justify-between items-start gap-3 ytis-card-row"):
                            with ui.column().classes("gap-1 ytis-flex-main"):
                                ui.label(row.get("query", "-")).classes("font-bold")
                                ui.label(f"Goal: {row.get('goal', '-')} | Purpose: {row.get('purpose', '-')}").classes("text-sm text-slate-300")
                                ui.label("Reject if: " + "; ".join(row.get("reject_if", [])[:4])).classes("text-xs text-slate-500")
                            with ui.column().classes("gap-1 items-end ytis-flex-side"):
                                ui.badge(row.get("priority", "-"), color="orange")
                                status_select = ui.select(QUEUE_STATUSES, value=row.get("status", "To search"), label="Status").classes("w-48")
                                qid = str(row.get("query_id") or "")
                                status_select.on("update:model-value", lambda e, query_id=qid, select=status_select: (update_query_status(root, query_id, select.value or "To search"), ui.notify("Status updated", type="positive")))
                                with ui.row().classes("gap-1"):
                                    ui.button("Copy", icon="content_copy", on_click=lambda q=row.get("query", ""): ui.run_javascript("navigator.clipboard.writeText(" + repr(q) + ")")).props("outline dense")
                                    ui.button("Delete", icon="delete", on_click=lambda query_id=qid: (delete_query(root, query_id), render_queue())).props("outline dense color=negative")

        generate_button.on("click", generate)
        save_campaign_button.on("click", save_campaign)
        copy_queries_button.on("click", copy_queries)
        add_query_button.on("click", add_custom)
        export_button.on("click", export_queue)
        refresh_button.on("click", render_queue)
        goal.on("update:model-value", lambda e: topic.set_value(RESEARCH_GOALS.get(goal.value or "", {}).get("default_topic", topic.value or "")))

        generate()
        render_queue()


def ui_card_metric(label: str, value: str, caption: str) -> None:
    with ui.card().classes("ytis-metric p-4"):
        ui.label(label).classes("text-sm text-slate-400")
        ui.label(value).classes("text-2xl font-bold")
        ui.label(caption).classes("text-xs text-slate-500")
