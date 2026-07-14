from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "research-provider-configuration"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import (
    DeterministicFindingProvider,
    ProviderConfigurationError,
    ResearchProviderSettings,
    StructuredJsonFindingProvider,
    build_finding_provider,
)


def expect_configuration_error(action) -> bool:
    try:
        action()
    except ProviderConfigurationError:
        return True
    return False


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    checks: dict[str, bool] = {}

    default_settings = ResearchProviderSettings.from_environment({})
    default_provider = build_finding_provider(default_settings)
    checks["default_mode_is_deterministic"] = default_settings.mode == "deterministic"
    checks["default_provider_is_deterministic"] = isinstance(
        default_provider, DeterministicFindingProvider
    )
    checks["default_provider_name_preserved"] = (
        default_provider.provider_name == "deterministic-rules"
    )

    structured_settings = ResearchProviderSettings.from_environment(
        {
            "YTIS_RESEARCH_PROVIDER": " structured-json ",
            "YTIS_RESEARCH_PROVIDER_NAME": "offline-fake-model",
            "YTIS_RESEARCH_MAX_FINDINGS": "12",
        }
    )
    prompts: list[str] = []

    def generator(prompt: str) -> str:
        prompts.append(prompt)
        return '{"findings": []}'

    structured_provider = build_finding_provider(
        structured_settings,
        structured_generator=generator,
    )
    checks["structured_mode_parsed"] = structured_settings.mode == "structured-json"
    checks["structured_name_parsed"] = structured_settings.provider_name == "offline-fake-model"
    checks["structured_limit_parsed"] = structured_settings.max_findings == 12
    checks["structured_provider_built"] = isinstance(
        structured_provider, StructuredJsonFindingProvider
    )
    checks["structured_provider_name_applied"] = (
        structured_provider.provider_name == "offline-fake-model"
    )

    checks["invalid_mode_rejected"] = expect_configuration_error(
        lambda: ResearchProviderSettings.from_environment(
            {"YTIS_RESEARCH_PROVIDER": "automatic"}
        )
    )
    checks["empty_provider_name_rejected"] = expect_configuration_error(
        lambda: ResearchProviderSettings.from_environment(
            {
                "YTIS_RESEARCH_PROVIDER": "structured-json",
                "YTIS_RESEARCH_PROVIDER_NAME": "   ",
            }
        )
    )
    checks["non_integer_limit_rejected"] = expect_configuration_error(
        lambda: ResearchProviderSettings.from_environment(
            {"YTIS_RESEARCH_MAX_FINDINGS": "many"}
        )
    )
    checks["zero_limit_rejected"] = expect_configuration_error(
        lambda: ResearchProviderSettings.from_environment(
            {"YTIS_RESEARCH_MAX_FINDINGS": "0"}
        )
    )
    checks["excessive_limit_rejected"] = expect_configuration_error(
        lambda: ResearchProviderSettings.from_environment(
            {"YTIS_RESEARCH_MAX_FINDINGS": "101"}
        )
    )
    checks["structured_mode_requires_injected_generator"] = expect_configuration_error(
        lambda: build_finding_provider(structured_settings)
    )
    checks["deterministic_mode_rejects_generator"] = expect_configuration_error(
        lambda: build_finding_provider(default_settings, structured_generator=generator)
    )
    checks["configuration_contains_no_secret_fields"] = set(
        ResearchProviderSettings.__dataclass_fields__
    ) == {"mode", "provider_name", "max_findings"}
    checks["generator_not_called_during_configuration"] = prompts == []

    report = {
        "ok": all(checks.values()),
        "checks": checks,
        "default": {
            "mode": default_settings.mode,
            "provider_name": default_provider.provider_name,
        },
        "structured": {
            "mode": structured_settings.mode,
            "provider_name": structured_provider.provider_name,
            "max_findings": structured_settings.max_findings,
        },
    }
    (OUT / "provider-configuration-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    lines = [
        "# Research Provider Configuration Report",
        "",
        f"- Overall: {'PASS' if report['ok'] else 'FAIL'}",
        "",
        "## Checks",
        "",
    ]
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} `{name}`"
        for name, passed in checks.items()
    )
    (OUT / "provider-configuration-report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
