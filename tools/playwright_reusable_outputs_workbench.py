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
OUT = ROOT / "artifacts" / "reusable-outputs-workbench"
BASE_URL = os.environ.get("YTIS_BASE_URL", "http://127.0.0.1:8080")
DUPLICATE_FACT = "The platform supports evidence-linked local reports."
ACTION = "Use this evidence when designing the next reporting iteration."
FINDING_ID = "f001"


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
    temp_root = Path(tempfile.mkdtemp(prefix="ytis-reusable-", dir=OUT))
    screenshot_path = OUT / "reusable-outputs-final.png"
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
        console_errors: list[str] = []
        page_errors: list[str] = []
        server_errors: list[str] = []
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1500})
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
            page.get_by_test_id("investigation-id").fill("reusable-output-proof")
            page.get_by_test_id("investigation-title").fill("Reusable output workbench proof")

            page.get_by_test_id("source-title").fill("Primary note")
            page.get_by_test_id("source-origin").fill("fixture-primary")
            page.get_by_test_id("source-text").fill(DUPLICATE_FACT)
            page.get_by_test_id("add-source").click()
            page.get_by_test_id("source-pack-item-1").wait_for(state="visible")

            page.get_by_test_id("source-title").fill("Normalized duplicate note")
            page.get_by_test_id("source-origin").fill("fixture-copy")
            page.get_by_test_id("source-text").fill("  THE platform   supports evidence-linked local reports.  ")
            page.get_by_test_id("add-source").click()
            page.get_by_test_id("source-pack-item-2").wait_for(state="visible")
            page.get_by_test_id("duplicate-warning").wait_for(state="visible")
            report["checks"]["duplicate_warning_visible"] = page.get_by_test_id("duplicate-warning").is_visible()
            report["checks"]["duplicate_group_exact"] = (
                "source-001, source-002" in page.get_by_test_id("duplicate-group-1").inner_text()
            )

            page.get_by_test_id("analyze-source").click()
            page.get_by_test_id("finding-2").wait_for(state="visible", timeout=15_000)

            page.get_by_test_id("card-action-1").fill(ACTION)
            page.get_by_test_id("save-card-1").click()
            page.wait_for_timeout(400)
            cards_dir = temp_root / "insight_cards"
            report["checks"]["pending_card_not_created"] = not cards_dir.exists() or not list(cards_dir.glob("*.json"))

            page.get_by_test_id("accept-1").click()
            page.get_by_test_id("save-card-1").click()
            card_path = cards_dir / f"reusable-output-proof--{FINDING_ID}.json"
            deadline = time.time() + 10
            while time.time() < deadline and not card_path.exists():
                time.sleep(0.1)
            report["checks"]["accepted_card_created"] = card_path.exists()

            page.get_by_test_id("export-reviewed-report").click()
            reviewed_path = (
                temp_root
                / "reports"
                / "reusable-output-proof"
                / "reviewed"
                / "technical-lessons.md"
            )
            deadline = time.time() + 10
            while time.time() < deadline and not reviewed_path.exists():
                time.sleep(0.1)
            report["checks"]["reviewed_template_created"] = reviewed_path.exists()

            page.screenshot(path=str(screenshot_path), full_page=True)
            context.tracing.stop(path=str(trace_path))
            context.close()
            browser.close()

        card_payload = json.loads(card_path.read_text(encoding="utf-8")) if card_path.exists() else {}
        reviewed_markdown = reviewed_path.read_text(encoding="utf-8") if reviewed_path.exists() else ""
        report["checks"].update(
            {
                "card_action_persisted": card_payload.get("action") == ACTION,
                "card_finding_exact": card_payload.get("finding_id") == FINDING_ID,
                "card_evidence_exact": card_payload.get("evidence_ids") == ["source-001:e001"],
                "reviewed_report_boundary": "Only human-accepted findings are included." in reviewed_markdown,
                "reviewed_report_contains_accepted_fact": DUPLICATE_FACT in reviewed_markdown,
                "reviewed_report_contains_accepted_evidence": "source-001:e001" in reviewed_markdown,
                "reviewed_report_excludes_pending_duplicate": "source-002:e001" not in reviewed_markdown,
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
