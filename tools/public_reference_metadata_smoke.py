from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "artifacts" / "public-reference-metadata"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ytis.research import capture_public_reference


def rejected(value: str, expected: str) -> bool:
    try:
        capture_public_reference(value)
    except ValueError as exc:
        return expected in str(exc)
    return False


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    metadata = capture_public_reference(" HTTPS://Example.COM:443/path?q=1#fragment ")
    explicit_port = capture_public_reference("http://example.com:8080/")
    checks = {
        "normalizes_url": metadata.normalized_url == "https://example.com/path?q=1",
        "captures_host": metadata.host == "example.com",
        "removes_default_port": metadata.port is None,
        "preserves_query": metadata.query == "q=1",
        "removes_fragment": "#" not in metadata.normalized_url,
        "keeps_non_default_port": explicit_port.port == 8080 and ":8080" in explicit_port.normalized_url,
        "rejects_blank": rejected(" ", "required"),
        "rejects_non_http": rejected("file:///tmp/a.txt", "http or https"),
        "rejects_credentials": rejected("https://user:pass@example.com/", "credentials"),
        "rejects_missing_host": rejected("https:///path", "host"),
        "rejects_invalid_port": rejected("https://example.com:bad/", "invalid port"),
    }
    result = {"ok": all(checks.values()), "checks": checks, "metadata": metadata.to_dict()}
    (OUT / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
