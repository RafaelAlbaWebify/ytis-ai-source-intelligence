from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "provider-configuration-guard"
BASE_URL = "http://127.0.0.1:8080"


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
    raise RuntimeError(f"YTIS did not become ready: {last_error}")


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
    report_path = OUT / "provider-configuration-guard.json"
    screenshot_path = OUT / "provider-configuration-guard.png"
    trace_path = OUT / "trace.zip"
    server_log_path = OUT / "server.log"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONUNBUFFERED"] = "1"
    env["YTIS_RESEARCH_PROVIDER"] = "structured-json"
    env["YTIS_RESEARCH_PROVIDER_NAME"] = "unavailable-test-provider"
    env["YTIS_RESEARCH_DIR"] = tempfile.mkdtemp(prefix="ytis-provider-guard-")

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
            context = browser.new_context(viewport={"width": 1365, "height": 900})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            page.on(
                "console",
                lambda message: console_errors.append(message.text)
                if message.type == "error"
                else None,
            )
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on(
                "response",
                lambda response: server_errors.append(f"{response.status} {response.url}")
                if response.status >= 500
                else None,
            )
            page.goto(
                BASE_URL + "/technical-research",
                wait_until="networkidle",
                timeout=30_000,
            )
            body = page.locator("body").inner_text()
            report["checks"] = {
                "workbench_route_loaded": "Technical Research Workbench" in body,
                "guard_visible": page.get_by_test_id("provider-unavailable").count() == 1,
                "configuration_error_visible": (
                    "requires an explicitly injected generator"
                    in page.get_by_test_id("provider-configuration-error").inner_text()
                ),
                "analyze_control_absent": page.get_by_test_id("analyze-source").count() == 0,
                "no_console_errors": not console_errors,
                "no_page_errors": not page_errors,
                "no_server_errors": not server_errors,
            }
            report["errors"] = console_errors + page_errors + server_errors
            page.screenshot(path=str(screenshot_path), full_page=True)
            context.tracing.stop(path=str(trace_path))
            context.close()
            browser.close()
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
