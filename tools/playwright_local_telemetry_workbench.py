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
OUT = ROOT / "artifacts" / "local-telemetry-workbench"
BASE_URL = os.environ.get("YTIS_BASE_URL", "http://127.0.0.1:8080")
SENSITIVE_SOURCE = "SENSITIVE_SOURCE_MARKER_91D2"
SENSITIVE_QUESTION = "SENSITIVE_QUESTION_MARKER_7A4C"


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
    trace_path = OUT / "trace.zip"
    screenshot_path = OUT / "telemetry-enabled.png"
    server_log_path = OUT / "server.log"
    report_path = OUT / "report.json"
    temp_root = Path(tempfile.mkdtemp(prefix="ytis-local-telemetry-", dir=OUT))

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONUNBUFFERED"] = "1"
    env["YTIS_RESEARCH_DIR"] = str(temp_root)
    env["YTIS_RESEARCH_TELEMETRY"] = "local-jsonl"

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
        from ytis.research import JsonlProviderTelemetryStore

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
            page.goto(BASE_URL.rstrip("/") + "/technical-research", wait_until="networkidle", timeout=30_000)
            report["checks"]["telemetry_enabled_visible"] = (
                page.get_by_test_id("telemetry-status").inner_text() == "Local telemetry enabled"
            )
            report["checks"]["telemetry_panel_visible"] = page.get_by_test_id("telemetry-panel").count() == 1
            report["checks"]["panel_starts_empty"] = page.get_by_test_id("telemetry-empty").count() == 1
            report["checks"]["initial_total_zero"] = page.get_by_test_id("telemetry-total").inner_text() == "0"

            page.get_by_test_id("research-question").fill(SENSITIVE_QUESTION)
            page.get_by_test_id("source-text").fill(
                f"{SENSITIVE_SOURCE}. The platform supports local evidence analysis. "
                "Human review is required before publication."
            )
            page.get_by_test_id("analyze-source").click()
            page.get_by_test_id("finding-1").wait_for(state="visible", timeout=15_000)
            report["checks"]["finding_rendered"] = page.locator("[data-testid^='finding-']").count() >= 1

            page.get_by_test_id("refresh-telemetry").click()
            page.get_by_test_id("telemetry-total").wait_for(state="visible", timeout=10_000)
            report["checks"]["summary_total_updated"] = page.get_by_test_id("telemetry-total").inner_text() == "1"
            report["checks"]["summary_success_rate_updated"] = (
                page.get_by_test_id("telemetry-success-rate").inner_text() == "100.0%"
            )
            report["checks"]["provider_row_visible"] = (
                "deterministic-rules" in page.get_by_test_id("telemetry-provider-row").inner_text()
            )
            report["checks"]["recent_row_visible"] = (
                "success" in page.get_by_test_id("telemetry-recent-row").inner_text()
            )

            page.screenshot(path=str(screenshot_path), full_page=True)
            context.tracing.stop(path=str(trace_path))
            context.close()
            browser.close()

        telemetry_path = temp_root / "telemetry" / "provider-executions.jsonl"
        store = JsonlProviderTelemetryStore(telemetry_path)
        events = store.read()
        raw = telemetry_path.read_text(encoding="utf-8") if telemetry_path.exists() else ""
        report["checks"].update(
            {
                "telemetry_file_created": telemetry_path.exists(),
                "one_event_written": len(events) == 1,
                "success_recorded": len(events) == 1 and events[0].outcome == "success",
                "deterministic_provider_recorded": len(events) == 1 and events[0].provider_name == "deterministic-rules",
                "source_not_persisted": SENSITIVE_SOURCE not in raw,
                "question_not_persisted": SENSITIVE_QUESTION not in raw,
                "no_console_errors": not console_errors,
                "no_page_errors": not page_errors,
                "no_server_errors": not server_errors,
            }
        )
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
