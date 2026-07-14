from __future__ import annotations

from nicegui import ui

from ytis.research import JsonlProviderTelemetryStore, summarize_provider_telemetry


def render_provider_telemetry_panel(store: JsonlProviderTelemetryStore) -> None:
    """Render privacy-safe local execution metadata with explicit manual refresh."""

    summary_container = ui.column().classes("w-full gap-3")

    def refresh() -> None:
        summary_container.clear()
        try:
            events = store.read(skip_invalid=True)
            summary = summarize_provider_telemetry(events, recent_limit=5)
        except Exception as exc:
            with summary_container:
                ui.label("Telemetry summary unavailable").classes("text-red-300 font-bold")
                ui.label(type(exc).__name__).classes("text-xs text-slate-400")
            return

        with summary_container:
            with ui.grid(columns=4).classes("w-full gap-3"):
                _metric("Executions", str(summary.total_executions), "telemetry-total")
                _metric("Success rate", f"{summary.success_rate * 100:.1f}%", "telemetry-success-rate")
                _metric("Average duration", f"{summary.average_duration_ms:.1f} ms", "telemetry-average-duration")
                _metric("Findings", str(summary.total_findings), "telemetry-total-findings")

            if summary.providers:
                ui.label("Provider breakdown").classes("text-sm font-bold text-slate-300")
                for provider in summary.providers:
                    ui.label(
                        f"{provider.provider_name} · {provider.executions} executions · "
                        f"{provider.successes} success · {provider.failures} failure · "
                        f"{provider.average_duration_ms:.1f} ms average"
                    ).classes("text-xs text-slate-400").props("data-testid=telemetry-provider-row")
            else:
                ui.label("No provider executions recorded yet.").classes("text-sm text-slate-400").props(
                    "data-testid=telemetry-empty"
                )

            if summary.recent_events:
                ui.label("Recent executions").classes("text-sm font-bold text-slate-300")
                for event in reversed(summary.recent_events):
                    suffix = f" · {event.error_type}" if event.error_type else ""
                    ui.label(
                        f"{event.provider_name} · {event.outcome} · {event.duration_ms:.1f} ms · "
                        f"{event.evidence_count} evidence · {event.finding_count} findings{suffix}"
                    ).classes("text-xs text-slate-400").props("data-testid=telemetry-recent-row")

    with ui.column().classes("ytis-page gap-4"):
        with ui.card().classes("ytis-card p-4 w-full").props("data-testid=telemetry-panel"):
            with ui.row().classes("w-full justify-between items-center gap-3"):
                with ui.column().classes("gap-0"):
                    ui.label("Provider execution telemetry").classes("text-xl font-bold")
                    ui.label(
                        "Read-only local metadata. No prompts, source text, findings, responses, or exception messages."
                    ).classes("text-xs text-slate-400")
                ui.button("Refresh", icon="refresh", on_click=refresh).props(
                    "outline dense data-testid=refresh-telemetry"
                )
            refresh()


def _metric(label: str, value: str, test_id: str) -> None:
    with ui.card().classes("p-3"):
        ui.label(label).classes("text-xs text-slate-400")
        ui.label(value).classes("text-lg font-bold").props(f"data-testid={test_id}")
