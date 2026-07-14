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
OUT = ROOT / "artifacts" / "playwright"
SCREENSHOTS = OUT / "screenshots"
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
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    server_log_path = OUT / "server.log"
    report_json_path = OUT / "route-smoke-report.json"
    report_md_path = OUT / "route-smoke-report.md"
    trace_path = OUT / "trace.zip"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONUNBUFFERED"] = "1"

    creationflags = 0
    start_new_session = os.name != "nt"
    server_log = server_log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-m", "ytis.app"],
        cwd=ROOT,
        env=env,
        stdout=server_log,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=start_new_session,
        creationflags=creationflags,
    )

    report: dict[str, Any] = {
        "ok": False,
        "base_url": BASE_URL,
        "routes": [],
        "startup_error": "",
        "server_exit_code": None,
    }

    try:
        wait_for_server()

        if str(SRC) not in sys.path:
            sys.path.insert(0, str(SRC))
        from ytis.ui.layout import NAV_ITEMS
        from playwright.sync_api import sync_playwright

        routes = [path for _label, path, _icon in NAV_ITEMS]
        failures = 0

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            for index, route in enumerate(routes, start=1):
                page = context.new_page()
                console_errors: list[str] = []
                page_errors: list[str] = []
                server_errors: list[str] = []

                page.on(
                    "console",
                    lambda message, bucket=console_errors: bucket.append(message.text)
                    if message.type == "error"
                    else None,
                )
                page.on("pageerror", lambda error, bucket=page_errors: bucket.append(str(error)))
                page.on(
                    "response",
                    lambda response, bucket=server_errors: bucket.append(
                        f"{response.status} {response.url}"
                    )
                    if response.status >= 500
                    else None,
                )

                url = BASE_URL.rstrip("/") + route
                entry: dict[str, Any] = {
                    "route": route,
                    "url": url,
                    "ok": False,
                    "status": None,
                    "title": "",
                    "console_errors": console_errors,
                    "page_errors": page_errors,
                    "server_errors": server_errors,
                    "fallback_detected": False,
                    "error": "",
                }

                try:
                    response = page.goto(url, wait_until="networkidle", timeout=30_000)
                    entry["status"] = response.status if response else None
                    entry["title"] = page.title()
                    body_text = page.locator("body").inner_text(timeout=10_000)
                    entry["fallback_detected"] = "module not available" in body_text.lower()
                    screenshot_name = f"{index:02d}-{route.strip('/').replace('/', '-') or 'dashboard'}.png"
                    page.screenshot(path=str(SCREENSHOTS / screenshot_name), full_page=True)

                    entry["ok"] = bool(
                        response
                        and response.status < 500
                        and not console_errors
                        and not page_errors
                        and not server_errors
                        and not entry["fallback_detected"]
                    )
                except Exception as exc:
                    entry["error"] = str(exc)

                if not entry["ok"]:
                    failures += 1
                report["routes"].append(entry)
                page.close()

            context.tracing.stop(path=str(trace_path))
            context.close()
            browser.close()

        report["ok"] = failures == 0

    except Exception as exc:
        report["startup_error"] = str(exc)
        report["ok"] = False
    finally:
        stop_process(process)
        report["server_exit_code"] = process.poll()
        server_log.close()

    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# YTIS Playwright Route Smoke Report",
        "",
        f"- Overall: {'PASS' if report['ok'] else 'FAIL'}",
        f"- Base URL: {report['base_url']}",
        f"- Routes checked: {len(report['routes'])}",
        f"- Server exit code after shutdown: {report['server_exit_code']}",
        "",
        "## Route results",
        "",
    ]
    for entry in report["routes"]:
        lines.append(
            f"- {'PASS' if entry['ok'] else 'FAIL'} `{entry['route']}` "
            f"status={entry['status']} console={len(entry['console_errors'])} "
            f"page={len(entry['page_errors'])} server={len(entry['server_errors'])} "
            f"fallback={entry['fallback_detected']}"
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
