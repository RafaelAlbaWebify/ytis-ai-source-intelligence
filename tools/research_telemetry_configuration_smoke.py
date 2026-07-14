from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "research-telemetry-configuration"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import (
    ProviderExecutionEvent,
    TelemetryConfigurationError,
    build_provider_telemetry_observer,
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="ytis-telemetry-config-", dir=OUT))
    checks: dict[str, bool] = {}

    checks["default_is_off"] = build_provider_telemetry_observer(
        storage_root=root,
        environment={},
    ) is None
    checks["explicit_off_is_off"] = build_provider_telemetry_observer(
        storage_root=root,
        environment={"YTIS_RESEARCH_TELEMETRY": " OFF "},
    ) is None

    observer = build_provider_telemetry_observer(
        storage_root=root,
        environment={"YTIS_RESEARCH_TELEMETRY": "local-jsonl"},
    )
    checks["local_observer_created"] = observer is not None
    if observer is not None:
        observer(
            ProviderExecutionEvent(
                provider_name="configuration-proof",
                outcome="success",
                duration_ms=4.5,
                evidence_count=2,
                finding_count=1,
            )
        )

    telemetry_path = root / "telemetry" / "provider-executions.jsonl"
    persisted = telemetry_path.read_text(encoding="utf-8") if telemetry_path.exists() else ""
    checks["expected_path_used"] = telemetry_path.exists()
    checks["one_record_written"] = len([line for line in persisted.splitlines() if line]) == 1
    checks["no_file_created_when_off"] = not (root / "off.jsonl").exists()

    try:
        build_provider_telemetry_observer(
            storage_root=root,
            environment={"YTIS_RESEARCH_TELEMETRY": "remote"},
        )
        checks["invalid_mode_rejected"] = False
    except TelemetryConfigurationError:
        checks["invalid_mode_rejected"] = True

    report = {
        "ok": all(checks.values()),
        "checks": checks,
        "telemetry_path": str(telemetry_path),
    }
    (OUT / "telemetry-configuration-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
