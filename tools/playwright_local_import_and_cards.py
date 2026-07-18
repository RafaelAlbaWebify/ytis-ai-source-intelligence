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

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "local-import-and-cards"
BASE_URL = os.environ.get("YTIS_BASE_URL", "http://127.0.0.1:8080")


def wait_for_server(timeout: int = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE_URL, timeout=3) as response:
                if response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(1)
    raise RuntimeError("YTIS did not become ready")


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
    temp_root = Path(tempfile.mkdtemp(prefix="ytis-import-cards-", dir=OUT))
    source_file = temp_root / "source.md"
    source_file.write_text(
        "The platform supports local evidence-linked analysis. Human review is required before reuse.",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONUNBUFFERED"] = "1"
    env["YTIS_RESEARCH_DIR"] = str(temp_root / "storage")

    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    from ytis.research import InsightCard, JsonInsightCardRepository

    card_repository = JsonInsightCardRepository(Path(env["YTIS_RESEARCH_DIR"]) / "insight_cards")
    card_repository.save(
        InsightCard(
            card_id="card-a",
            investigation_id="seed-a",
            finding_id="finding-a",
            claim="Preserve evidence provenance.",
            evidence_ids=("source-001:e001",),
            confidence=0.9,
            action="Keep exact evidence IDs.",
        )
    )
    card_repository.save(
        InsightCard(
            card_id="card-b",
            investigation_id="seed-b",
            finding_id="finding-b",
            claim="  preserve   evidence provenance. ",
            evidence_ids=("source-002:e001",),
            confidence=0.8,
            action="Review related evidence.",
        )
    )

    server_log_path = OUT / "server.log"
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
    result = {"ok": False, "checks": {}, "errors": []}
    try:
        wait_for_server()
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1200})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            page.goto(BASE_URL + "/local-source-import", wait_until="networkidle")
            page.get_by_test_id("local-import-path").fill(str(source_file))
            page.get_by_test_id("run-local-import").click()
            page.get_by_test_id("local-import-result").wait_for(state="visible", timeout=15_000)
            result["checks"]["import_result_visible"] = page.get_by_text("Saved local-import-001", exact=True).is_visible()
            saved = Path(env["YTIS_RESEARCH_DIR"]) / "investigations" / "local-import-001.json"
            payload = json.loads(saved.read_text(encoding="utf-8"))
            result["checks"]["investigation_saved"] = payload["sources"][0]["content"] == source_file.read_text(encoding="utf-8")
            result["checks"]["pending_findings_created"] = bool(payload["findings"]) and payload["reviews"] == []

            page.goto(BASE_URL + "/insight-cards", wait_until="networkidle")
            page.get_by_test_id("insight-card-2").wait_for(state="visible", timeout=15_000)
            result["checks"]["two_cards_visible"] = page.locator("[data-testid^='insight-card-']").count() == 2
            relation = page.get_by_test_id("related-card-1")
            result["checks"]["related_advisory_visible"] = relation.is_visible() and "same-normalized-claim" in relation.inner_text()
            page.screenshot(path=str(OUT / "final.png"), full_page=True)
            context.tracing.stop(path=str(OUT / "trace.zip"))
            context.close()
            browser.close()
        result["ok"] = all(result["checks"].values())
    except Exception as exc:
        result["errors"].append(str(exc))
    finally:
        stop_process(process)
        server_log.close()
    (OUT / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
