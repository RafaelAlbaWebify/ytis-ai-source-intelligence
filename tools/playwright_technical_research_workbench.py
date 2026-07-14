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
OUT = ROOT / "artifacts" / "technical-research-workbench"
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
    report_path = OUT / "workbench-report.json"
    report_md_path = OUT / "workbench-report.md"
    trace_path = OUT / "trace.zip"
    screenshot_path = OUT / "workbench-final.png"
    server_log_path = OUT / "server.log"

    temp_root = Path(tempfile.mkdtemp(prefix="ytis-research-ui-", dir=OUT))
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

    report: dict[str, Any] = {
        "ok": False,
        "checks": {},
        "errors": [],
        "storage_root": str(temp_root),
        "server_exit_code": None,
    }

    try:
        wait_for_server()
        if str(SRC) not in sys.path:
            sys.path.insert(0, str(SRC))
        from playwright.sync_api import sync_playwright
        from ytis.research import JsonInvestigationRepository, TechnicalResearchService

        console_errors: list[str] = []
        page_errors: list[str] = []
        server_errors: list[str] = []

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1200})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            page.on(
                "console",
                lambda message: console_errors.append(message.text) if message.type == "error" else None,
            )
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on(
                "response",
                lambda response: server_errors.append(f"{response.status} {response.url}")
                if response.status >= 500
                else None,
            )

            page.goto(BASE_URL.rstrip("/") + "/technical-research", wait_until="networkidle", timeout=30_000)
            report["checks"]["page_loaded"] = "Technical Research Workbench" in page.locator("body").inner_text()

            page.get_by_test_id("investigation-id").locator("input").fill("browser-proof-001")
            page.get_by_test_id("investigation-title").locator("input").fill("Browser proof investigation")
            page.get_by_test_id("research-question").locator("input").fill(
                "What technical capabilities, constraints, risks, and recommendations are stated?"
            )
            page.get_by_test_id("source-title").locator("input").fill("Browser fixture technical note")
            page.get_by_test_id("source-text").locator("textarea").fill(
                "The platform supports local transcript cleaning and validated ZIP packaging. "
                "The current workflow requires human review before findings are published. "
                "A major risk is that unsupported claims could appear without evidence links. "
                "The next step should add structured evidence-linked findings and reports."
            )
            page.get_by_test_id("analyze-source").click()
            page.get_by_test_id("finding-4").wait_for(state="visible", timeout=15_000)
            report["checks"]["four_findings_rendered"] = page.locator("[data-testid^='finding-']").count() == 4
            report["checks"]["evidence_visible"] = "source-001:e001" in page.locator("body").inner_text()

            page.get_by_test_id("accept-1").click()
            page.get_by_test_id("reject-2").click()
            page.get_by_test_id("save-investigation").click()
            page.get_by_test_id("export-report").click()
            page.wait_for_timeout(1500)
            page.screenshot(path=str(screenshot_path), full_page=True)
            context.tracing.stop(path=str(trace_path))
            context.close()
            browser.close()

        repository = JsonInvestigationRepository(temp_root / "investigations")
        investigation = repository.load("browser-proof-001")
        service = TechnicalResearchService()
        service.validate_grounding(investigation)
        accepted = investigation.review_status(investigation.findings[0].finding_id)
        rejected = investigation.review_status(investigation.findings[1].finding_id)
        markdown_path = temp_root / "reports" / "browser-proof-001" / "technical-research-report.md"
        json_path = temp_root / "reports" / "browser-proof-001" / "technical-research-report.json"
        markdown = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""

        report["checks"].update(
            {
                "saved_investigation_exists": repository.exists("browser-proof-001"),
                "saved_aggregate_grounded": len(investigation.evidence) == 4 and len(investigation.findings) == 4,
                "accepted_review_persisted": accepted == "accepted",
                "rejected_review_persisted": rejected == "rejected",
                "markdown_export_exists": markdown_path.exists(),
                "json_export_exists": json_path.exists(),
                "accepted_finding_in_markdown": investigation.findings[0].summary in markdown,
                "rejected_finding_not_in_markdown": investigation.findings[1].summary not in markdown,
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
        report["server_exit_code"] = process.poll()
        server_log.close()

    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# YTIS Technical Research Workbench Report",
        "",
        f"- Overall: {'PASS' if report['ok'] else 'FAIL'}",
        f"- Storage root: `{report['storage_root']}`",
        f"- Server exit code after shutdown: {report['server_exit_code']}",
        "",
        "## Checks",
        "",
    ]
    for name, passed in report["checks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{name}`")
    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in report["errors"])
    report_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
