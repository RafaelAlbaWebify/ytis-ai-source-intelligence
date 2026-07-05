from __future__ import annotations

from nicegui import ui

from ytis.core.expert_intelligence import (
    EXPERT_SOURCE_TYPES,
    EXTRACTION_MODES,
    generate_expert_prompt,
    infer_profile_defaults,
    load_expert_profiles,
    save_expert_profile,
    save_expert_prompt,
)
from ytis.ui.components import open_path
from ytis.ui.context import preferred_project_name
from ytis.ui.layout import render_shell
from ytis.ui.state import AppState, val

RATING_VALUES = ["High", "Medium", "Low", "Unknown"]
FIT_VALUES = ["High", "Medium", "Low", "Later", "Avoid", "Unknown"]
BUSINESS_TYPES = [
    "Unknown",
    "Consulting",
    "Productized service",
    "Agency",
    "Course / coaching",
    "Templates / digital products",
    "Affiliate / content",
    "SaaS / software",
    "Newsletter / community",
    "Local service",
    "Hybrid",
]


def render_expert_intelligence(state: AppState) -> None:
    render_shell(state, "/expert-intelligence")
    projects = state.load_projects()
    project_names = [val(p, "name", "Unnamed") for p in projects]
    default_project = preferred_project_name(state, project_names)
    default_project_record = next((p for p in projects if val(p, "name") == default_project), projects[0] if projects else {})
    initial_defaults = infer_profile_defaults(default_project_record, {"project": default_project})

    with ui.column().classes("ytis-page gap-4"):
        with ui.row().classes("w-full justify-between items-center ytis-toolbar-row"):
            with ui.column().classes("gap-0"):
                ui.label("Expert Intelligence").classes("text-3xl font-bold")
                ui.label("Profile experts, extract career lessons and business models, then create better prompts for ChatGPT.").classes("text-sm text-slate-300")
            with ui.row().classes("gap-2 flex-wrap"):
                ui.button("Research Radar", icon="radar", on_click=lambda: ui.navigate.to("/research-radar")).props("outline")
                ui.button("Knowledge Cards", icon="category", on_click=lambda: ui.navigate.to("/knowledge"), color="primary")

        with ui.grid().classes("ytis-grid-4"):
            profiles = load_expert_profiles(state.project_root_path)
            metric_card("Expert profiles", str(len(profiles)), "saved locally")
            metric_card("Projects", str(len(project_names)), "source packs")
            metric_card("Prompt modes", str(len(EXTRACTION_MODES)), "career/business")
            metric_card("Fit lens", "Rafael", "study, build, test, avoid")

        with ui.row().classes("w-full gap-4 items-start ytis-card-row"):
            with ui.card().classes("ytis-card p-5 ytis-flex-main"):
                ui.label("Expert / Source Profile").classes("text-xl font-bold")
                ui.label("This is a hypothesis until the transcript evidence proves it. Keep it skeptical.").classes("text-sm text-slate-400")
                with ui.grid().classes("ytis-grid-2 mt-2"):
                    selected_project = ui.select(project_names, value=default_project if default_project in project_names else (project_names[0] if project_names else None), label="Project / source pack").classes("w-full")
                    source_name = ui.input("Expert / channel / source name", value=initial_defaults.get("source_name", ""), placeholder="Example: Kieran Moloney").classes("w-full")
                    source_type_default = initial_defaults.get("source_type", "Unknown")
                    if source_type_default not in EXPERT_SOURCE_TYPES:
                        source_type_default = "Unknown"
                    source_type = ui.select(EXPERT_SOURCE_TYPES, value=source_type_default, label="Source type").classes("w-full")
                    topic = ui.input("Topic", value=initial_defaults.get("topic", ""), placeholder="Example: productized services, application support, audits").classes("w-full")
                    business_type_default = initial_defaults.get("business_type", "Unknown")
                    if business_type_default not in BUSINESS_TYPES:
                        business_type_default = "Unknown"
                    business_type = ui.select(BUSINESS_TYPES, value=business_type_default, label="Business type hypothesis").classes("w-full")
                    target_audience = ui.input("Audience / customer", value=initial_defaults.get("target_audience", ""), placeholder="Who they teach or sell to").classes("w-full")
                credibility_notes = ui.textarea("Credibility notes", value=initial_defaults.get("credibility_notes", ""), placeholder="What makes this source credible or risky? Real examples? Proof? Hype?").classes("w-full mt-2").props("rows=3")
                rafael_relevance = ui.textarea("Relevance to Rafael", value=initial_defaults.get("rafael_relevance", ""), placeholder="Why this matters for career, Webify, study, build, or business ideas.").classes("w-full").props("rows=3")

            with ui.card().classes("ytis-card p-5 ytis-flex-side"):
                ui.label("Visual Fit Assessment").classes("text-xl font-bold")
                practical_examples = ui.select(RATING_VALUES, value="Unknown", label="Practical examples").classes("w-full")
                evidence_quality = ui.select(RATING_VALUES, value="Unknown", label="Evidence quality").classes("w-full")
                specificity = ui.select(RATING_VALUES, value="Unknown", label="Specificity").classes("w-full")
                hype_risk = ui.select(RATING_VALUES, value="Unknown", label="Hype risk").classes("w-full")
                rafael_fit = ui.select(FIT_VALUES, value="Unknown", label="Rafael fit").classes("w-full")
                with ui.row().classes("gap-2 mt-2 flex-wrap"):
                    save_profile_button = ui.button("Save Profile", icon="save", color="primary")
                    apply_defaults_button = ui.button("Apply Project Defaults", icon="auto_fix_high").props("outline")
                    reset_button = ui.button("Reset", icon="restart_alt").props("outline")

        with ui.card().classes("ytis-card p-5 w-full"):
            ui.label("Expert Intelligence Prompt").classes("text-xl font-bold")
            with ui.grid().classes("ytis-grid-3"):
                mode = ui.select(EXTRACTION_MODES, value="Both", label="Extraction mode").classes("w-full")
                notes = ui.input("Extra analysis focus", placeholder="Example: look for pricing, delivery workflow, acquisition, what I should study/build").classes("w-full")
                prompt_status = ui.label("Prompt auto-generates from the profile.").classes("text-xs text-slate-400 self-end")
            with ui.row().classes("gap-2 flex-wrap mt-2"):
                generate_button = ui.button("Generate Prompt", icon="psychology", color="primary")
                copy_button = ui.button("Copy Prompt", icon="content_copy").props("outline")
                save_prompt_button = ui.button("Save Prompt MD", icon="save").props("outline")
            prompt_output = ui.textarea("Generated prompt").classes("w-full mt-2").props("rows=22")
            prompt_output.style("font-family: Consolas, monospace; font-size: 12px; line-height: 1.45;")

        with ui.card().classes("ytis-card p-5 w-full"):
            with ui.row().classes("w-full justify-between items-center ytis-toolbar-row"):
                ui.label("Saved Expert Profiles").classes("text-xl font-bold")
                refresh_profiles_button = ui.button("Refresh", icon="refresh").props("outline dense")
            profiles_container = ui.column().classes("w-full gap-2 mt-2")

        def selected_project_data() -> dict:
            name = selected_project.value
            return next((p for p in projects if val(p, "name") == name), {}) if projects else {}

        def profile_payload() -> dict:
            return {
                "project": selected_project.value or "",
                "source_name": source_name.value or "",
                "source_type": source_type.value or "Unknown",
                "topic": topic.value or "",
                "business_type": business_type.value or "Unknown",
                "target_audience": target_audience.value or "",
                "credibility_notes": credibility_notes.value or "",
                "rafael_relevance": rafael_relevance.value or "",
                "practical_examples": practical_examples.value or "Unknown",
                "evidence_quality": evidence_quality.value or "Unknown",
                "specificity": specificity.value or "Unknown",
                "hype_risk": hype_risk.value or "Unknown",
                "rafael_fit": rafael_fit.value or "Unknown",
            }

        def apply_project_defaults(overwrite: bool = False) -> None:
            defaults = infer_profile_defaults(selected_project_data(), profile_payload())
            controls = [
                (source_name, "source_name"),
                (topic, "topic"),
                (target_audience, "target_audience"),
                (credibility_notes, "credibility_notes"),
                (rafael_relevance, "rafael_relevance"),
            ]
            for control, key in controls:
                if overwrite or not str(control.value or "").strip():
                    control.value = defaults.get(key, "")
                    control.update()
            if overwrite or source_type.value == "Unknown":
                inferred_source_type = defaults.get("source_type", "Unknown")
                source_type.value = inferred_source_type if inferred_source_type in EXPERT_SOURCE_TYPES else "Unknown"
                source_type.update()
            if overwrite or business_type.value == "Unknown":
                inferred_business_type = defaults.get("business_type", "Unknown")
                business_type.value = inferred_business_type if inferred_business_type in BUSINESS_TYPES else "Unknown"
                business_type.update()
            generate_prompt()

        def generate_prompt() -> None:
            prompt = generate_expert_prompt(selected_project_data(), profile_payload(), mode.value or "Both", notes.value or "")
            prompt_output.value = prompt
            prompt_output.update()
            prompt_status.text = f"Generated | {len(prompt):,} characters | mode: {mode.value}"
            prompt_status.update()

        def copy_prompt() -> None:
            text = prompt_output.value or ""
            if not text:
                ui.notify("Generate a prompt first", type="warning")
                return
            safe = text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
            ui.run_javascript(f"navigator.clipboard.writeText(`{safe}`)")
            ui.notify("Prompt copied", type="positive")

        def save_prompt_file() -> None:
            text = prompt_output.value or ""
            if not text:
                ui.notify("Generate a prompt first", type="warning")
                return
            path = save_expert_prompt(text, state.downloads_dir, source_name.value or "expert", mode.value or "Both")
            ui.notify(f"Saved: {path}", type="positive")
            open_path(path)

        def save_profile_action() -> None:
            payload = profile_payload()
            if not str(payload.get("source_name") or "").strip():
                ui.notify("Enter an expert/channel/source name first", type="warning")
                return
            saved = save_expert_profile(state.project_root_path, payload)
            ui.notify(f"Saved profile: {saved.get('source_name')}", type="positive")
            render_profiles()

        def reset_profile() -> None:
            source_name.value = ""
            topic.value = ""
            target_audience.value = ""
            credibility_notes.value = ""
            rafael_relevance.value = ""
            for control in [source_name, topic, target_audience, credibility_notes, rafael_relevance]:
                control.update()
            source_type.value = "Unknown"
            business_type.value = "Unknown"
            for control in [source_type, business_type]:
                control.update()
            apply_project_defaults(overwrite=True)
            ui.notify("Profile form reset to project defaults", type="positive")

        def render_profiles() -> None:
            profiles_container.clear()
            profiles = load_expert_profiles(state.project_root_path)
            with profiles_container:
                if not profiles:
                    ui.label("No expert profiles saved yet.").classes("text-slate-400")
                    return
                for row in list(reversed(profiles))[:20]:
                    with ui.card().classes("ytis-mini-card p-4 w-full"):
                        with ui.row().classes("w-full justify-between items-start gap-3 ytis-card-row"):
                            with ui.column().classes("gap-1"):
                                ui.label(row.get("source_name", "-")).classes("font-bold")
                                ui.label(f"Topic: {row.get('topic', '-')} | Type: {row.get('source_type', '-')}").classes("text-sm text-slate-300")
                                ui.label(f"Project: {row.get('project', '-')}").classes("text-xs text-slate-500")
                            with ui.column().classes("gap-1 items-end"):
                                ui.badge(f"Fit: {row.get('rafael_fit', '-')}", color="blue")
                                ui.badge(f"Hype: {row.get('hype_risk', '-')}", color="orange")

        selected_project.on("update:model-value", lambda e: apply_project_defaults(overwrite=True))
        for control in [source_name, source_type, topic, business_type, target_audience, mode, notes]:
            control.on("update:model-value", lambda e: generate_prompt())
        credibility_notes.on("blur", lambda e: generate_prompt())
        rafael_relevance.on("blur", lambda e: generate_prompt())
        for control in [practical_examples, evidence_quality, specificity, hype_risk, rafael_fit]:
            control.on("update:model-value", lambda e: generate_prompt())

        generate_button.on("click", generate_prompt)
        copy_button.on("click", copy_prompt)
        save_prompt_button.on("click", save_prompt_file)
        save_profile_button.on("click", save_profile_action)
        apply_defaults_button.on("click", lambda: (apply_project_defaults(overwrite=True), ui.notify("Project defaults applied", type="positive")))
        reset_button.on("click", reset_profile)
        refresh_profiles_button.on("click", render_profiles)

        generate_prompt()
        render_profiles()


def metric_card(label: str, value: str, caption: str) -> None:
    with ui.card().classes("ytis-metric p-4"):
        ui.label(label).classes("text-sm text-slate-400")
        ui.label(value).classes("text-2xl font-bold")
        ui.label(caption).classes("text-xs text-slate-500")
