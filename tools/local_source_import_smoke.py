from __future__ import annotations

import inspect
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "local-source-import"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import (
    SUPPORTED_LOCAL_SOURCE_SUFFIXES,
    import_local_source,
)


def expect_value_error(fn, text: str) -> bool:
    try:
        fn()
    except ValueError as exc:
        return text in str(exc)
    return False


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    temp_root = Path(tempfile.mkdtemp(prefix="ytis-import-", dir=OUT))
    allowed = temp_root / "allowed"
    outside = temp_root / "outside"
    allowed.mkdir()
    outside.mkdir()

    text_path = allowed / "architecture.txt"
    text_path.write_text("The platform supports local evidence imports.", encoding="utf-8")
    markdown_path = allowed / "role.md"
    markdown_path.write_text("# Role\n\nHuman review is required.", encoding="utf-8")
    unsupported_path = allowed / "data.csv"
    unsupported_path.write_text("value", encoding="utf-8")
    binary_path = allowed / "binary.txt"
    binary_path.write_bytes(b"\xff\xfe\x00")
    oversized_path = allowed / "large.txt"
    oversized_path.write_text("x" * 33, encoding="utf-8")
    outside_path = outside / "outside.txt"
    outside_path.write_text("Outside root.", encoding="utf-8")

    imported = import_local_source(
        text_path,
        source_id="source-001",
        allowed_root=allowed,
    )
    imported_markdown = import_local_source(
        markdown_path,
        source_id="source-002",
        title="Role requirements",
        source_type="job-description",
        allowed_root=allowed,
    )

    symlink_path = allowed / "linked.txt"
    symlink_functionally_checked = False
    symlink_rejected = False
    try:
        symlink_path.symlink_to(outside_path)
        symlink_functionally_checked = True
        symlink_rejected = expect_value_error(
            lambda: import_local_source(symlink_path, source_id="linked", allowed_root=allowed),
            "symbolic links are not supported",
        )
    except (OSError, NotImplementedError):
        pass

    checks = {
        "supported_suffixes_exact": SUPPORTED_LOCAL_SOURCE_SUFFIXES == (".txt", ".md", ".markdown"),
        "text_imported": imported.content == "The platform supports local evidence imports.",
        "default_title_from_stem": imported.title == "architecture",
        "default_type_document_notes": imported.source_type == "document-notes",
        "origin_is_resolved_path": imported.origin == str(text_path.resolve()),
        "markdown_imported": imported_markdown.content.startswith("# Role"),
        "explicit_title_preserved": imported_markdown.title == "Role requirements",
        "explicit_type_preserved": imported_markdown.source_type == "job-description",
        "outside_root_rejected": expect_value_error(
            lambda: import_local_source(outside_path, source_id="outside", allowed_root=allowed),
            "outside allowed_root",
        ),
        "unsupported_extension_rejected": expect_value_error(
            lambda: import_local_source(unsupported_path, source_id="csv", allowed_root=allowed),
            "unsupported local source extension",
        ),
        "invalid_utf8_rejected": expect_value_error(
            lambda: import_local_source(binary_path, source_id="binary", allowed_root=allowed),
            "valid UTF-8",
        ),
        "oversized_rejected": expect_value_error(
            lambda: import_local_source(oversized_path, source_id="large", allowed_root=allowed, max_bytes=32),
            "exceeds maximum size",
        ),
        "missing_file_rejected": expect_value_error(
            lambda: import_local_source(allowed / "missing.txt", source_id="missing", allowed_root=allowed),
            "local source not found",
        ),
        "invalid_max_bytes_rejected": expect_value_error(
            lambda: import_local_source(text_path, source_id="bad-size", allowed_root=allowed, max_bytes=0),
            "max_bytes must be positive",
        ),
        "symlink_guard_declared": "is_symlink" in inspect.getsource(import_local_source),
        "symlink_rejected_when_supported": (not symlink_functionally_checked) or symlink_rejected,
    }
    report = {
        "ok": all(checks.values()),
        "checks": checks,
        "symlink_functionally_checked": symlink_functionally_checked,
        "imported": {
            "text": imported.to_dict() if hasattr(imported, "to_dict") else {
                "source_id": imported.source_id,
                "title": imported.title,
                "source_type": imported.source_type,
                "origin": imported.origin,
            },
            "markdown": {
                "source_id": imported_markdown.source_id,
                "title": imported_markdown.title,
                "source_type": imported_markdown.source_type,
                "origin": imported_markdown.origin,
            },
        },
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "report.md").write_text(
        "# Local source import proof\n\n"
        + "\n".join(f"- {'PASS' if value else 'FAIL'} `{name}`" for name, value in checks.items())
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
