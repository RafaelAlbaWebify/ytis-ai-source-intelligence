from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "duplicate-source-detection"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import SourceDocument, find_duplicate_sources, normalize_source_content, source_fingerprint


def expect_value_error(fn, text: str) -> bool:
    try:
        fn()
    except ValueError as exc:
        return text in str(exc)
    return False


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = [
        SourceDocument(source_id="source-001", title="A", content="Evidence linked reports are local.", origin="fixture-a"),
        SourceDocument(source_id="source-002", title="B", content="  evidence   LINKED reports are local.  ", origin="fixture-b"),
        SourceDocument(source_id="source-003", title="C", content="Human review is required.", origin="fixture-c"),
        SourceDocument(source_id="source-004", title="D", content="Human review is required.\n", origin="fixture-d"),
        SourceDocument(source_id="source-005", title="E", content="A distinct source remains distinct.", origin="fixture-e"),
    ]
    groups = find_duplicate_sources(sources)
    checks = {
        "normalization_case_whitespace_insensitive": normalize_source_content(sources[0].content) == normalize_source_content(sources[1].content),
        "fingerprints_match_normalized_duplicates": source_fingerprint(sources[0]) == source_fingerprint(sources[1]),
        "distinct_fingerprint_differs": source_fingerprint(sources[0]) != source_fingerprint(sources[4]),
        "two_duplicate_groups_found": len(groups) == 2,
        "groups_deterministically_ordered": [group.source_ids for group in groups] == [
            ("source-001", "source-002"),
            ("source-003", "source-004"),
        ],
        "fingerprints_are_sha256": all(len(group.fingerprint) == 64 for group in groups),
        "input_sources_unchanged": [source.source_id for source in sources] == [
            "source-001", "source-002", "source-003", "source-004", "source-005"
        ],
        "unique_sources_return_no_groups": find_duplicate_sources([sources[0], sources[2], sources[4]]) == (),
        "duplicate_ids_rejected": expect_value_error(
            lambda: find_duplicate_sources([sources[0], sources[0]]),
            "source IDs must be unique",
        ),
    }
    report = {
        "ok": all(checks.values()),
        "checks": checks,
        "groups": [
            {"fingerprint": group.fingerprint, "source_ids": list(group.source_ids)}
            for group in groups
        ],
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "report.md").write_text(
        "# Duplicate source detection proof\n\n"
        + "\n".join(f"- {'PASS' if value else 'FAIL'} `{name}`" for name, value in checks.items())
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
