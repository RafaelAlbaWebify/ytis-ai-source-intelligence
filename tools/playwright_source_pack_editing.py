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
OUT = ROOT / "artifacts" / "source-pack-editing-workbench"
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
    temp_root = Path(tempfile.mkdtemp(prefix="ytis-source-edit-", dir=OUT))
    screenshot_path = OUT / "source-pack-editing-final.png"
    trace_path = OUT / "trace.zip"
    server_log_path = OUT / "server.log"
    report_path = OUT / "report.json"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONUNBUFFERED"] = "1"
    env["YTIS_RESEARCH_DIR"] = str(temp_root)
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
        from playwright.sync_api import sync_playwright

        console_errors: list[str] = []
        page_errors: list[str] = []
        server_errors: list[str] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1400})
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

            page.get_by_test_id("source-title").fill("First source")
            page.get_by_test_id("source-origin").fill("first-origin")
            page.get_by_test_id("source-text").fill("The platform supports stable source editing.")
            page.get_by_test_id("add-source").click()
            page.get_by_test_id("source-pack-item-1").wait_for(state="visible")

            page.get_by_test_id("source-title").fill("Second source")
            page.get_by_test_id("source-origin").fill("second-origin")
            page.get_by_test_id("source-text").fill("The workflow requires stable source ordering.")
            page.get_by_test_id("add-source").click()
            page.get_by_test_id("source-pack-item-2").wait_for(state="visible")

            page.get_by_test_id("edit-source-1").click()
            report["checks"]["edit_mode_identifies_source"] = "source-001" in page.get_by_test_id(
                "source-edit-status"
            ).inner_text()
            page.get_by_test_id("source-title").fill("First source updated")
            page.get_by_test_id("source-origin").fill("first-origin-updated")
            page.get_by_test_id("add-source").click()
            page.get_by_test_id("source-pack-title-1").wait_for(state="visible")
            report["checks"]["edit_preserves_id"] = "source-001" in page.get_by_test_id(
                "source-pack-title-1"
            ).inner_text()
            report["checks"]["edit_updates_metadata"] = (
                "First source updated" in page.get_by_test_id("source-pack-title-1").inner_text()
                and "first-origin-updated" in page.get_by_test_id("source-pack-origin-1").inner_text()
            )

            page.get_by_test_id("move-source-up-2").click()
            report["checks"]["move_changes_order_only"] = (
                "source-002" in page.get_by_test_id("source-pack-title-1").inner_text()
                and "source-001" in page.get_by_test_id("source-pack-title-2").inner_text()
            )

            page.get_by_test_id("remove-source-1").click()
            page.get_by_test_id("source-pack-item-2").wait_for(state="detached", timeout=10_000)
            report["checks"]["remove_does_not_renumber"] = "source-001" in page.get_by_test_id(
                "source-pack-title-1"
            ).inner_text()

            page.get_by_test_id("source-title").fill("Third source")
            page.get_by_test_id("source-origin").fill("third-origin")
            page.get_by_test_id("source-text").fill("The next source receives the next unused identifier.")
            page.get_by_test_id("add-source").click()
            page.get_by_test_id("source-pack-item-2").wait_for(state="visible")
            report["checks"]["new_source_uses_unused_id"] = "source-002" in page.get_by_test_id(
                "source-pack-title-2"
            ).inner_text()

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
