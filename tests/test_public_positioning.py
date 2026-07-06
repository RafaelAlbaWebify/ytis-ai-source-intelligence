from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

def check(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig").lower()

readme = read("README.md")
check("your technical intelligence system" in readme, "README missing YTIS expanded name")
check("aide" in readme, "README missing AIDE")
check("ai developer" in readme, "README missing AI Developer")
check("source intelligence" in readme, "README missing source intelligence")
check("youtube intelligence system" not in readme, "README still has old YouTube-only name")
for rel in ["docs/safety-boundaries.md", "docs/roadmap.md", "docs/sample-workflow.md", "docs/github-publication-checklist.md"]:
    check((ROOT / rel).exists(), f"Missing required doc: {rel}")
    if (ROOT / rel).exists():
        check("c:\\users\\ralba" not in read(rel), f"Local user path found in {rel}")

print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
sys.exit(0 if not errors else 1)
