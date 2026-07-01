from __future__ import annotations

from nicegui import ui

from ytis.core.library_intelligence import (
    compact,
    create_library_upload_bundle,
    generate_prompt,
    ranked_projects,
    save_prompt,
    summarize,
)
from ytis.core.project_hygiene import audit_projects
from ytis.ui.components import open_path
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, short_path, val


def _metric(title: str, value: str, caption: str = "") -> None:
    with ui.card().classes("ytis-metric p-4"):
        ui.label(title).classes("text-sm text-slate-400")
        ui.label(value).classes("text-2xl font-bold whitespace-nowrap")
        if caption:
            ui.label(caption).classes("text-xs text-slate-500")


def render_intelligence(state: AppState) -> None:
    render_shell(state, "/intelligence")

    projects = audit_projects(state.load_projects())
    ranked = ranked_projects(projects)
    stats = summarize(projects)

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("Multi-Project Intelligence").classes("text-3xl font-bold")
                ui.label("Compare saved packs and generate cross-channel analysis prompts").classes("text-sm text-slate-300")
            with ui.row().classes("gap-2"):
                ui.button("Search Library", icon="search", on_click=lambda: ui.navigate.to("/search")).props("outline")
                ui.button("Build New Pack", icon="add", on_click=lambda: ui.navigate.to("/build"), color="primary")

        with ui.grid(columns=5).classes("w-full gap-3"):
            _metric("Projects", compact(stats.projects), "library")
            _metric("Videos", compact(stats.videos), "indexed")
            _metric("Transcripts", compact(stats.transcripts), "clean TXT")
            _metric("Words", compact(stats.words), "analysis volume")
            _metric("ZIP-ready", compact(stats.zip_ready), "upload packs")

        with ui.grid(columns=2).classes("w-full gap-4"):
            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Project Comparison").classes("text-xl font-bold")
                rows = []
                for p in ranked:
                    rows.append({
                        "Project": val(p, "name", "Unnamed"),
                        "Strength": val(p, "_strength", "-"),
                        "Videos": compact(p.get("videos_found")),
                        "TXT": compact(p.get("transcripts_created")),
                        "Words": compact(p.get("total_words")),
                        "Words/TXT": compact(p.get("_density")),
                        "Status": val(p, "_hygiene_status", "-"),
                    })
                if rows:
                    ui.table(
                        columns=[{"name": k, "label": k, "field": k} for k in rows[0].keys()],
                        rows=rows,
                        row_key="Project",
                    ).classes("w-full")
                else:
                    ui.label("No projects yet.").classes("text-slate-400")

            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Library Upload Bundle").classes("text-xl font-bold")
                ready = stats.projects >= 2 and stats.zip_ready >= 2
                ui.label("Ready to bundle multiple research packs" if ready else "Build at least two ZIP-ready packs").classes(
                    "text-green-400 font-bold" if ready else "text-yellow-300 font-bold"
                )
                ui.label("Creates one ZIP containing all ZIP-ready packs, the multi-project prompt, and a README.").classes("text-sm text-slate-400")
                bundle_status = ui.label("No bundle created yet.").classes("text-xs text-slate-500")
                with ui.row().classes("gap-2 mt-3"):
                    create_bundle_btn = ui.button("Create Upload Bundle", icon="archive", color="primary")
                    open_bundle_btn = ui.button("Open Bundle", icon="inventory_2").props("outline")
                    open_bundle_btn.disable()

        with ui.card().classes("ytis-card p-5 w-full"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Cross-Project Prompt Generator").classes("text-xl font-bold")
                prompt_status = ui.label("Ready").classes("text-xs text-green-400")

            focus = ui.textarea(
                "Analysis focus",
                value="Compare these channels for business lessons, service ideas, offer/pricing patterns, acquisition workflows, and practical actions for Webify Digital Solutions.",
            ).classes("w-full").props("rows=3")

            with ui.row().classes("gap-2 mt-2"):
                generate_btn = ui.button("Generate Library Prompt", icon="hub", color="primary")
                copy_btn = ui.button("Copy Prompt", icon="content_copy").props("outline")
                save_btn = ui.button("Save MD", icon="save").props("outline")
                ui.button("Open Downloads", icon="folder_open", on_click=lambda: open_path(state.downloads_dir)).props("outline")

            copy_btn.disable()
            save_btn.disable()
            output = ui.textarea("Generated multi-project prompt").classes("w-full mt-3").props("rows=22")
            output.style("font-family: Consolas, monospace; font-size: 12px; line-height: 1.45;")

            last_bundle = {"path": None}

            def do_generate() -> None:
                if not projects:
                    ui.notify("No projects available", type="warning")
                    return
                text = generate_prompt(projects, focus.value or "")
                output.value = text
                output.update()
                copy_btn.enable()
                save_btn.enable()
                prompt_status.text = f"Generated | {len(text):,} characters"
                prompt_status.update()

            def do_copy() -> None:
                text = output.value or ""
                safe = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
                ui.run_javascript(f"navigator.clipboard.writeText(`{safe}`)")
                ui.notify("Prompt copied", type="positive")

            def do_save() -> None:
                path = save_prompt(output.value or "", state.downloads_dir)
                ui.notify(f"Saved: {path}", type="positive")
                open_path(path)

            def do_bundle() -> None:
                if not projects:
                    ui.notify("No projects available", type="warning")
                    return
                result = create_library_upload_bundle(projects, focus.value or "", state.downloads_dir)
                last_bundle["path"] = result.bundle_path
                bundle_status.text = f"Bundle ready: {result.bundle_path.name} | {len(result.included_zips)} packs included"
                bundle_status.classes(remove="text-slate-500")
                bundle_status.classes(add="text-green-400")
                bundle_status.update()
                open_bundle_btn.enable()
                ui.notify("Library upload bundle created", type="positive")
                open_path(result.bundle_path)

            generate_btn.on("click", do_generate)
            copy_btn.on("click", do_copy)
            save_btn.on("click", do_save)
            create_bundle_btn.on("click", do_bundle)
            open_bundle_btn.on("click", lambda: open_path(last_bundle["path"]) if last_bundle["path"] else None)
            if projects:
                do_generate()

        with ui.card().classes("ytis-card p-5 w-full"):
            ui.label("ZIP Upload Checklist").classes("text-xl font-bold")
            ui.label("Upload these ZIPs together when using the cross-project prompt, or use the Library Upload Bundle above.").classes("text-sm text-slate-400")
            for p in ranked:
                with ui.row().classes("w-full justify-between border-b border-slate-800 py-1"):
                    ui.label(val(p, "name", "Unnamed")).classes("text-sm font-bold")
                    if p.get("zip_path"):
                        ui.button(short_path(p.get("zip_path"), 70), icon="inventory_2", on_click=lambda path=p.get("zip_path"): open_path(path)).props("outline dense")
                    else:
                        ui.label("No ZIP").classes("text-sm text-red-400")
