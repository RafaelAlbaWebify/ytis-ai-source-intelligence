from __future__ import annotations

import ast
import importlib
import json
import os
import platform
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ARTIFACT_DIR = ROOT / "artifacts" / "architecture"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def module_name(path: Path) -> str:
    return ".".join(path.relative_to(SRC).with_suffix("").parts)


def import_modules(paths: list[Path]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in paths:
        name = module_name(path)
        try:
            importlib.import_module(name)
            results.append({"module": name, "ok": True, "error": ""})
        except Exception as exc:  # characterization must retain the real exception
            results.append({
                "module": name,
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            })
    return results


def count_broad_exception_handlers(path: Path) -> list[dict[str, Any]]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    findings: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        broad = node.type is None
        if isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}:
            broad = True
        if broad:
            findings.append({"path": path.relative_to(ROOT).as_posix(), "line": node.lineno})
    return findings


def main() -> int:
    core_paths = sorted((SRC / "ytis" / "core").glob("*.py"))
    ui_paths = sorted((SRC / "ytis" / "ui").glob("*.py"))
    imported = import_modules(core_paths + ui_paths)

    from ytis.ui.layout import NAV_ITEMS, ROUTE_ALIASES
    from ytis.ui.state import AppState

    routes = [path for _label, path, _icon in NAV_ITEMS]
    labels = [label for label, _path, _icon in NAV_ITEMS]
    duplicate_routes = sorted({route for route in routes if routes.count(route) > 1})
    duplicate_labels = sorted({label for label in labels if labels.count(label) > 1})

    state_error = ""
    state_ok = False
    with tempfile.TemporaryDirectory(prefix="ytis-characterization-") as temp_dir:
        base = Path(temp_dir)
        try:
            state = AppState(
                app_version="characterization",
                project_root_path=base,
                downloads_dir=base / "downloads",
            )
            state_ok = state.load_projects() == [] and state.current_project == {}
        except Exception as exc:
            state_error = f"{type(exc).__name__}: {exc}"

    broad_handlers: list[dict[str, Any]] = []
    for path in core_paths + ui_paths:
        broad_handlers.extend(count_broad_exception_handlers(path))

    failures = [item for item in imported if not item["ok"]]
    hard_errors: list[str] = []
    if failures:
        hard_errors.append(f"{len(failures)} module imports failed")
    if duplicate_routes:
        hard_errors.append(f"duplicate routes: {duplicate_routes}")
    if duplicate_labels:
        hard_errors.append(f"duplicate navigation labels: {duplicate_labels}")
    if not state_ok:
        hard_errors.append(f"AppState empty-state check failed: {state_error or 'unexpected state'}")

    report = {
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "ci": os.environ.get("CI", ""),
        },
        "modules": {
            "core_count": len(core_paths),
            "ui_count": len(ui_paths),
            "imported": imported,
            "failed_count": len(failures),
        },
        "navigation": {
            "item_count": len(NAV_ITEMS),
            "routes": routes,
            "aliases": ROUTE_ALIASES,
            "duplicate_routes": duplicate_routes,
            "duplicate_labels": duplicate_labels,
        },
        "state": {"empty_state_ok": state_ok, "error": state_error},
        "architecture_warnings": {
            "broad_exception_handler_count": len(broad_handlers),
            "broad_exception_handlers": broad_handlers,
        },
        "hard_errors": hard_errors,
        "ok": not hard_errors,
    }

    json_path = ARTIFACT_DIR / "architecture-characterization.json"
    md_path = ARTIFACT_DIR / "architecture-characterization.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# YTIS Architecture Characterization",
        "",
        f"Overall: {'PASS' if report['ok'] else 'FAIL'}",
        "",
        f"- Core modules discovered: {len(core_paths)}",
        f"- UI modules discovered: {len(ui_paths)}",
        f"- Module import failures: {len(failures)}",
        f"- Navigation items: {len(NAV_ITEMS)}",
        f"- Broad exception handlers: {len(broad_handlers)}",
        f"- Empty AppState check: {'PASS' if state_ok else 'FAIL'}",
        "",
        "## Routes",
        "",
    ]
    lines.extend(f"- `{route}`" for route in routes)
    lines.extend(["", "## Import failures", ""])
    if failures:
        lines.extend(f"- `{item['module']}` — {item['error']}" for item in failures)
    else:
        lines.append("None.")
    lines.extend(["", "## Architecture warnings", ""])
    if broad_handlers:
        lines.extend(
            f"- `{item['path']}:{item['line']}` uses a broad exception handler."
            for item in broad_handlers
        )
    else:
        lines.append("None detected.")
    lines.extend(["", "## Hard errors", ""])
    lines.extend(f"- {error}" for error in hard_errors) if hard_errors else lines.append("None.")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
