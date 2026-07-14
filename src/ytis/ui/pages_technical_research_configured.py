from __future__ import annotations

from collections.abc import Callable

from nicegui import ui

from ytis.research import (
    ProviderConfigurationError,
    ResearchProviderSettings,
    TechnicalResearchService,
    build_finding_provider,
)
from ytis.ui.layout import NAV_GROUPS, NAV_ITEMS, render_shell
from ytis.ui.pages_technical_research import render_technical_research
from ytis.ui.state import AppState

_ROUTE = "/technical-research"
_NAV_ITEM = ("Technical Research", _ROUTE, "science")


def _register_navigation() -> None:
    if _NAV_ITEM in NAV_ITEMS:
        return
    for group_name, items in NAV_GROUPS:
        if group_name == "Evidence":
            items.insert(0, _NAV_ITEM)
            break
    else:
        NAV_GROUPS.append(("Evidence", [_NAV_ITEM]))
    NAV_ITEMS.insert(
        next((index for index, item in enumerate(NAV_ITEMS) if item[1] == "/search"), len(NAV_ITEMS)),
        _NAV_ITEM,
    )


def register_configured_technical_research_page(
    *,
    app_version: str,
    structured_generator: Callable[[str], str] | None = None,
) -> None:
    """Register the workbench with explicit provider construction and fail-closed guards."""

    _register_navigation()
    state = AppState(app_version=app_version)

    @ui.page(_ROUTE)
    def technical_research_page() -> None:
        try:
            settings = ResearchProviderSettings.from_environment()
            provider = build_finding_provider(
                settings,
                structured_generator=structured_generator,
            )
        except ProviderConfigurationError as exc:
            render_shell(state, _ROUTE)
            with ui.column().classes("ytis-page gap-4"):
                ui.label("Technical Research Workbench").classes("text-3xl font-bold")
                ui.badge("Provider unavailable", color="negative").props(
                    "outline data-testid=provider-unavailable"
                )
                with ui.card().classes("ytis-card p-4 w-full"):
                    ui.label("Research provider configuration is incomplete").classes(
                        "text-xl font-bold text-red-300"
                    )
                    ui.label(str(exc)).classes("text-sm text-slate-300").props(
                        "data-testid=provider-configuration-error"
                    )
                    ui.label(
                        "YTIS has not started a structured provider. Return to deterministic mode "
                        "or inject a generator explicitly in application code."
                    ).classes("text-sm text-slate-400")
            return

        service = TechnicalResearchService(provider=provider)
        render_technical_research(
            state,
            service=service,
            provider_label=f"Active provider: {service.provider_name}",
        )
