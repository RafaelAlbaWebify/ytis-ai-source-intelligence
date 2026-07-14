from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import os

from ytis.research.providers import DeterministicFindingProvider, FindingProvider
from ytis.research.structured_provider import StructuredJsonFindingProvider


class ProviderConfigurationError(ValueError):
    """Raised when research-provider configuration is invalid or incomplete."""


@dataclass(frozen=True)
class ResearchProviderSettings:
    mode: str = "deterministic"
    provider_name: str = "structured-json"
    max_findings: int = 25

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> "ResearchProviderSettings":
        values = os.environ if environment is None else environment
        mode = values.get("YTIS_RESEARCH_PROVIDER", "deterministic").strip().lower()
        if mode not in {"deterministic", "structured-json"}:
            raise ProviderConfigurationError(
                "YTIS_RESEARCH_PROVIDER must be 'deterministic' or 'structured-json'"
            )

        provider_name = values.get("YTIS_RESEARCH_PROVIDER_NAME", "structured-json").strip()
        if not provider_name:
            raise ProviderConfigurationError("YTIS_RESEARCH_PROVIDER_NAME cannot be empty")

        raw_max = values.get("YTIS_RESEARCH_MAX_FINDINGS", "25").strip()
        try:
            max_findings = int(raw_max)
        except ValueError as exc:
            raise ProviderConfigurationError(
                "YTIS_RESEARCH_MAX_FINDINGS must be an integer"
            ) from exc
        if not 1 <= max_findings <= 100:
            raise ProviderConfigurationError(
                "YTIS_RESEARCH_MAX_FINDINGS must be between 1 and 100"
            )

        return cls(
            mode=mode,
            provider_name=provider_name,
            max_findings=max_findings,
        )


def build_finding_provider(
    settings: ResearchProviderSettings,
    *,
    structured_generator: Callable[[str], str] | None = None,
) -> FindingProvider:
    if settings.mode == "deterministic":
        if structured_generator is not None:
            raise ProviderConfigurationError(
                "structured_generator must not be supplied in deterministic mode"
            )
        return DeterministicFindingProvider()

    if settings.mode == "structured-json":
        if structured_generator is None:
            raise ProviderConfigurationError(
                "structured-json mode requires an explicitly injected generator"
            )
        return StructuredJsonFindingProvider(
            generator=structured_generator,
            provider_name=settings.provider_name,
            max_findings=settings.max_findings,
        )

    raise ProviderConfigurationError(f"unsupported provider mode: {settings.mode}")
