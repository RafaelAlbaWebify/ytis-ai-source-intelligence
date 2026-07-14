from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ARTIFACT_DIR = ROOT / "artifacts" / "source-pack-smoke"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SAMPLE_SRT = """1
00:00:00,000 --> 00:00:03,000
Evidence should be traceable and reviewable.

2
00:00:03,000 --> 00:00:06,000
Evidence should be traceable and reviewable.

3
00:00:06,000 --> 00:00:10,000
Human review separates source evidence from interpretation.
"""


def main() -> int:
    from ytis.core import builder
    from ytis.core.builder import BuildOptions, build_research_pack

    checks: dict[str, bool] = {}
    details: dict[str, object] = {}
    error = ""

    with tempfile.TemporaryDirectory(prefix="ytis-source-pack-") as temp_dir:
        root = Path(temp_dir)
        projects = root / "projects"
        downloads = root / "downloads"
        project_name = "CI Evidence Fixture"
        safe_project_name = "CI_Evidence_Fixture"
        existing_project = projects / f"{safe_project_name}_YTIS_RESEARCH_READY"
        raw_srt = existing_project / "raw_srt"
        raw_srt.mkdir(parents=True, exist_ok=True)
        fixture_name = "20260714 - Evidence Workflow [fixture01].en.srt"
        (raw_srt / fixture_name).write_text(SAMPLE_SRT, encoding="utf-8")

        original_fetch = builder.fetch_channel_video_index
        builder.fetch_channel_video_index = lambda _url, _callback=None: []
        try:
            result = build_research_pack(
                BuildOptions(
                    name=project_name,
                    url="https://example.invalid/public-safe-fixture",
                    lang="en",
                    output_downloads=downloads,
                    base_projects_dir=projects,
                    mode="repackage",
                )
            )

            project_dir = Path(result.project_dir)
            zip_path = Path(result.zip_path)
            summary_path = project_dir / "project_summary.json"
            index_path = project_dir / "transcript_index.csv"
            combined_path = project_dir / "ALL_TRANSCRIPTS_COMBINED.md"
            prompt_path = project_dir / "README_ANALYSIS_PROMPT.md"
            registry_path = projects / "projects_index.json"
            clean_files = sorted((project_dir / "clean_txt").glob("*.txt"))
            clean_text = clean_files[0].read_text(encoding="utf-8") if clean_files else ""

            zip_names: list[str] = []
            if zip_path.exists():
                with zipfile.ZipFile(zip_path, "r") as archive:
                    zip_names = archive.namelist()
                    bad_member = archive.testzip()
            else:
                bad_member = "zip missing"

            summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
            checks = {
                "project_dir_exists": project_dir.exists(),
                "zip_exists": zip_path.exists(),
                "zip_integrity": bad_member is None,
                "summary_exists": summary_path.exists(),
                "index_exists": index_path.exists(),
                "combined_report_exists": combined_path.exists(),
                "analysis_prompt_exists": prompt_path.exists(),
                "registry_exists": registry_path.exists(),
                "one_transcript_created": result.transcripts_created == 1,
                "positive_word_count": result.total_words > 0,
                "repackage_mode_preserved": result.mode == "repackage",
                "duplicate_caption_collapsed": clean_text.lower().count(
                    "evidence should be traceable and reviewable"
                ) == 1,
                "source_id_preserved": "fixture01" in clean_text or "fixture01" in index_path.read_text(encoding="utf-8-sig"),
                "summary_transactional": summary.get("transactional_build") is True,
                "required_zip_content": all(
                    any(name == required or name.endswith("/" + required) for name in zip_names)
                    for required in (
                        "ALL_TRANSCRIPTS_COMBINED.md",
                        "project_summary.json",
                        "README_ANALYSIS_PROMPT.md",
                    )
                ),
            }
            details = {
                "result": {
                    "project_dir": str(project_dir),
                    "zip_path": str(zip_path),
                    "transcripts_created": result.transcripts_created,
                    "total_words": result.total_words,
                    "mode": result.mode,
                },
                "clean_text": clean_text,
                "zip_names": zip_names,
                "summary": summary,
            }
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        finally:
            builder.fetch_channel_video_index = original_fetch

    ok = bool(checks) and all(checks.values()) and not error
    report = {"ok": ok, "checks": checks, "details": details, "error": error}
    (ARTIFACT_DIR / "source-pack-smoke.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    lines = [
        "# Deterministic Source-Pack Smoke Test",
        "",
        f"Overall: {'PASS' if ok else 'FAIL'}",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {'PASS' if value else 'FAIL'} — `{name}`" for name, value in checks.items())
    if error:
        lines.extend(["", "## Error", "", error])
    (ARTIFACT_DIR / "source-pack-smoke.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
