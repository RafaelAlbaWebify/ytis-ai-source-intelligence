from __future__ import annotations

from nicegui import ui

from ytis.core.analysis_prompts import PROMPT_TEMPLATES, generate_prompt, save_prompt
from ytis.ui.components import open_path
from ytis.ui.formatting import compact_number, full_number
from ytis.ui.context import preferred_project_name
from ytis.ui.layout import render_shell
from ytis.ui.state import short_path, val
from ytis.ui.state import AppState


def _count_words(text: str) -> int:
    return len((text or "").split())


def render_analyze(state: AppState) -> None:
    render_shell(state, "/analyze")

    projects = state.load_projects()
    project_names = [val(p, "name", "Unnamed") for p in projects]
    default_project = preferred_project_name(state, project_names)

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center ytis-toolbar-row"):
            with ui.column().classes("gap-0"):
                ui.label("Analyze").classes("text-3xl font-bold")
                ui.label("Generate ready-to-copy prompts for ChatGPT analysis of YTIS research packs").classes("text-sm text-slate-300")
            with ui.row().classes("gap-2 flex-wrap"):
                ui.button("Inspect Pack", icon="inventory_2", on_click=lambda: ui.navigate.to("/inspector")).props("outline")
                ui.button("Build New Pack", icon="add", on_click=lambda: ui.navigate.to("/build"), color="primary")

        with ui.grid().classes("ytis-grid-3"):
            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Prompt Builder").classes("text-xl font-bold")
                selected_project = ui.select(
                    project_names,
                    value=default_project if default_project in project_names else (project_names[0] if project_names else None),
                    label="Project",
                ).classes("w-full")
                template = ui.select(list(PROMPT_TEMPLATES.keys()), value="Master Upload Analysis", label="Prompt type").classes("w-full")
                notes = ui.textarea(
                    "Extra notes / focus",
                    placeholder="Example: Focus on service ideas for Webify, pricing, workflows, and what I can implement realistically.",
                ).classes("w-full").props("rows=3")
                with ui.row().classes("gap-2 mt-2 flex-wrap"):
                    generate_button = ui.button("Generate Prompt", icon="psychology", color="primary")
                    copy_button = ui.button("Copy Prompt", icon="content_copy").props("outline")
                    save_button = ui.button("Save MD", icon="save").props("outline")
                    open_zip_button = ui.button("Open ZIP", icon="inventory_2").props("outline")
                copy_button.disable()
                save_button.disable()

            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Project Context").classes("text-xl font-bold")
                context_container = ui.column().classes("w-full gap-1")
                ui.separator().classes("bg-slate-700 my-2")
                ui.label("Workflow").classes("font-bold")
                ui.label("1. Inspect the ZIP.").classes("text-sm text-slate-400")
                ui.label("2. Generate and copy/save the prompt.").classes("text-sm text-slate-400")
                ui.label("3. Upload the YTIS ZIP to ChatGPT.").classes("text-sm text-slate-400")
                ui.label("4. Paste the generated prompt.").classes("text-sm text-slate-400")
                ui.separator().classes("bg-slate-700 my-2")
                ui.label("No AI API calls are made here. This page prepares your upload prompt.").classes("text-xs text-blue-300")

        with ui.card().classes("ytis-card p-5 w-full"):
            with ui.row().classes("w-full justify-between items-center ytis-toolbar-row"):
                with ui.column().classes("gap-0"):
                    ui.label("Prompt Preview").classes("text-xl font-bold")
                    prompt_stats = ui.label("No prompt generated yet.").classes("text-xs text-slate-400")
                prompt_status = ui.label("Ready").classes("text-xs text-green-400")
            output = ui.textarea("Generated prompt").classes("w-full mt-2").props("rows=24")
            output.style("font-family: Consolas, monospace; font-size: 12px; line-height: 1.45;")

        def selected_project_data() -> dict:
            name = selected_project.value
            return next((p for p in projects if val(p, "name") == name), {}) if projects else {}

        def render_context() -> None:
            context_container.clear()
            project = selected_project_data()
            with context_container:
                if not project:
                    ui.label("No project selected.").classes("text-slate-400")
                    return

                rows = [
                    ("Name", val(project, "name", "-"), ""),
                    ("Mode", val(project, "build_mode", "-"), ""),
                    ("Videos", compact_number(project.get("videos_found", 0)), full_number(project.get("videos_found", 0))),
                    ("Transcripts", compact_number(project.get("transcripts_created", 0)), full_number(project.get("transcripts_created", 0))),
                    ("Missing", compact_number(project.get("missing_subtitles", 0)), full_number(project.get("missing_subtitles", 0))),
                    ("Words", compact_number(project.get("total_words", 0)), full_number(project.get("total_words", 0))),
                    ("ZIP", short_path(project.get("zip_path", "-"), 48), ""),
                ]
                for key, display_value, full_value in rows:
                    with ui.row().classes("w-full justify-between gap-3 border-b border-slate-800 py-1"):
                        ui.label(key).classes("text-sm text-slate-400")
                        label = ui.label(str(display_value)).classes("text-sm text-right break-all")
                        if full_value:
                            label.tooltip(full_value)

                zip_path = project.get("zip_path")
                if zip_path:
                    open_zip_button.enable()
                else:
                    open_zip_button.disable()

        def generate() -> None:
            project = selected_project_data()
            if not project:
                ui.notify("No project selected", type="warning")
                return
            prompt = generate_prompt(project, template.value or "Master Upload Analysis", notes.value or "")
            output.value = prompt
            output.update()
            copy_button.enable()
            save_button.enable()
            prompt_status.text = "Generated"
            prompt_stats.text = f"{len(prompt):,} characters | {_count_words(prompt):,} words | template: {template.value}"
            prompt_status.update()
            prompt_stats.update()

        def copy() -> None:
            text = output.value or ""
            if not text:
                ui.notify("Generate a prompt first", type="warning")
                return
            safe = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
            ui.run_javascript(f"navigator.clipboard.writeText(`{safe}`)")
            ui.notify("Prompt copied to clipboard", type="positive")

        def save() -> None:
            text = output.value or ""
            if not text:
                ui.notify("Generate a prompt first", type="warning")
                return
            project = selected_project_data()
            path = save_prompt(text, state.downloads_dir, val(project, "name", "project"), template.value or "Prompt")
            ui.notify(f"Saved: {path}", type="positive")
            open_path(path)

        def open_zip() -> None:
            project = selected_project_data()
            zip_path = project.get("zip_path")
            if not zip_path:
                ui.notify("No ZIP path available", type="warning")
                return
            open_path(zip_path)

        generate_button.on("click", generate)
        copy_button.on("click", copy)
        save_button.on("click", save)
        open_zip_button.on("click", open_zip)
        selected_project.on("update:model-value", lambda e: (render_context(), generate()))
        template.on("update:model-value", lambda e: generate())
        notes.on("blur", lambda e: generate())

        render_context()
        if projects:
            generate()
