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
OUT = ROOT / "artifacts" / "structured-provider-workbench"
BASE_URL = "http://127.0.0.1:8080"


def wait_for_server(timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE_URL, timeout=3) as response:
                if response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(1)
    raise RuntimeError("structured fixture app did not become ready")


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
    temp_root = Path(tempfile.mkdtemp(prefix="ytis-structured-ui-", dir=OUT))
    report_path = OUT / "report.json"
    screenshot_path = OUT / "structured-workbench.png"
    trace_path = OUT / "trace.zip"
    server_log_path = OUT / "server.log"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONUNBUFFERED"] = "1"
    env["YTIS_RESEARCH_DIR"] = str(temp_root)
    env["YTIS_RESEARCH_PROVIDER"] = "structured-json"
    env["YTIS_RESEARCH_PROVIDER_NAME"] = "ci-structured-fixture"
    env["YTIS_RESEARCH_MAX_FINDINGS"] = "5"

    server_log = server_log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "tools/run_structured_provider_fixture_app.py"],
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
        from ytis.research import JsonInvestigationRepository

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
            page.on("response", lambda response: server_errors.append(f"{response.status} {response.url}") if response.status >= 500 else None)

            page.goto(BASE_URL + "/technical-research", wait_until="networkidle", timeout=30_000)
            provider_text = page.get_by_test_id("active-provider").inner_text()
            report["checks"]["structured_provider_visible"] = "ci-structured-fixture" in provider_text

            page.get_by_test_id("investigation-id").fill("structured-browser-proof")
            page.get_by_test_id("analyze-source").click()
            page.get_by_test_id("finding-2").wait_for(state="visible", timeout=15_000)
            report["checks"]["two_structured_findings"] = page.locator("[data-testid^='finding-']").count() == 2
            body_text = page.locator("body").inner_text()
            report["checks"]["structured_titles_visible"] = (
                "Local processing capability" in body_text and "Human review constraint" in body_text
            )

            page.get_by_test_id("accept-1").click()
            page.get_by_test_id("reject-2").click()
            page.get_by_test_id("save-investigation").click()
            page.get_by_test_id("export-report").click()
            page.wait_for_timeout(1200)
            page.screenshot(path=str(screenshot_path), full_page=True)
            context.tracing.stop(path=str(trace_path))
            browser.close()

        repository = JsonInvestigationRepository(temp_root / "investigations")
        investigation = repository.load("structured-browser-proof")
        markdown_path = temp_root / "reports" / "structured-browser-proof" / "technical-research-report.md"
        markdown = markdown_path.read_text(encoding="utf-8")
        report["checks"].update(
            {
                "saved_structured_investigation": "structured-browser-proof" in repository.list_ids(),
                "structured_ids_persisted": [item.finding_id for item in investigation.findings]
                == ["structured-f001", "structured-f002"],
                "accepted_review_persisted": investigation.review_status("structured-f001") == "accepted",
                "rejected_review_persisted": investigation.review_status("structured-f002") == "rejected",
                "accepted_in_markdown": "Local processing capability" in markdown,
                "rejected_not_in_markdown": "Human review constraint" not in markdown,
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
