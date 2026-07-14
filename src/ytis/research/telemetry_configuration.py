from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path

from ytis.research.telemetry import ProviderExecutionObserver
from ytis.research.telemetry_store import JsonlProviderTelemetryStore


class TelemetryConfigurationError(ValueError):
    """Raised when provider telemetry configuration is invalid."""


def build_provider_telemetry_observer(
    *,
    storage_root: Path,
    environment: Mapping[str, str] | None = None,
) -> ProviderExecutionObserver | None:
    """Build an explicitly enabled local observer; telemetry is off by default."""

    values = os.environ if environment is None else environment
    mode = values.get("YTIS_RESEARCH_TELEMETRY", "off").strip().lower()
    if mode == "off":
        return None
    if mode != "local-jsonl":
        raise TelemetryConfigurationError(
            "YTIS_RESEARCH_TELEMETRY must be 'off' or 'local-jsonl'"
        )

    store = JsonlProviderTelemetryStore(storage_root / "telemetry" / "provider-executions.jsonl")
    return store.append
