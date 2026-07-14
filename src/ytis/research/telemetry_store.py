from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from ytis.research.telemetry import ProviderExecutionEvent


class TelemetryRecordError(ValueError):
    """Raised when a persisted telemetry record is malformed or unsafe."""


class JsonlProviderTelemetryStore:
    """Append-only local store for privacy-safe provider execution metadata."""

    _FIELDS = {
        "provider_name",
        "outcome",
        "duration_ms",
        "evidence_count",
        "finding_count",
        "error_type",
    }

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: ProviderExecutionEvent) -> Path:
        payload = asdict(event)
        if set(payload) != self._FIELDS:
            raise TelemetryRecordError("telemetry event schema does not match the allowlist")
        line = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
            handle.write("\n")
            handle.flush()
        return self.path

    def read(self, *, limit: int | None = None, skip_invalid: bool = False) -> list[ProviderExecutionEvent]:
        if limit is not None and limit < 1:
            raise ValueError("limit must be at least 1")
        if not self.path.exists():
            return []

        events: list[ProviderExecutionEvent] = []
        for line_number, raw_line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw_line.strip():
                if skip_invalid:
                    continue
                raise TelemetryRecordError(f"line {line_number}: blank telemetry record")
            try:
                payload = json.loads(raw_line)
                event = self._decode(payload)
            except (json.JSONDecodeError, TypeError, ValueError, TelemetryRecordError) as exc:
                if skip_invalid:
                    continue
                raise TelemetryRecordError(f"line {line_number}: invalid telemetry record") from exc
            events.append(event)

        if limit is not None:
            return events[-limit:]
        return events

    @classmethod
    def _decode(cls, payload: Any) -> ProviderExecutionEvent:
        if not isinstance(payload, dict):
            raise TelemetryRecordError("telemetry record must be a JSON object")
        if set(payload) != cls._FIELDS:
            raise TelemetryRecordError("telemetry record keys do not match the allowlist")
        if not isinstance(payload["provider_name"], str):
            raise TelemetryRecordError("provider_name must be a string")
        if payload["outcome"] not in {"success", "failure"}:
            raise TelemetryRecordError("outcome must be success or failure")
        if isinstance(payload["duration_ms"], bool) or not isinstance(payload["duration_ms"], (int, float)):
            raise TelemetryRecordError("duration_ms must be numeric")
        for field in ("evidence_count", "finding_count"):
            if isinstance(payload[field], bool) or not isinstance(payload[field], int):
                raise TelemetryRecordError(f"{field} must be an integer")
        if payload["error_type"] is not None and not isinstance(payload["error_type"], str):
            raise TelemetryRecordError("error_type must be a string or null")
        return ProviderExecutionEvent(
            provider_name=payload["provider_name"],
            outcome=payload["outcome"],
            duration_ms=float(payload["duration_ms"]),
            evidence_count=payload["evidence_count"],
            finding_count=payload["finding_count"],
            error_type=payload["error_type"],
        )
