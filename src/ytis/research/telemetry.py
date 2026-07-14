from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypeAlias


@dataclass(frozen=True)
class ProviderExecutionEvent:
    """Non-sensitive metadata emitted after a finding-provider execution."""

    provider_name: str
    outcome: Literal["success", "failure"]
    duration_ms: float
    evidence_count: int
    finding_count: int
    error_type: str | None = None

    def __post_init__(self) -> None:
        if not self.provider_name.strip():
            raise ValueError("provider_name cannot be blank")
        if self.duration_ms < 0:
            raise ValueError("duration_ms cannot be negative")
        if self.evidence_count < 0 or self.finding_count < 0:
            raise ValueError("telemetry counts cannot be negative")
        if self.outcome == "success" and self.error_type is not None:
            raise ValueError("successful events cannot include an error type")
        if self.outcome == "failure" and not self.error_type:
            raise ValueError("failed events require an error type")


ProviderExecutionObserver: TypeAlias = Callable[[ProviderExecutionEvent], None]
