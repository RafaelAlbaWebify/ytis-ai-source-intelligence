from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "playwright-navigation"
BASE_URL = os.environ.get("YTIS_BASE_URL", "http://127.0.0.1:8080")


def wait_for_server(timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    last_error = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE_URL, timeout=3) as response:
                if response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = str(exc)
        time.sleep(1)
    raise RuntimeError(f"YTIS did not become ready at {BASE_URL}: {last_error}")


def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=10)
    except Exception:
        process.kill()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / "navigation-interaction-report.json"
    report_md_path = OUT / "navigation-interaction-report.md"
    trace_path = OUT / "trace.zip"
    screenshot_path = OUT / "navigation-final.png"
    server_log_path = OUT / "server.log"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONUNBUFFERED"] = "1"

    server_log = server_log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-m", "ytis.app"],
        cwd=ROOT,
        env=env,
        stdout=server_log,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=os.name != "nt",
    )

    report: dict[str, Any] = {
        "ok": False,
        "base_url": BASE_URL,
        "interactions": [],
        "startup_error": "",
        "server_exit_code": None,
    }

    try:
        wait_for_server()
        if str(SRC) not in sys.path:
            sys.path.insert(0, str(SRC))

        from playwright.sync_api import sync_playwright
        from ytis.ui.layout import NAV_ITEMS

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()

            global_console_errors: list[str] = []
            global_page_errors: list[str] = []
            global_server_errors: list[str] = []
            page.on(
                "console",
                lambda message: global_console_errors.append(message.text)
                if message.type == "error"
                else None,
            )
            page.on("pageerror", lambda error: global_page_errors.append(str(error)))
            page.on(
                "response",
                lambda response: global_server_errors.append(f"{response.status} {response.url}")
                if response.status >= 500
                else None,
            )

            page.goto(BASE_URL, wait_until="networkidle", timeout=30_000)

            for label, route, _icon in NAV_ITEMS:
                before_console = len(global_console_errors)
                before_page = len(global_page_errors)
                before_server = len(global_server_errors)
                entry: dict[str, Any] = {
                    "label": label,
                    "expected_route": route,
                    "actual_path": "",
                    "active_count": 0,
                    "ok": False,
                    "error": "",
                    "console_errors": [],
                    "page_errors": [],
                    "server_errors": [],
                }
                try:
                    button = page.locator(".ytis-nav-expanded").get_by_role("button", name=label, exact=True)
                    button.wait_for(state="visible", timeout=10_000)
                    button.click()
                    expected_url = BASE_URL.rstrip("/") + route
                    page.wait_for_url(expected_url, timeout=15_000)
                    page.wait_for_load_state("networkidle", timeout=30_000)
                    entry["actual_path"] = page.url.replace(BASE_URL.rstrip("/"), "") or "/"
                    entry["active_count"] = page.locator(".ytis-nav-expanded .ytis-nav-active").count()
                    active_text = page.locator(".ytis-nav-expanded .ytis-nav-active").all_inner_texts()
                    entry["active_labels"] = [text.strip() for text in active_text]
                    entry["console_errors"] = global_console_errors[before_console:]
                    entry["page_errors"] = global_page_errors[before_page:]
                    entry["server_errors"] = global_server_errors[before_server:]
                    entry["ok"] = bool(
                        entry["actual_path"] == route
                        and entry["active_count"] == 1
                        and label in entry["active_labels"]
                        and not entry["console_errors"]
                        and not entry["page_errors"]
                        and not entry["server_errors"]
                    )
                except Exception as exc:
                    entry["error"] = str(exc)
                report["interactions"].append(entry)

            page.screenshot(path=str(screenshot_path), full_page=True)
            context.tracing.stop(path=str(trace_path))
            context.close()
            browser.close()

        report["ok"] = bool(report["interactions"]) and all(
            entry["ok"] for entry in report["interactions"]
        )
    except Exception as exc:
        report["startup_error"] = str(exc)
    finally:
        stop_process(process)
        report["server_exit_code"] = process.poll()
        server_log.close()

    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# YTIS Playwright Navigation Interaction Report",
        "",
        f"- Overall: {'PASS' if report['ok'] else 'FAIL'}",
        f"- Interactions checked: {len(report['interactions'])}",
        f"- Server exit code after shutdown: {report['server_exit_code']}",
        "",
        "## Results",
        "",
    ]
    for entry in report["interactions"]:
        lines.append(
            f"- {'PASS' if entry['ok'] else 'FAIL'} `{entry['label']}` -> "
            f"`{entry['actual_path'] or entry['expected_route']}` active={entry['active_count']}"
        )
        if entry["error"]:
            lines.append(f"  - error: {entry['error']}")
    if report["startup_error"]:
        lines.extend(["", "## Startup error", "", report["startup_error"]])
    report_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
