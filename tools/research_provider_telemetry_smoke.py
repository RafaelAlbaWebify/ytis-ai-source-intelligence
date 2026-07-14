from __future__ import annotations

import json
import sys
from dataclasses import asdict, fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "research-provider-telemetry"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import ProviderExecutionEvent, SourceDocument, TechnicalResearchService


class FailingProvider:
    provider_name = "failing-fixture"

    def generate_findings(self, *, question: str, evidence: list) -> list:
        del question, evidence
        raise RuntimeError("SECRET prompt and source content must never enter telemetry")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    source = SourceDocument(
        source_id="telemetry-source",
        title="Telemetry fixture",
        content="The platform supports privacy-safe execution metadata.",
    )

    success_events: list[ProviderExecutionEvent] = []
    ticks = iter([1_000_000_000, 1_012_500_000])
    success = TechnicalResearchService(
        execution_observer=success_events.append,
        clock_ns=lambda: next(ticks),
    )
    investigation = success.create_investigation(
        investigation_id="telemetry-success",
        title="Telemetry success",
        question="What capability is stated?",
        sources=[source],
    )

    failure_events: list[ProviderExecutionEvent] = []
    failure_ticks = iter([2_000_000_000, 2_007_000_000])
    try:
        TechnicalResearchService(
            provider=FailingProvider(),
            execution_observer=failure_events.append,
            clock_ns=lambda: next(failure_ticks),
        ).create_investigation(
            investigation_id="telemetry-failure",
            title="Telemetry failure",
            question="This question is sensitive",
            sources=[source],
        )
        failure_raised = False
    except RuntimeError:
        failure_raised = True

    observer_failure_ignored = True
    try:
        TechnicalResearchService(
            execution_observer=lambda _event: (_ for _ in ()).throw(RuntimeError("observer failed")),
            clock_ns=iter([3_000_000_000, 3_001_000_000]).__next__,
        ).create_investigation(
            investigation_id="telemetry-observer",
            title="Observer isolation",
            question="What capability is stated?",
            sources=[source],
        )
    except Exception:
        observer_failure_ignored = False

    success_event = success_events[0]
    failure_event = failure_events[0]
    serialized = json.dumps([asdict(success_event), asdict(failure_event)], sort_keys=True)
    allowed_fields = {
        "provider_name",
        "outcome",
        "duration_ms",
        "evidence_count",
        "finding_count",
        "error_type",
    }
    checks = {
        "success_event_emitted": len(success_events) == 1 and success_event.outcome == "success",
        "success_counts_recorded": success_event.evidence_count == len(investigation.evidence)
        and success_event.finding_count == len(investigation.findings),
        "success_duration_recorded": success_event.duration_ms == 12.5,
        "failure_re_raised": failure_raised,
        "failure_event_emitted": len(failure_events) == 1 and failure_event.outcome == "failure",
        "failure_type_only": failure_event.error_type == "RuntimeError",
        "failure_duration_recorded": failure_event.duration_ms == 7.0,
        "observer_failure_isolated": observer_failure_ignored,
        "event_schema_allowlisted": {item.name for item in fields(ProviderExecutionEvent)} == allowed_fields,
        "no_source_content": source.content not in serialized,
        "no_question_content": "This question is sensitive" not in serialized,
        "no_exception_message": "SECRET" not in serialized,
    }
    report = {"ok": all(checks.values()), "checks": checks, "events": json.loads(serialized)}
    (OUT / "provider-telemetry-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
