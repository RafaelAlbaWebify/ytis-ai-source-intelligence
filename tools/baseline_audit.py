from __future__ import annotations

import importlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def run_command(name: str, command: list[str], env: dict[str, str] | None = None) -> CheckResult:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    detail = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part)
    return CheckResult(name=name, ok=completed.returncode == 0, detail=detail or f"exit={completed.returncode}")


def import_check(module_name: str) -> CheckResult:
    try:
        importlib.import_module(module_name)
    except Exception as exc:  # diagnostic boundary: preserve the real exception
        return CheckResult(name=f"import:{module_name}", ok=False, detail=f"{type(exc).__name__}: {exc}")
    return CheckResult(name=f"import:{module_name}", ok=True, detail="import succeeded")


def inventory() -> dict[str, Any]:
    files = [path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts]
    python_files = [path for path in files if path.suffix == ".py"]
    return {
        "file_count": len(files),
        "python_file_count": len(python_files),
        "top_level": sorted(path.name for path in ROOT.iterdir() if path.name != ".git"),
        "python_files": sorted(str(path.relative_to(ROOT)).replace("\\", "/") for path in python_files),
    }


def main() -> int:
    output_dir = ROOT / "artifacts" / "baseline"
    output_dir.mkdir(parents=True, exist_ok=True)

    pythonpath = str(SRC)
    env = os.environ.copy()
    env["PYTHONPATH"] = pythonpath + os.pathsep + env.get("PYTHONPATH", "")
    if pythonpath not in sys.path:
        sys.path.insert(0, pythonpath)

    checks = [
        run_command("pip-check", [sys.executable, "-m", "pip", "check"], env),
        run_command("compileall", [sys.executable, "-m", "compileall", "-q", "src", "tests", "tools"], env),
        run_command("public-positioning", [sys.executable, "tests/test_public_positioning.py"], env),
        import_check("ytis.app"),
    ]

    report = {
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "inventory": inventory(),
        "checks": [asdict(check) for check in checks],
        "ok": all(check.ok for check in checks),
    }

    json_path = output_dir / "baseline-report.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# YTIS Baseline Audit",
        "",
        f"Overall: {'PASS' if report['ok'] else 'FAIL'}",
        "",
        "## Checks",
        "",
    ]
    for check in checks:
        lines.extend([
            f"### {'PASS' if check.ok else 'FAIL'} — {check.name}",
            "",
            "```text",
            check.detail,
            "```",
            "",
        ])
    (output_dir / "baseline-report.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
