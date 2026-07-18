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
OUT = ROOT / "artifacts" / "public-demo"
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
    screenshot_path = OUT / "public-demo-final.png"
    trace_path = OUT / "trace.zip"
    server_log_path = OUT / "server.log"
    report_path = OUT / "report.json"
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
    report: dict[str, Any] = {"ok": False, "checks": {}, "errors": []}
    try:
        wait_for_server()
        if str(SRC) not in sys.path:
            sys.path.insert(0, str(SRC))
        from playwright.sync_api import sync_playwright

        console_errors: list[str] = []
        page_errors: list[str] = []
        server_errors: list[str] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1200})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on(
                "response",
                lambda response: server_errors.append(f"{response.status} {response.url}")
                if response.status >= 500
                else None,
            )
            page.goto(BASE_URL.rstrip("/") + "/demo", wait_until="networkidle", timeout=30_000)
            report["checks"]["demo_route_loaded"] = page.get_by_text("YTIS Demo Journey", exact=True).is_visible()
            report["checks"]["offline_badge_visible"] = page.get_by_test_id("demo-provider").is_visible()
            report["checks"]["public_source_visible"] = page.get_by_test_id("demo-source-text").is_visible()
            report["checks"]["review_warning_visible"] = page.get_by_test_id("demo-review-warning").is_visible()
            report["checks"]["empty_state_visible"] = page.get_by_test_id("demo-empty").is_visible()
            page.get_by_test_id("run-demo").click()
            page.get_by_test_id("demo-finding-4").wait_for(state="visible", timeout=15_000)
            summary = page.get_by_test_id("demo-summary").inner_text()
            body = page.locator("body").inner_text()
            report["checks"]["four_findings_rendered"] = page.locator("[data-testid^='demo-finding-']").count() == 4
            report["checks"]["summary_exact"] = "4 evidence units" in summary and "4 findings" in summary
            report["checks"]["all_categories_visible"] = all(
                category in body for category in ("capability", "constraint", "risk", "recommendation")
            )
            report["checks"]["provenance_visible"] = all(
                f"demo-source-001:e00{index}" in body for index in range(1, 5)
            )
            report["checks"]["pending_review_visible"] = body.count("pending human review") >= 4
            report["checks"]["no_save_controls"] = "Save investigation" not in body
            page.screenshot(path=str(screenshot_path), full_page=True)
            context.tracing.stop(path=str(trace_path))
            context.close()
            browser.close()
        report["checks"]["no_console_errors"] = not console_errors
        report["checks"]["no_page_errors"] = not page_errors
        report["checks"]["no_server_errors"] = not server_errors
        report["errors"] = console_errors + page_errors + server_errors
        report["ok"] = all(report["checks"].values())
    except Exception as exc:
        report["errors"].append(str(exc))
    finally:
        stop_process(process)
        server_log.close()
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
