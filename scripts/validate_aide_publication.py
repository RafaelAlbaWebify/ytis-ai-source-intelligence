from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "docs/safety-boundaries.md",
    "docs/roadmap.md",
    "docs/sample-workflow.md",
    "docs/github-publication-checklist.md",
    "src/ytis/app.py",
]

PUBLIC_SCAN_PATHS = ["README.md", "docs", "src/ytis"]
FORBIDDEN_PATTERNS = [
    r"guarantee[s]?\s+(revenue|income|accuracy|results)",
    r"fully\s+autonomous\s+ai\s+agent",
    r"replace[s]?\s+human\s+review",
    r"bypass(es|ing)?\s+(paywalls?|captcha|login)",
    r"scrape[s]?\s+private\s+content",
    r"production\s+mlops\s+platform",
    r"black[- ]box\s+recommender",
]
GENERATED_TRACKED_PREFIXES = (
    "analysis_results/",
    "knowledge_cards/",
    "missions/",
    "missions_deleted/",
    "ytis_state/",
    "projects/",
    "exports/",
    "patch_backup_",
    ".venv/",
    "node_modules/",
)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def public_files() -> list[Path]:
    out: list[Path] = []
    for rel in PUBLIC_SCAN_PATHS:
        p = ROOT / rel
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            for child in p.rglob("*"):
                if child.is_file() and child.suffix.lower() in {".md", ".py", ".ps1", ".txt", ".json"}:
                    if child.name == "validate_aide_publication.py":
                        continue
                    out.append(child)
    return sorted(set(out))


def git_ls_files() -> list[str]:
    result = subprocess.run(["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return []
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"missing required file: {rel}")

    readme_path = ROOT / "README.md"
    readme = read_text(readme_path).lower() if readme_path.exists() else ""
    for phrase in ["your technical intelligence system", "aide", "ai developer", "local-first", "source intelligence", "chatgpt"]:
        if phrase not in readme:
            errors.append(f"README missing phrase: {phrase}")
    if "youtube intelligence system" in readme:
        errors.append("README still says YouTube Intelligence System")

    for file_path in public_files():
        rel = file_path.relative_to(ROOT).as_posix()
        text = read_text(file_path).lower()
        if "c:\\users\\ralba" in text:
            errors.append(f"local user path found in: {rel}")
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text):
                errors.append(f"unsafe or overclaim pattern in {rel}: {pattern}")

    tracked = git_ls_files()
    generated = [path for path in tracked if path.startswith(GENERATED_TRACKED_PREFIXES)]
    if generated:
        errors.append("generated/local files tracked: " + ", ".join(generated[:25]))
        if len(generated) > 25:
            errors.append(f"generated/local tracked count: {len(generated)}")

    result = {"ok": not errors, "errors": errors, "warnings": warnings, "tracked_file_count": len(tracked)}
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
