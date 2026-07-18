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

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "playwright-start-here"
BASE_URL = os.environ.get("YTIS_BASE_URL", "http://127.0.0.1:8080")


def wait_for_server(timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
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
    server_log = (OUT / "server.log").open("w", encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(
        [sys.executable, "-m", "ytis.app"],
        cwd=ROOT,
        env=env,
        stdout=server_log,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=os.name != "nt",
    )
    report = {"ok": False, "checks": {}, "visuals": {}, "errors": []}
    try:
        wait_for_server()
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            page.on("console", lambda message: report["errors"].append(message.text) if message.type == "error" else None)
            page.on("pageerror", lambda error: report["errors"].append(str(error)))
            response = page.goto(f"{BASE_URL}/start", wait_until="networkidle", timeout=30_000)

            body_background = page.locator("body").evaluate("element => getComputedStyle(element).backgroundColor")
            sidebar_background = page.locator(".ytis-sidebar").evaluate(
                "element => ({color: getComputedStyle(element).backgroundColor, image: getComputedStyle(element).backgroundImage})"
            )
            panel_background = page.locator(".ytis-card").first.evaluate(
                "element => getComputedStyle(element).backgroundColor"
            )
            panel_radius = page.locator(".ytis-card").first.evaluate(
                "element => getComputedStyle(element).borderRadius"
            )
            report["visuals"] = {
                "body_background": body_background,
                "sidebar_background": sidebar_background,
                "panel_background": panel_background,
                "panel_radius": panel_radius,
            }

            checks = {
                "route_ok": bool(response and response.status < 500),
                "title_visible": page.get_by_text("Start Here", exact=True).is_visible(),
                "demo_entry": page.get_by_test_id("start-demo").is_visible(),
                "import_entry": page.get_by_test_id("start-import").is_visible(),
                "workbench_entry": page.get_by_test_id("start-workbench").is_visible(),
                "cards_entry": page.get_by_test_id("start-cards").is_visible(),
                "review_boundary": page.get_by_test_id("start-review-boundary").is_visible(),
                "light_operational_canvas": body_background == "rgb(246, 248, 251)",
                "white_operational_panels": panel_background == "rgb(255, 255, 255)",
                "trace_navy_sidebar": "linear-gradient" in sidebar_background["image"]
                and ("7, 26, 51" in sidebar_background["image"] or "11, 35, 66" in sidebar_background["image"]),
                "restrained_panel_radius": panel_radius in {"11px", "0.7rem"},
            }
            page.get_by_test_id("start-demo").click()
            page.wait_for_url("**/demo")
            checks["demo_navigation"] = page.url.endswith("/demo")
            page.goto(f"{BASE_URL}/start", wait_until="networkidle")
            page.get_by_test_id("start-import").click()
            page.wait_for_url("**/local-source-import")
            checks["import_navigation"] = page.url.endswith("/local-source-import")
            page.goto(f"{BASE_URL}/start", wait_until="networkidle")
            page.get_by_test_id("start-workbench").click()
            page.wait_for_url("**/technical-research")
            checks["workbench_navigation"] = page.url.endswith("/technical-research")
            page.goto(f"{BASE_URL}/start", wait_until="networkidle")
            page.get_by_test_id("start-cards").click()
            page.wait_for_url("**/insight-cards")
            checks["cards_navigation"] = page.url.endswith("/insight-cards")
            page.goto(f"{BASE_URL}/start", wait_until="networkidle")
            page.screenshot(path=str(OUT / "start-here.png"), full_page=True)
            context.tracing.stop(path=str(OUT / "trace.zip"))
            report["checks"] = checks
            report["ok"] = all(checks.values()) and not report["errors"]
            browser.close()
    except Exception as exc:
        report["errors"].append(str(exc))
    finally:
        stop_process(process)
        server_log.close()
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
