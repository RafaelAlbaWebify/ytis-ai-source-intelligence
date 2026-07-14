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
OUT = ROOT / "artifacts" / "multi-source-workbench"
BASE_URL = os.environ.get("YTIS_BASE_URL", "http://127.0.0.1:8080")
SOURCE_ONE_FACT = "The collector supports offline evidence packaging."
SOURCE_TWO_FACT = "A major risk is loss of provenance during manual consolidation."


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
    temp_root = Path(tempfile.mkdtemp(prefix="ytis-multi-source-", dir=OUT))
    screenshot_path = OUT / "multi-source-final.png"
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
    report: dict[str, Any] = {"ok": False, "checks": {}, "errors": [], "storage_root": str(temp_root)}

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
            page.get_by_test_id("investigation-id").fill("multi-source-proof-001")
            page.get_by_test_id("investigation-title").fill("Multi-source provenance proof")

            page.get_by_test_id("source-title").fill("Collector capability note")
            page.get_by_test_id("source-text").fill(SOURCE_ONE_FACT)
            page.get_by_test_id("add-source").click()
            page.get_by_test_id("source-pack-item-1").wait_for(state="visible")

            page.get_by_test_id("source-title").fill("Consolidation risk note")
            page.get_by_test_id("source-text").fill(SOURCE_TWO_FACT)
            page.get_by_test_id("add-source").click()
            page.get_by_test_id("source-pack-item-2").wait_for(state="visible")
            report["checks"]["two_sources_staged"] = page.locator("[data-testid^='source-pack-item-']").count() == 2
            report["checks"]["stable_source_ids_visible"] = (
                "source-001" in page.get_by_test_id("source-pack-title-1").inner_text()
                and "source-002" in page.get_by_test_id("source-pack-title-2").inner_text()
            )

            page.get_by_test_id("analyze-source").click()
            page.get_by_test_id("finding-2").wait_for(state="visible", timeout=15_000)
            body = page.locator("body").inner_text()
            report["checks"]["both_provenance_chains_visible"] = (
                "source-001:e001" in body and "source-002:e001" in body
            )
            page.get_by_test_id("accept-1").click()
            page.get_by_test_id("accept-2").click()
            page.get_by_test_id("save-investigation").click()
            page.get_by_test_id("export-report").click()
            page.wait_for_timeout(1000)

            page.get_by_test_id("remove-source-2").click()
            page.get_by_test_id("source-pack-item-2").wait_for(state="detached", timeout=10_000)
            report["checks"]["source_removed_before_reopen"] = page.locator("[data-testid^='source-pack-item-']").count() == 1
            page.get_by_test_id("saved-investigation").click()
            page.get_by_text("multi-source-proof-001", exact=True).last.click()
            page.get_by_test_id("reopen-investigation").click()
            page.get_by_test_id("source-pack-item-2").wait_for(state="visible", timeout=10_000)
            report["checks"]["reopen_restored_two_sources"] = page.locator("[data-testid^='source-pack-item-']").count() == 2

            page.screenshot(path=str(screenshot_path), full_page=True)
            context.tracing.stop(path=str(trace_path))
            context.close()
            browser.close()

        repository = JsonInvestigationRepository(temp_root / "investigations")
        investigation = repository.load("multi-source-proof-001")
        TechnicalResearchService().validate_grounding(investigation)
        markdown_path = temp_root / "reports" / "multi-source-proof-001" / "technical-research-report.md"
        json_path = temp_root / "reports" / "multi-source-proof-001" / "technical-research-report.json"
        markdown = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""
        payload = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else {}

        report["checks"].update(
            {
                "two_sources_persisted": [source.source_id for source in investigation.sources] == ["source-001", "source-002"],
                "source_titles_persisted": [source.title for source in investigation.sources]
                == ["Collector capability note", "Consolidation risk note"],
                "evidence_spans_both_sources": {item.source_id for item in investigation.evidence}
                == {"source-001", "source-002"},
                "reviews_persisted": all(
                    investigation.review_status(finding.finding_id) == "accepted"
                    for finding in investigation.findings
                ),
                "markdown_contains_both_facts": SOURCE_ONE_FACT in markdown and SOURCE_TWO_FACT in markdown,
                "markdown_contains_both_source_ids": "source-001:e001" in markdown and "source-002:e001" in markdown,
                "json_contains_two_sources": len(payload.get("sources", [])) == 2,
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
