from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "source-pack-editing"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import SourceDocument, edit_source, move_source


def expect_value_error(fn, text: str) -> bool:
    try:
        fn()
    except ValueError as exc:
        return text in str(exc)
    return False


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    original = (
        SourceDocument(
            source_id="source-001",
            title="Architecture note",
            content="Original capability evidence.",
            source_type="technical-note",
            origin="fixture-a",
        ),
        SourceDocument(
            source_id="source-002",
            title="Role note",
            content="Original role evidence.",
            source_type="job-description",
            origin="fixture-b",
        ),
        SourceDocument(
            source_id="source-003",
            title="Article note",
            content="Original article evidence.",
            source_type="article-notes",
            origin="fixture-c",
        ),
    )

    edited = edit_source(
        original,
        source_id="source-002",
        title="Updated role note",
        content="Updated role evidence.",
        origin="fixture-b-updated",
    )
    moved = move_source(edited, source_id="source-003", target_index=0)
    unchanged_move = move_source(moved, source_id="source-001", target_index=1)

    checks = {
        "edit_preserves_ids": [source.source_id for source in edited]
        == ["source-001", "source-002", "source-003"],
        "edit_preserves_position": edited[1].source_id == "source-002",
        "edit_updates_requested_fields": (
            edited[1].title == "Updated role note"
            and edited[1].content == "Updated role evidence."
            and edited[1].origin == "fixture-b-updated"
        ),
        "edit_preserves_unspecified_type": edited[1].source_type == "job-description",
        "edit_does_not_mutate_input": original[1].title == "Role note" and original[1].origin == "fixture-b",
        "move_changes_order_only": [source.source_id for source in moved]
        == ["source-003", "source-001", "source-002"],
        "move_preserves_all_fields": {source.source_id: asdict(source) for source in moved}
        == {source.source_id: asdict(source) for source in edited},
        "move_to_same_position_stable": unchanged_move == moved,
        "unknown_edit_rejected": expect_value_error(
            lambda: edit_source(original, source_id="missing", title="Missing"),
            "unknown source",
        ),
        "unknown_move_rejected": expect_value_error(
            lambda: move_source(original, source_id="missing", target_index=0),
            "unknown source",
        ),
        "negative_index_rejected": expect_value_error(
            lambda: move_source(original, source_id="source-001", target_index=-1),
            "out of range",
        ),
        "large_index_rejected": expect_value_error(
            lambda: move_source(original, source_id="source-001", target_index=3),
            "out of range",
        ),
        "invalid_edit_content_rejected": expect_value_error(
            lambda: edit_source(original, source_id="source-001", content=" "),
            "content is required",
        ),
        "duplicate_ids_rejected": expect_value_error(
            lambda: edit_source((original[0], original[0]), source_id="source-001", title="Duplicate"),
            "source IDs must be unique",
        ),
    }
    report = {
        "ok": all(checks.values()),
        "checks": checks,
        "edited_order": [source.source_id for source in edited],
        "moved_order": [source.source_id for source in moved],
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "report.md").write_text(
        "# Source pack editing and reordering proof\n\n"
        + "\n".join(f"- {'PASS' if value else 'FAIL'} `{name}`" for name, value in checks.items())
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
