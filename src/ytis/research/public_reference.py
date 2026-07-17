from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit


@dataclass(frozen=True)
class PublicReferenceMetadata:
    normalized_url: str
    scheme: str
    host: str
    port: int | None
    path: str
    query: str

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "normalized_url": self.normalized_url,
            "scheme": self.scheme,
            "host": self.host,
            "port": self.port,
            "path": self.path,
            "query": self.query,
        }


def capture_public_reference(value: str) -> PublicReferenceMetadata:
    """Validate and normalize public-reference metadata without fetching the URL."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError("public reference URL is required")
    raw = value.strip()
    parsed = urlsplit(raw)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("public reference URL must use http or https")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("public reference URL must not contain credentials")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("public reference URL must include a host")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("public reference URL has an invalid port") from exc
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("public reference URL has an invalid port")

    default_port = 80 if scheme == "http" else 443
    netloc = host if port in {None, default_port} else f"{host}:{port}"
    path = parsed.path or "/"
    normalized = urlunsplit(SplitResult(scheme, netloc, path, parsed.query, ""))
    return PublicReferenceMetadata(
        normalized_url=normalized,
        scheme=scheme,
        host=host,
        port=None if port == default_port else port,
        path=path,
        query=parsed.query,
    )
