from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ytis.research.telemetry import ProviderExecutionEvent


@dataclass(frozen=True)
class ProviderTelemetryBreakdown:
    provider_name: str
    executions: int
    successes: int
    failures: int
    average_duration_ms: float


@dataclass(frozen=True)
class ProviderTelemetrySummary:
    total_executions: int
    successes: int
    failures: int
    success_rate: float
    average_duration_ms: float
    maximum_duration_ms: float
    total_evidence: int
    total_findings: int
    providers: tuple[ProviderTelemetryBreakdown, ...]
    failure_types: tuple[tuple[str, int], ...]
    recent_events: tuple[ProviderExecutionEvent, ...]


def summarize_provider_telemetry(
    events: list[ProviderExecutionEvent],
    *,
    recent_limit: int = 10,
) -> ProviderTelemetrySummary:
    """Aggregate validated provider metadata without introducing content fields."""

    if recent_limit < 0:
        raise ValueError("recent_limit cannot be negative")

    total = len(events)
    successes = sum(event.outcome == "success" for event in events)
    failures = total - successes
    durations = [event.duration_ms for event in events]

    by_provider: dict[str, list[ProviderExecutionEvent]] = {}
    for event in events:
        by_provider.setdefault(event.provider_name, []).append(event)

    provider_breakdowns = tuple(
        ProviderTelemetryBreakdown(
            provider_name=provider_name,
            executions=len(provider_events),
            successes=sum(event.outcome == "success" for event in provider_events),
            failures=sum(event.outcome == "failure" for event in provider_events),
            average_duration_ms=(
                sum(event.duration_ms for event in provider_events) / len(provider_events)
            ),
        )
        for provider_name, provider_events in sorted(by_provider.items())
    )

    failure_counts = Counter(
        event.error_type
        for event in events
        if event.outcome == "failure" and event.error_type is not None
    )
    recent_events = tuple(events[-recent_limit:]) if recent_limit else ()

    return ProviderTelemetrySummary(
        total_executions=total,
        successes=successes,
        failures=failures,
        success_rate=(successes / total) if total else 0.0,
        average_duration_ms=(sum(durations) / total) if total else 0.0,
        maximum_duration_ms=max(durations, default=0.0),
        total_evidence=sum(event.evidence_count for event in events),
        total_findings=sum(event.finding_count for event in events),
        providers=provider_breakdowns,
        failure_types=tuple(sorted(failure_counts.items())),
        recent_events=recent_events,
    )
