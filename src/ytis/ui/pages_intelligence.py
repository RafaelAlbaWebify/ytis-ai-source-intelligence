from __future__ import annotations

from nicegui import ui

from ytis.core.library_intelligence import (
    FOCUS_PRESETS,
    TOPIC_KEYWORDS,
    compact,
    create_library_upload_bundle,
    export_topic_evidence,
    export_topic_matrix,
    filter_topic_evidence,
    generate_prompt,
    ranked_projects,
    save_prompt,
    scan_topic_matrix,
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
    topic_rows, topic_evidence = scan_topic_matrix(projects)
    project_names = [val(p, "name", "Unnamed") for p in projects]
    project_checks: dict[str, object] = {}

    def selected_projects() -> list[dict]:
        selected_names = [name for name, checkbox in project_checks.items() if getattr(checkbox, "value", False)]
        selected = [p for p in projects if val(p, "name", "Unnamed") in selected_names]
        return selected or projects

    def open_in_viewer(file_path: str) -> None:
        setattr(state, "viewer_file_path", file_path)
        ui.navigate.to("/viewer")

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center"):
            with ui.column().classes("gap-0"):
                ui.label("Multi-Project Intelligence").classes("text-3xl font-bold")
                ui.label("Compare saved packs, scan business topics, and create selective analysis bundles").classes("text-sm text-slate-300")
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
                    ui.table(columns=[{"name": k, "label": k, "field": k} for k in rows[0].keys()], rows=rows, row_key="Project").classes("w-full")
                else:
                    ui.label("No projects yet.").classes("text-slate-400")

            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Analysis Scope").classes("text-xl font-bold")
                ui.label("Choose which projects should be used for the prompt and bundle.").classes("text-sm text-slate-400")
                with ui.row().classes("gap-3"):
                    for p in ranked:
                        name = val(p, "name", "Unnamed")
                        project_checks[name] = ui.checkbox(name, value=True).classes("text-sm")
                preset_select = ui.select(list(FOCUS_PRESETS.keys()), value="Business lessons", label="Focus preset").classes("w-full")
                selected_status = ui.label("").classes("text-xs text-blue-300")

        with ui.grid(columns=2).classes("w-full gap-4"):
            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Library Upload Bundle").classes("text-xl font-bold")
                ui.label("Creates one ZIP containing selected ZIP-ready packs, prompt, README, topic matrix, and topic evidence.").classes("text-sm text-slate-400")
                bundle_status = ui.label("No bundle created yet.").classes("text-xs text-slate-500")
                with ui.row().classes("gap-2 mt-3"):
                    create_bundle_btn = ui.button("Create Selected Bundle", icon="archive", color="primary")
                    open_bundle_btn = ui.button("Open Bundle", icon="inventory_2").props("outline")
                    open_bundle_btn.disable()

            with ui.card().classes("ytis-card p-5 w-full"):
                ui.label("Scope Summary").classes("text-xl font-bold")
                scope_summary = ui.column().classes("w-full gap-1")

        with ui.card().classes("ytis-card p-5 w-full"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Library Topic Matrix").classes("text-xl font-bold")
                with ui.row().classes("gap-2"):
                    export_matrix_btn = ui.button("Export Matrix CSV", icon="download").props("outline dense")
                    export_evidence_btn = ui.button("Export Evidence CSV", icon="download").props("outline dense")

            ui.label("Local keyword scan across all clean transcripts. Use it as a navigation map, not final analysis.").classes("text-sm text-slate-400")
            if topic_rows:
                columns = [
                    {"name": "Topic", "label": "Topic", "field": "Topic", "align": "left"},
                    {"name": "Total", "label": "Total", "field": "Total", "align": "right"},
                    {"name": "Strongest", "label": "Strongest", "field": "Strongest", "align": "left"},
                ]
                for project_name in project_names:
                    columns.append({"name": project_name, "label": project_name[:16], "field": project_name, "align": "right"})

                display_rows = []
                for row in topic_rows:
                    display = dict(row)
                    display["Total"] = compact(display["Total"])
                    for project_name in project_names:
                        display[project_name] = compact(display.get(project_name, 0))
                    display_rows.append(display)
                ui.table(columns=columns, rows=display_rows, row_key="Topic").classes("w-full")
            else:
                ui.label("No topic data found.").classes("text-slate-400")

        with ui.card().classes("ytis-card p-5 w-full"):
            ui.label("Topic Drilldown").classes("text-xl font-bold")
            with ui.row().classes("w-full gap-3"):
                topic_select = ui.select(["All topics"] + list(TOPIC_KEYWORDS.keys()), value="All topics", label="Topic").classes("flex-1")
                project_select = ui.select(["All projects"] + project_names, value="All projects", label="Project").classes("flex-1")
                limit_select = ui.select([10, 25, 50, 100], value=25, label="Limit").classes("w-32")
            drilldown_status = ui.label("").classes("text-xs text-slate-400")
            drilldown_results = ui.column().classes("w-full gap-2")

            def render_drilldown() -> None:
                drilldown_results.clear()
                filtered = filter_topic_evidence(topic_evidence, topic_select.value or "All topics", project_select.value or "All projects")
                filtered = filtered[: int(limit_select.value or 25)]
                drilldown_status.text = f"{len(filtered)} evidence items shown"
                drilldown_status.update()
                with drilldown_results:
                    if not filtered:
                        ui.label("No evidence for this filter.").classes("text-slate-400")
                        return
                    for hit in filtered:
                        with ui.card().classes("ytis-mini-card p-3 w-full"):
                            with ui.row().classes("w-full justify-between items-start gap-3"):
                                with ui.column().classes("gap-1 flex-1"):
                                    ui.label(f"{hit.topic} | {hit.project} | {hit.matches} matches").classes("font-bold")
                                    ui.label(hit.file_name).classes("text-xs text-blue-300")
                                    ui.label(hit.snippet).classes("text-sm text-slate-300")
                                with ui.column().classes("gap-1"):
                                    ui.button("Open in Viewer", icon="article", on_click=lambda p=hit.file_path: open_in_viewer(p)).props("outline dense")
                                    ui.button("Open TXT", icon="description", on_click=lambda p=hit.file_path: open_path(p)).props("outline dense")

            topic_select.on("update:model-value", lambda e: render_drilldown())
            project_select.on("update:model-value", lambda e: render_drilldown())
            limit_select.on("update:model-value", lambda e: render_drilldown())
            render_drilldown()

        with ui.card().classes("ytis-card p-5 w-full"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Cross-Project Prompt Generator").classes("text-xl font-bold")
                prompt_status = ui.label("Ready").classes("text-xs text-green-400")

            focus = ui.textarea("Analysis focus", value=FOCUS_PRESETS["Business lessons"]).classes("w-full").props("rows=3")

            with ui.row().classes("gap-2 mt-2"):
                generate_btn = ui.button("Generate Scoped Prompt", icon="hub", color="primary")
                copy_btn = ui.button("Copy Prompt", icon="content_copy").props("outline")
                save_btn = ui.button("Save MD", icon="save").props("outline")
                ui.button("Open Downloads", icon="folder_open", on_click=lambda: open_path(state.downloads_dir)).props("outline")

            copy_btn.disable()
            save_btn.disable()
            output = ui.textarea("Generated multi-project prompt").classes("w-full mt-3").props("rows=18")
            output.style("font-family: Consolas, monospace; font-size: 12px; line-height: 1.45;")

            last_bundle = {"path": None}

            def update_scope_summary() -> None:
                selected = selected_projects()
                scoped = summarize(selected)
                selected_status.text = f"{scoped.projects} selected projects | {compact(scoped.words)} words | {scoped.zip_ready} ZIP-ready"
                selected_status.update()
                scope_summary.clear()
                with scope_summary:
                    for key, value in [
                        ("Selected projects", scoped.projects),
                        ("Videos", scoped.videos),
                        ("Transcripts", scoped.transcripts),
                        ("Words", compact(scoped.words)),
                        ("ZIP-ready", scoped.zip_ready),
                    ]:
                        with ui.row().classes("w-full justify-between border-b border-slate-800 py-1"):
                            ui.label(key).classes("text-sm text-slate-400")
                            ui.label(str(value)).classes("text-sm font-bold")

            def apply_preset() -> None:
                preset = preset_select.value or "Business lessons"
                focus.value = FOCUS_PRESETS.get(preset, "")
                focus.update()
                update_scope_summary()
                do_generate()

            def do_generate() -> None:
                selected = selected_projects()
                if not selected:
                    ui.notify("No selected projects", type="warning")
                    return
                text = generate_prompt(selected, focus.value or "", preset_select.value or "Custom")
                output.value = text
                output.update()
                copy_btn.enable()
                save_btn.enable()
                prompt_status.text = f"Generated | {len(text):,} characters | {len(selected)} projects"
                prompt_status.update()
                update_scope_summary()

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
                selected = selected_projects()
                if not selected:
                    ui.notify("No selected projects", type="warning")
                    return
                result = create_library_upload_bundle(selected, focus.value or "", state.downloads_dir, preset_select.value or "Custom")
                last_bundle["path"] = result.bundle_path
                bundle_status.text = f"Bundle ready: {result.bundle_path.name} | {len(result.included_zips)} packs included"
                bundle_status.classes(remove="text-slate-500")
                bundle_status.classes(add="text-green-400")
                bundle_status.update()
                open_bundle_btn.enable()
                ui.notify("Selected upload bundle created", type="positive")
                open_path(result.bundle_path)

            def do_export_matrix() -> None:
                path = export_topic_matrix(topic_rows, state.downloads_dir)
                ui.notify(f"Exported: {path}", type="positive")
                open_path(path)

            def do_export_evidence() -> None:
                filtered = filter_topic_evidence(topic_evidence, topic_select.value or "All topics", project_select.value or "All projects")
                path = export_topic_evidence(filtered, state.downloads_dir)
                ui.notify(f"Exported: {path}", type="positive")
                open_path(path)

            generate_btn.on("click", do_generate)
            copy_btn.on("click", do_copy)
            save_btn.on("click", do_save)
            create_bundle_btn.on("click", do_bundle)
            open_bundle_btn.on("click", lambda: open_path(last_bundle["path"]) if last_bundle["path"] else None)
            export_matrix_btn.on("click", do_export_matrix)
            export_evidence_btn.on("click", do_export_evidence)
            preset_select.on("update:model-value", lambda e: apply_preset())

            for checkbox in project_checks.values():
                checkbox.on("update:model-value", lambda e: (update_scope_summary(), do_generate()))

            if projects:
                update_scope_summary()
                do_generate()

        with ui.card().classes("ytis-card p-5 w-full"):
            ui.label("ZIP Upload Checklist").classes("text-xl font-bold")
            ui.label("Upload these ZIPs together when using the cross-project prompt, or use the selected Library Upload Bundle above.").classes("text-sm text-slate-400")
            for p in ranked:
                with ui.row().classes("w-full justify-between border-b border-slate-800 py-1"):
                    ui.label(val(p, "name", "Unnamed")).classes("text-sm font-bold")
                    if p.get("zip_path"):
                        ui.button(short_path(p.get("zip_path"), 70), icon="inventory_2", on_click=lambda path=p.get("zip_path"): open_path(path)).props("outline dense")
                    else:
                        ui.label("No ZIP").classes("text-sm text-red-400")
