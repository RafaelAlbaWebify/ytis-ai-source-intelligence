from __future__ import annotations

from dataclasses import fields
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "research-telemetry-summary"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import (
    ProviderExecutionEvent,
    ProviderTelemetryBreakdown,
    ProviderTelemetrySummary,
    summarize_provider_telemetry,
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    events = [
        ProviderExecutionEvent("provider-b", "success", 30.0, 3, 2),
        ProviderExecutionEvent("provider-a", "failure", 10.0, 2, 0, "TimeoutError"),
        ProviderExecutionEvent("provider-a", "success", 20.0, 4, 3),
        ProviderExecutionEvent("provider-b", "failure", 40.0, 1, 0, "TimeoutError"),
        ProviderExecutionEvent("provider-b", "failure", 50.0, 1, 0, "ValueError"),
    ]
    summary = summarize_provider_telemetry(events, recent_limit=2)
    empty = summarize_provider_telemetry([], recent_limit=0)

    summary_fields = {item.name for item in fields(ProviderTelemetrySummary)}
    breakdown_fields = {item.name for item in fields(ProviderTelemetryBreakdown)}
    forbidden_fragments = {"prompt", "source", "question", "evidence_text", "finding_text", "response", "message", "token", "credential"}

    checks = {
        "totals": summary.total_executions == 5 and summary.successes == 2 and summary.failures == 3,
        "success_rate": summary.success_rate == 0.4,
        "durations": summary.average_duration_ms == 30.0 and summary.maximum_duration_ms == 50.0,
        "aggregate_counts": summary.total_evidence == 11 and summary.total_findings == 5,
        "provider_order": tuple(item.provider_name for item in summary.providers) == ("provider-a", "provider-b"),
        "provider_a_breakdown": summary.providers[0] == ProviderTelemetryBreakdown("provider-a", 2, 1, 1, 15.0),
        "provider_b_breakdown": summary.providers[1] == ProviderTelemetryBreakdown("provider-b", 3, 1, 2, 40.0),
        "failure_types": summary.failure_types == (("TimeoutError", 2), ("ValueError", 1)),
        "recent_bounded": summary.recent_events == tuple(events[-2:]),
        "empty_summary": (
            empty.total_executions == 0
            and empty.success_rate == 0.0
            and empty.average_duration_ms == 0.0
            and empty.maximum_duration_ms == 0.0
            and empty.providers == ()
            and empty.recent_events == ()
        ),
        "summary_schema_safe": not any(fragment in name.lower() for name in summary_fields for fragment in forbidden_fragments),
        "breakdown_schema_safe": not any(fragment in name.lower() for name in breakdown_fields for fragment in forbidden_fragments),
    }

    try:
        summarize_provider_telemetry(events, recent_limit=-1)
        checks["negative_recent_limit_rejected"] = False
    except ValueError:
        checks["negative_recent_limit_rejected"] = True

    report = {
        "ok": all(checks.values()),
        "checks": checks,
        "summary_fields": sorted(summary_fields),
        "breakdown_fields": sorted(breakdown_fields),
        "provider_count": len(summary.providers),
    }
    (OUT / "summary-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "summary-report.md").write_text(
        "# Research Telemetry Summary Report\n\n"
        + f"- Overall: {'PASS' if report['ok'] else 'FAIL'}\n\n"
        + "## Checks\n\n"
        + "\n".join(f"- {'PASS' if value else 'FAIL'} `{name}`" for name, value in checks.items())
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
