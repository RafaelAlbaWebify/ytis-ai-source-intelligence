from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


CARD_TYPES = [
    "Service idea",
    "Workflow",
    "Warning",
    "Validation task",
    "Action item",
    "Pricing clue",
    "Outreach script",
    "Evidence note",
    "Other",
]

CARD_STATUS = [
    "Draft",
    "Review",
    "Validate",
    "Use",
    "Archived",
]


@dataclass
class KnowledgeCard:
    card_id: str
    title: str
    card_type: str
    status: str
    tags: list[str]
    mission_id: str
    mission_name: str
    source_analysis_id: str
    source_analysis_title: str
    created_at: str
    updated_at: str
    folder: Path
    card_path: Path
    metadata_path: Path
    summary: str


def safe_slug(text: str, fallback: str = "card") -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip())
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:80] or fallback


def cards_root(project_root: Path) -> Path:
    path = project_root / "knowledge_cards"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _summary(text: str, max_chars: int = 220) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if len(clean) <= max_chars:
        return clean
    return clean[:max_chars].rstrip() + "..."


def parse_tags(raw: str | list[str]) -> list[str]:
    if isinstance(raw, list):
        items = raw
    else:
        items = re.split(r"[,;#\n]+", raw or "")
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        clean = str(item).strip()
        if not clean:
            continue
        key = clean.lower()
        if key not in seen:
            result.append(clean)
            seen.add(key)
    return result


def save_card(
    project_root: Path,
    title: str,
    card_type: str,
    content: str,
    tags: list[str] | str,
    status: str = "Draft",
    mission_id: str = "",
    mission_name: str = "",
    source_analysis_id: str = "",
    source_analysis_title: str = "",
) -> KnowledgeCard:
    created_at = _now()
    title_clean = title.strip() or "Untitled card"
    card_id = f"{_stamp()}_{safe_slug(title_clean)}"
    folder = cards_root(project_root) / card_id
    folder.mkdir(parents=True, exist_ok=True)

    clean_tags = parse_tags(tags)
    card_path = folder / "card.md"
    metadata_path = folder / "metadata.json"

    body = content.strip()
    md = f"# {title_clean}\n\n"
    md += f"Type: {card_type or 'Other'}\n\n"
    md += f"Status: {status or 'Draft'}\n\n"
    md += f"Created: {created_at}\n\n"
    md += f"Tags: {', '.join(clean_tags) if clean_tags else '-'}\n\n"
    if mission_name or mission_id:
        md += f"Mission: {mission_name or '-'}\n\n"
        md += f"Mission ID: `{mission_id or '-'}`\n\n"
    if source_analysis_title or source_analysis_id:
        md += f"Source analysis: {source_analysis_title or '-'}\n\n"
        md += f"Source analysis ID: `{source_analysis_id or '-'}`\n\n"
    md += "---\n\n"
    md += body + "\n"
    card_path.write_text(md, encoding="utf-8")

    metadata = {
        "card_id": card_id,
        "title": title_clean,
        "card_type": card_type or "Other",
        "status": status or "Draft",
        "tags": clean_tags,
        "mission_id": mission_id,
        "mission_name": mission_name,
        "source_analysis_id": source_analysis_id,
        "source_analysis_title": source_analysis_title,
        "created_at": created_at,
        "updated_at": created_at,
        "card_path": str(card_path),
        "summary": _summary(body),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return _card_from_data(folder, metadata)


def _card_from_data(folder: Path, data: dict[str, Any]) -> KnowledgeCard:
    return KnowledgeCard(
        card_id=str(data.get("card_id") or folder.name),
        title=str(data.get("title") or folder.name),
        card_type=str(data.get("card_type") or "Other"),
        status=str(data.get("status") or "Draft"),
        tags=list(data.get("tags") or []),
        mission_id=str(data.get("mission_id") or ""),
        mission_name=str(data.get("mission_name") or ""),
        source_analysis_id=str(data.get("source_analysis_id") or ""),
        source_analysis_title=str(data.get("source_analysis_title") or ""),
        created_at=str(data.get("created_at") or ""),
        updated_at=str(data.get("updated_at") or ""),
        folder=folder,
        card_path=folder / "card.md",
        metadata_path=folder / "metadata.json",
        summary=str(data.get("summary") or ""),
    )


def _card_from_folder(folder: Path) -> KnowledgeCard | None:
    metadata_path = folder / "metadata.json"
    card_path = folder / "card.md"
    if not metadata_path.exists() or not card_path.exists():
        return None
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        return _card_from_data(folder, data)
    except Exception:
        return None


def list_cards(project_root: Path) -> list[KnowledgeCard]:
    root = cards_root(project_root)
    cards: list[KnowledgeCard] = []
    for folder in sorted(root.iterdir(), reverse=True):
        if folder.is_dir():
            card = _card_from_folder(folder)
            if card:
                cards.append(card)
    return cards


def read_card(card: KnowledgeCard) -> str:
    try:
        return card.card_path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return ""


def filter_cards(
    cards: list[KnowledgeCard],
    card_type: str = "All types",
    status: str = "All status",
    text: str = "",
) -> list[KnowledgeCard]:
    result = cards
    if card_type and card_type != "All types":
        result = [c for c in result if c.card_type == card_type]
    if status and status != "All status":
        result = [c for c in result if c.status == status]
    if text.strip():
        q = text.lower().strip()
        result = [
            c for c in result
            if q in c.title.lower()
            or q in c.summary.lower()
            or q in c.card_type.lower()
            or q in c.status.lower()
            or q in " ".join(c.tags).lower()
            or q in c.mission_name.lower()
            or q in c.source_analysis_title.lower()
        ]
    return result


def card_stats(cards: list[KnowledgeCard]) -> dict[str, Any]:
    types = sorted({c.card_type for c in cards})
    statuses = sorted({c.status for c in cards})
    tags = sorted({tag for c in cards for tag in c.tags})
    return {
        "cards": len(cards),
        "types": len(types),
        "statuses": len(statuses),
        "tags": len(tags),
        "validate": sum(1 for c in cards if c.status == "Validate"),
        "use": sum(1 for c in cards if c.status == "Use"),
        "draft": sum(1 for c in cards if c.status == "Draft"),
    }


def update_card_status(card: KnowledgeCard, status: str) -> None:
    data = json.loads(card.metadata_path.read_text(encoding="utf-8-sig"))
    data["status"] = status
    data["updated_at"] = _now()
    card.metadata_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def export_cards_zip(cards: list[KnowledgeCard], downloads_dir: Path, name: str = "YTIS_KNOWLEDGE_CARDS") -> Path:
    downloads_dir.mkdir(parents=True, exist_ok=True)
    zip_path = downloads_dir / f"{safe_slug(name)}_{_stamp()}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest: list[dict[str, Any]] = []
        for card in cards:
            base = f"{card.card_id}/"
            if card.card_path.exists():
                zf.write(card.card_path, base + "card.md")
            if card.metadata_path.exists():
                zf.write(card.metadata_path, base + "metadata.json")
            manifest.append({
                "card_id": card.card_id,
                "title": card.title,
                "card_type": card.card_type,
                "status": card.status,
                "tags": card.tags,
                "mission_name": card.mission_name,
                "source_analysis_title": card.source_analysis_title,
                "created_at": card.created_at,
                "summary": card.summary,
            })
        zf.writestr("MANIFEST.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        zf.writestr(
            "README.md",
            "# YTIS Knowledge Cards Export\n\n"
            "This ZIP contains reusable knowledge cards extracted from YTIS research and ChatGPT analyses.\n",
        )
    return zip_path
