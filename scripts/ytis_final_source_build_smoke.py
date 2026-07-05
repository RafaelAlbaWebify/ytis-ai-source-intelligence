from __future__ import annotations

import argparse
import csv
import inspect
import json
import sys
import time
import traceback
import zipfile
from collections import Counter
from pathlib import Path


def _now_stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _safe_read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _find_duplicates_from_index(index_path: Path) -> list[str]:
    if not index_path.exists():
        return []
    ids: list[str] = []
    try:
        with index_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                value = (row.get("video_id") or row.get("id") or row.get("filename") or "").strip()
                if value:
                    ids.append(value)
    except Exception:
        return ["INDEX_READ_ERROR"]
    counts = Counter(ids)
    return sorted([key for key, count in counts.items() if count > 1])


def _zip_ok(zip_path: Path) -> tuple[bool, str]:
    if not zip_path.exists():
        return False, "zip_missing"
    if zip_path.stat().st_size <= 0:
        return False, "zip_empty"
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            bad = zf.testzip()
            names = set(zf.namelist())
        if bad:
            return False, f"zip_bad_member:{bad}"

        # Accept both root-level files and packs that include a project folder prefix.
        required_endings = [
            "ALL_TRANSCRIPTS_COMBINED.md",
            "project_summary.json",
            "README_ANALYSIS_PROMPT.md",
        ]
        missing = []
        for ending in required_endings:
            if not any(name == ending or name.endswith("/" + ending) for name in names):
                missing.append(ending)
        if missing:
            return False, "zip_missing_required:" + ",".join(missing)
        return True, "zip_ok"
    except Exception as exc:
        return False, f"zip_error:{exc}"


def _make_build_options(BuildOptions, *, name: str, url: str, lang: str, output_downloads: Path, base_projects_dir: Path, mode: str):
    """BuildOptions changed during YTIS development; create it using only supported fields."""
    kwargs = {
        "name": name,
        "url": url,
        "lang": lang,
        "output_downloads": output_downloads,
        "base_projects_dir": base_projects_dir,
    }
    try:
        sig = inspect.signature(BuildOptions)
        if "mode" in sig.parameters:
            kwargs["mode"] = mode
    except Exception:
        kwargs["mode"] = mode
    try:
        return BuildOptions(**kwargs)
    except TypeError:
        kwargs.pop("mode", None)
        return BuildOptions(**kwargs)


def main() -> int:
    parser = argparse.ArgumentParser(description="YTIS final transaction-safe source build smoke test")
    parser.add_argument("--root", required=True, help="YTIS repository root")
    parser.add_argument("--project-name", default="YTIS_Final_Source_Smoke_MikeyWebsite")
    parser.add_argument("--url", default="https://www.youtube.com/@Mikeywebsite")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--mode", default="refresh", choices=["reuse", "refresh", "repackage"])
    parser.add_argument("--out-dir", required=True, help="Folder where proof files should be written")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "source_build_smoke.log"
    report_path = out_dir / "source_build_smoke_report.json"
    md_path = out_dir / "source_build_smoke_report.md"

    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    logs: list[dict] = []

    def callback(message: str, progress: float | None = None) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {message}"
        print(line, flush=True)
        logs.append({"time": time.strftime("%H:%M:%S"), "message": message, "progress": progress})
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    report = {
        "started_at": _now_stamp(),
        "root": str(root),
        "project_name": args.project_name,
        "url": args.url,
        "lang": args.lang,
        "mode": args.mode,
        "ok": False,
        "error": "",
        "traceback": "",
        "result": {},
        "checks": {},
        "logs": logs,
    }

    try:
        from ytis.core.builder import BuildOptions, build_research_pack
        from ytis.core.paths import default_downloads_dir

        # Do not import historical constants such as DOWNLOADS_DIR or PROJECTS_DIR.
        # Current YTIS exposes functions and uses root/projects as the source-pack folder.
        output_downloads = default_downloads_dir()
        base_projects_dir = root / "projects"

        callback("Starting transaction-safe source build smoke test.", 0.01)
        callback(f"Using output downloads: {output_downloads}", 0.02)
        callback(f"Using projects dir: {base_projects_dir}", 0.03)

        options = _make_build_options(
            BuildOptions,
            name=args.project_name,
            url=args.url,
            lang=args.lang,
            output_downloads=output_downloads,
            base_projects_dir=base_projects_dir,
            mode=args.mode,
        )
        result = build_research_pack(options, callback=callback)

        project_dir = Path(result.project_dir)
        zip_path = Path(result.zip_path)
        summary_path = project_dir / "project_summary.json"
        index_path = project_dir / "transcript_index.csv"
        summary = _safe_read_json(summary_path)
        duplicate_ids = _find_duplicates_from_index(index_path)
        zip_good, zip_message = _zip_ok(zip_path)

        checks = {
            "project_dir_exists": project_dir.exists(),
            "zip_exists": zip_path.exists(),
            "zip_ok": zip_good,
            "zip_message": zip_message,
            "summary_exists": summary_path.exists(),
            "index_exists": index_path.exists(),
            "duplicate_ids": duplicate_ids,
            "duplicate_free": len(duplicate_ids) == 0,
            "transcripts_created_positive": int(getattr(result, "transcripts_created", 0) or 0) > 0,
            "total_words_positive": int(getattr(result, "total_words", summary.get("total_words", 0)) or 0) > 0,
        }
        report["result"] = {
            "project_dir": str(project_dir),
            "zip_path": str(zip_path),
            "videos_found": int(getattr(result, "videos_found", summary.get("videos_found", 0)) or 0),
            "transcripts_created": int(getattr(result, "transcripts_created", summary.get("transcripts_created", 0)) or 0),
            "total_words": int(getattr(result, "total_words", summary.get("total_words", 0)) or 0),
            "missing_subtitles": int(getattr(result, "missing_subtitles", summary.get("missing_subtitles", 0)) or 0),
            "mode": str(getattr(result, "mode", args.mode)),
            "summary": summary,
        }
        report["checks"] = checks
        report["ok"] = all([
            checks["project_dir_exists"],
            checks["zip_ok"],
            checks["summary_exists"],
            checks["index_exists"],
            checks["duplicate_free"],
            checks["transcripts_created_positive"],
            checks["total_words_positive"],
        ])
        callback("Source build smoke test finished with ok=" + str(report["ok"]).lower(), 1.0)

    except Exception as exc:
        report["ok"] = False
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        callback("Source build smoke test failed: " + str(exc), None)

    report["finished_at"] = _now_stamp()
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# YTIS Final Source Build Smoke Test",
        "",
        f"OK: {report['ok']}",
        f"Project: {args.project_name}",
        f"URL: {args.url}",
        f"Mode: {args.mode}",
        "",
        "## Result",
        "",
    ]
    for key, value in report.get("result", {}).items():
        if key != "summary":
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## Checks", ""])
    for key, value in report.get("checks", {}).items():
        lines.append(f"- {key}: {value}")
    if report.get("error"):
        lines.extend(["", "## Error", "", str(report.get("error")), "", "## Traceback", "", "```", str(report.get("traceback", "")), "```"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
