from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "publication-readiness"

REQUIRED_FILES = (
    "README.md",
    "docs/roadmap.md",
    "docs/safety-boundaries.md",
    "docs/public-demo.md",
    "docs/publication-review.md",
    "docs/visual-system.md",
    "src/ytis/ui/trace_visual_system.py",
    "src/ytis/ui/pages_start_here.py",
    "examples/portfolio-investigation/README.md",
    "examples/portfolio-investigation/investigation.json",
    "examples/portfolio-investigation/insight-card.json",
    "examples/portfolio-investigation/source-credibility.md",
    "examples/portfolio-investigation/business-model.md",
    "examples/portfolio-investigation/technical-lessons.md",
    "examples/portfolio-investigation/learning-roadmap.md",
    "examples/portfolio-investigation/opportunity-analysis.md",
)

REQUIRED_WORKFLOWS = (
    ".github/workflows/baseline-ci.yml",
    ".github/workflows/playwright-route-smoke.yml",
    ".github/workflows/playwright-navigation-interaction.yml",
    ".github/workflows/playwright-start-here.yml",
    ".github/workflows/playwright-technical-research.yml",
    ".github/workflows/playwright-multi-source-workbench.yml",
    ".github/workflows/playwright-source-pack-editing.yml",
    ".github/workflows/playwright-reusable-outputs.yml",
    ".github/workflows/playwright-local-import-and-cards.yml",
    ".github/workflows/playwright-structured-provider.yml",
    ".github/workflows/playwright-provider-configuration-guard.yml",
    ".github/workflows/playwright-local-telemetry.yml",
    ".github/workflows/playwright-public-demo.yml",
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    missing_files = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    missing_workflows = [path for path in REQUIRED_WORKFLOWS if not (ROOT / path).is_file()]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    review = (ROOT / "docs" / "publication-review.md").read_text(encoding="utf-8")
    safety = (ROOT / "docs" / "safety-boundaries.md").read_text(encoding="utf-8")
    visual = (ROOT / "docs" / "visual-system.md").read_text(encoding="utf-8")
    theme = (ROOT / "src" / "ytis" / "ui" / "trace_visual_system.py").read_text(encoding="utf-8")
    start_proof = (ROOT / "tools" / "playwright_start_here.py").read_text(encoding="utf-8")

    forbidden_tracked_names = {".env", "credentials.json", "secrets.json", "token.json"}
    forbidden_present = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*")
        if path.is_file() and path.name.lower() in forbidden_tracked_names
    ]

    checks = {
        "required_portfolio_files_present": not missing_files,
        "required_workflows_present": not missing_workflows,
        "readme_links_portfolio_example": "examples/portfolio-investigation/" in readme,
        "readme_links_start_here": "/start" in readme,
        "readme_states_human_review": "Human review is always required" in readme,
        "publication_review_blocks_steps_none": "steps: None" in review,
        "publication_review_requires_same_commit_screenshots": "same commit that is merged" in review,
        "safety_boundary_exists": bool(safety.strip()),
        "visual_contract_names_trace": "TRACE operational interface" in visual,
        "visual_contract_rejects_neon": "neon glow" in visual,
        "theme_uses_light_canvas": "#f6f8fb" in theme,
        "theme_uses_trace_navy": "#071a33" in theme and "#0b2342" in theme,
        "browser_checks_visual_contract": "light_operational_canvas" in start_proof
        and "trace_navy_sidebar" in start_proof,
        "no_obvious_secret_files": not forbidden_present,
    }
    result = {
        "ok": all(checks.values()),
        "checks": checks,
        "missing_files": missing_files,
        "missing_workflows": missing_workflows,
        "forbidden_present": forbidden_present,
    }
    (OUT / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
