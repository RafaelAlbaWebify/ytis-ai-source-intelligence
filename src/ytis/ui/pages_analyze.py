from __future__ import annotations

from nicegui import ui

from ytis.core.analysis_prompts import PROMPT_TEMPLATES, generate_prompt, save_prompt
from ytis.ui.components import open_path
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, val


def render_analyze(state: AppState) -> None:
    render_shell(state, "/analyze")

    projects = state.load_projects()
    project_names = [val(p, "name", "Unnamed") for p in projects]
    latest = state.current_project or state.load_latest_project()
    default_project = val(latest, "name", project_names[0] if project_names else "")

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("Analyze").classes("text-3xl font-bold")
                ui.label("Generate ready-to-copy prompts for ChatGPT analysis of YTIS research packs").classes("text-sm text-slate-300")
            ui.button("Build New Pack", icon="add", on_click=lambda: ui.navigate.to("/build"), color="primary")

        with ui.grid(columns=3).classes("w-full gap-4"):
            with ui.card().classes("ytis-card p-5 w-full").style("grid-column: span 2;"):
                ui.label("Prompt Builder").classes("text-xl font-bold")
                selected_project = ui.select(project_names, value=default_project if default_project in project_names else (project_names[0] if project_names else None), label="Project").classes("w-full")
                template = ui.select(list(PROMPT_TEMPLATES.keys()), value="Master Upload Analysis", label="Prompt type").classes("w-full")
                notes = ui.textarea("Extra notes / focus", placeholder="Example: Focus on service ideas for Webify, pricing, and workflows I can implement.").classes("w-full").props("rows=4")
                with ui.row().classes("gap-2 mt-2"):
                    generate_button = ui.button("Generate Prompt", icon="psychology", color="primary")
                    copy_button = ui.button("Copy Prompt", icon="content_copy").props("outline")
                    save_button = ui.button("Save MD", icon="save").props("outline")
                copy_button.disable()
                save_button.disable()

            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("How to use").classes("text-xl font-bold")
                ui.label("1. Select the project and prompt type.").classes("text-sm text-slate-400")
                ui.label("2. Generate and copy/save the prompt.").classes("text-sm text-slate-400")
                ui.label("3. Upload the YTIS ZIP or combined transcript file to ChatGPT.").classes("text-sm text-slate-400")
                ui.label("4. Paste the generated prompt.").classes("text-sm text-slate-400")
                ui.separator().classes("bg-slate-700 my-3")
                ui.label("This page does not call an AI API. It prepares high-quality prompts for your current workflow.").classes("text-xs text-blue-300")

        output = ui.textarea("Generated prompt").classes("w-full").props("rows=22")

        def selected_project_data() -> dict:
            name = selected_project.value
            return next((p for p in projects if val(p, "name") == name), {}) if projects else {}

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

        def copy() -> None:
            text = output.value or ""
            if not text:
                ui.notify("Generate a prompt first", type="warning")
                return
            escaped = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
            ui.run_javascript(f"navigator.clipboard.writeText(`{escaped}`)")
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

        generate_button.on("click", generate)
        copy_button.on("click", copy)
        save_button.on("click", save)

        if projects:
            generate()
