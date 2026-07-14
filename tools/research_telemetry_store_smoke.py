from __future__ import annotations

import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "research-telemetry-store"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import JsonlProviderTelemetryStore, ProviderExecutionEvent, TelemetryRecordError


SENSITIVE_MARKERS = {
    "SECRET_SOURCE_CONTENT",
    "SECRET_RESEARCH_QUESTION",
    "SECRET_PROVIDER_RESPONSE",
    "SECRET_EXCEPTION_MESSAGE",
    "api-key-should-never-appear",
}


def expect_record_error(action) -> bool:
    try:
        action()
    except TelemetryRecordError:
        return True
    return False


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    path = OUT / "provider-executions.jsonl"
    store = JsonlProviderTelemetryStore(path)

    success = ProviderExecutionEvent(
        provider_name="deterministic-rules",
        outcome="success",
        duration_ms=12.5,
        evidence_count=4,
        finding_count=3,
    )
    failure = ProviderExecutionEvent(
        provider_name="ci-structured-fixture",
        outcome="failure",
        duration_ms=7.25,
        evidence_count=4,
        finding_count=0,
        error_type="RuntimeError",
    )
    store.append(success)
    store.append(failure)
    raw = path.read_text(encoding="utf-8")
    records = store.read()

    missing_store = JsonlProviderTelemetryStore(OUT / "missing" / "events.jsonl")
    checks = {
        "append_created_file": path.is_file(),
        "two_lines_written": len(raw.splitlines()) == 2,
        "round_trip_preserved": records == [success, failure],
        "tail_limit_returns_latest": store.read(limit=1) == [failure],
        "missing_file_is_empty": missing_store.read() == [],
        "allowlisted_keys_only": all(
            set(json.loads(line)) == set(asdict(success)) for line in raw.splitlines()
        ),
        "sensitive_markers_absent": not any(marker in raw for marker in SENSITIVE_MARKERS),
    }

    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"provider_name":"bad","outcome":"success","duration_ms":1,"evidence_count":1,"finding_count":1,"error_type":null,"extra":"SECRET_SOURCE_CONTENT"}\n')
    checks["extra_field_rejected"] = expect_record_error(store.read)
    checks["skip_invalid_recovers_valid"] = store.read(skip_invalid=True) == [success, failure]

    bad_types_path = OUT / "bad-types.jsonl"
    bad_types_path.write_text(
        '{"provider_name":"bad","outcome":"success","duration_ms":true,"evidence_count":1,"finding_count":1,"error_type":null}\n',
        encoding="utf-8",
    )
    checks["boolean_duration_rejected"] = expect_record_error(JsonlProviderTelemetryStore(bad_types_path).read)

    blank_path = OUT / "blank.jsonl"
    blank_path.write_text("\n", encoding="utf-8")
    checks["blank_record_rejected"] = expect_record_error(JsonlProviderTelemetryStore(blank_path).read)
    checks["invalid_limit_rejected"] = False
    try:
        store.read(limit=0)
    except ValueError:
        checks["invalid_limit_rejected"] = True

    report = {
        "ok": all(checks.values()),
        "checks": checks,
        "records": [asdict(item) for item in records],
        "path": str(path),
    }
    (OUT / "telemetry-store-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "telemetry-store-report.md").write_text(
        "# Research Telemetry Store Report\n\n"
        + f"- Overall: {'PASS' if report['ok'] else 'FAIL'}\n"
        + f"- Records: {len(records)}\n\n"
        + "## Checks\n\n"
        + "\n".join(f"- {'PASS' if value else 'FAIL'} `{name}`" for name, value in checks.items())
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
