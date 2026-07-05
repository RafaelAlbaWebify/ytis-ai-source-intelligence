from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ytis.core.io_utils import atomic_write_json, atomic_write_text, now_stamp, unique_child_path


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


@dataclass(frozen=True)
class CardTemplate:
    key: str
    title: str
    card_type: str
    status: str
    tags: list[str]
    content: str


WEBIFY_QUICK_TEMPLATES = [
    CardTemplate(
        key="lost_lead_recovery_audit",
        title="Lost Lead Recovery Audit",
        card_type="Service idea",
        status="Use",
        tags=["Webify", "offer", "lost leads", "validation"],
        content=(
            "## Purpose\n"
            "A small diagnostic offer that checks whether a business is losing website enquiries after the visitor submits a form or tries to contact the company.\n\n"
            "## When to use\n"
            "Use this when a small business depends on website enquiries but cannot prove that every enquiry reaches the right person and gets a timely response.\n\n"
            "## Target business\n"
            "Best initial targets are clinics, dentists, physiotherapists, legal/accounting firms, trades, training academies, and small B2B service companies. Prioritize businesses where one missed lead has meaningful value.\n\n"
            "## Evidence/source\n"
            "Created from the Webify service ideas mission, especially Step 5 - Validation plan. The reusable finding is that the offer should focus on operational reliability: form, inbox, owner, response, and follow-up.\n\n"
            "## Core promise\n"
            "I help small businesses check whether website enquiries are being lost because of broken forms, email routing problems, unclear ownership, or weak follow-up.\n\n"
            "## Operational checklist\n"
            "1. Identify all website enquiry paths.\n"
            "2. Submit controlled test enquiries.\n"
            "3. Confirm the expected recipient receives them.\n"
            "4. Check inbox, spam/junk, promotions, shared mailboxes, and aliases.\n"
            "5. Review basic DNS/email clues such as SPF, DKIM, DMARC, and sender domain alignment at a high level.\n"
            "6. Confirm who owns the first response.\n"
            "7. Record current response-time practice.\n"
            "8. Rate risk as green, amber, or red.\n"
            "9. Produce a short fix plan and lead response checklist.\n\n"
            "## Boundaries / what not to promise\n"
            "Do not sell this as web design, SEO, ads, cybersecurity, cloud architecture, DBA work, custom development, or an AI agency service. Keep it as an operations and reliability audit.\n\n"
            "## Deliverable\n"
            "Short report with tested paths, delivery result, ownership gap, response risk, email/domain observations, risk rating, and recommended next actions. Optional 30-minute review call.\n\n"
            "## Pricing / validation hypothesis\n"
            "Test starter prices such as EUR 97 for a basic check, EUR 197 with a written response runbook, and EUR 297-497 when coordination, retest, and handover are included. Treat these as hypotheses, not proven prices.\n\n"
            "## Next action\n"
            "Use this card to create a pilot checklist and contact 10 local businesses. Record whether they recognize the problem, accept a pilot, and find the report useful.\n"
        ),
    ),
    CardTemplate(
        key="website_to_inbox_reliability_check",
        title="Website-to-Inbox Reliability Check",
        card_type="Workflow",
        status="Use",
        tags=["Webify", "workflow", "email", "forms"],
        content=(
            "## Purpose\n"
            "A repeatable workflow for proving whether website enquiries travel reliably from the public website to the mailbox and first-response owner.\n\n"
            "## When to use\n"
            "Use this during a Lost Lead Recovery Audit, before proposing any larger fix, redesign, CRM, or marketing work.\n\n"
            "## Inputs needed\n"
            "- Website URL.\n"
            "- Contact form URL or enquiry paths.\n"
            "- Expected recipient mailbox or shared mailbox.\n"
            "- Business email domain.\n"
            "- Current owner of first response.\n"
            "- Any known history of missed leads, spam issues, or slow replies.\n\n"
            "## Operational checklist\n"
            "1. Identify the main website enquiry paths.\n"
            "2. Submit a controlled test enquiry with a clear subject/body marker.\n"
            "3. Confirm whether the expected recipient receives it.\n"
            "4. Check where it lands: inbox, spam/junk, promotions, quarantine, shared mailbox, or forwarding target.\n"
            "5. Confirm whether the notification contains enough useful lead data.\n"
            "6. Confirm who owns the first response.\n"
            "7. Record response-time target and current practice.\n"
            "8. Review obvious SPF, DKIM, DMARC, MX, and routing clues without positioning as a deep email security audit.\n"
            "9. Record evidence: timestamp, sender, recipient, screenshot or notes, and result.\n"
            "10. Produce a risk rating: green, amber, or red.\n\n"
            "## Risk rating guide\n"
            "Green: test enquiry arrived in the expected place and ownership is clear.\n"
            "Amber: enquiry arrived but there is uncertainty, weak ownership, spam risk, slow process, or poor tracking.\n"
            "Red: form fails, enquiry goes missing, recipient is wrong, mail lands in spam without monitoring, or no owner exists.\n\n"
            "## Boundaries / what not to promise\n"
            "Do not promise full deliverability engineering, email security certification, CRM implementation, or website redesign. Escalate or partner if the fix requires deep hosting, DNS, developer, or email-admin access.\n\n"
            "## Deliverable\n"
            "A short reliability note that shows what was tested, what happened, the risk rating, and the next practical fix.\n\n"
            "## Next action\n"
            "Turn this workflow into the first page of the audit report template and use it in every pilot.\n"
        ),
    ),
    CardTemplate(
        key="lead_response_runbook",
        title="Lead Response Runbook",
        card_type="Workflow",
        status="Validate",
        tags=["Webify", "runbook", "follow-up", "operations"],
        content=(
            "## Purpose\n"
            "A simple operating procedure for handling new website enquiries after the technical path has been checked.\n\n"
            "## When to use\n"
            "Use this when the enquiry technically arrives, but ownership, timing, backup coverage, or follow-up discipline is weak.\n\n"
            "## Target business\n"
            "Small businesses that rely on inboxes rather than a mature CRM, especially where leads are handled by an owner, receptionist, office manager, or shared mailbox.\n\n"
            "## Evidence/source\n"
            "Created from the Webify mission finding that lost leads can be operational, not only technical: the email may arrive but still be ignored, delayed, or owned by nobody.\n\n"
            "## Runbook\n"
            "1. Define the lead owner: one named person or shared mailbox owner.\n"
            "2. Define backup owner for holidays, sickness, and busy periods.\n"
            "3. Check new enquiries at least twice per working day, or define a stricter target if leads are high value.\n"
            "4. Set response target: for example same business day, under 4 hours, or under 1 hour depending on business type.\n"
            "5. Use a simple response template for first acknowledgement.\n"
            "6. Log date, lead source, customer name, response status, next action, and owner.\n"
            "7. Escalate immediately if the form fails, notifications stop, or enquiries land in spam.\n"
            "8. Retest the website form after website, DNS, email, plugin, or hosting changes.\n\n"
            "## Boundaries / what not to promise\n"
            "Do not turn this into a full CRM consultancy unless a clear paid follow-on service is defined. Keep the first version as a lightweight operating runbook.\n\n"
            "## Deliverable\n"
            "One-page lead response checklist plus owner/backup owner table.\n\n"
            "## Validation signal\n"
            "Strong signal if the business says: 'We do not have this written down' or 'Sometimes nobody knows who should answer.'\n\n"
            "## Next action\n"
            "Use this as the recommended add-on after the Website-to-Inbox Reliability Check.\n"
        ),
    ),
    CardTemplate(
        key="do_not_position_as_generic_agency",
        title="Do not position as generic agency",
        card_type="Warning",
        status="Use",
        tags=["Webify", "positioning", "guardrail"],
        content=(
            "## Purpose\n"
            "A positioning guardrail to keep Webify aligned with Rafael's real credibility and avoid overclaiming.\n\n"
            "## Do not position Rafael/Webify as\n"
            "- Generic developer.\n"
            "- Software agency.\n"
            "- Cybersecurity expert.\n"
            "- Cloud architect.\n"
            "- DBA.\n"
            "- Generic web designer.\n"
            "- AI agency.\n\n"
            "## Better positioning\n"
            "Use operations and support language: lost enquiries, broken forms, email routing, mailbox ownership, response time, troubleshooting, documentation, runbooks, and practical fix plans.\n\n"
            "## Why this matters\n"
            "The offer is credible because Rafael has real experience in IT operations, application support, Microsoft 365, DNS/email basics, incident management, escalation, documentation, and troubleshooting under production pressure.\n\n"
            "## Acceptable promise\n"
            "I check whether enquiries can be lost between your website form, mailbox, owner, and follow-up process, then give you a practical fix plan.\n\n"
            "## Red-flag promises to avoid\n"
            "- I will redesign your full website.\n"
            "- I will guarantee deliverability.\n"
            "- I will secure your email/domain.\n"
            "- I will build a CRM.\n"
            "- I will automate your whole business with AI.\n\n"
            "## Next action\n"
            "Review every Webify page, outreach message, and report introduction against this guardrail before publishing or sending.\n"
        ),
    ),
    CardTemplate(
        key="validate_with_10_local_businesses",
        title="Validate with 10 local businesses",
        card_type="Validation task",
        status="Validate",
        tags=["Webify", "validation", "outreach"],
        content=(
            "## Purpose\n"
            "A small market test to learn whether business owners care about hidden website enquiry loss before building a bigger service or website.\n\n"
            "## Target sample\n"
            "Talk to 10 small businesses where one missed enquiry has meaningful value. Prioritize clinics, dentists, physiotherapists, legal/accounting firms, trades, training academies, and small B2B service companies.\n\n"
            "## Discovery questions\n"
            "1. When someone fills your website contact form, who receives it?\n"
            "2. Do you know if every form submission reaches the right inbox?\n"
            "3. Have you ever discovered an enquiry late?\n"
            "4. Do enquiries ever go to spam or the wrong person?\n"
            "5. How quickly do you normally reply to a new website enquiry?\n"
            "6. Is one person responsible for checking new leads?\n"
            "7. Do you track missed enquiries?\n"
            "8. When was the last time someone tested your website form?\n"
            "9. Would a short reliability report be useful?\n"
            "10. Would you pay a small fixed fee for that check?\n\n"
            "## Success criteria\n"
            "- At least 5 out of 10 recognize the risk as relevant.\n"
            "- At least 3 agree to a pilot audit.\n"
            "- At least 2 pilots reveal real issues or meaningful uncertainty.\n"
            "- At least 1 business is willing to pay or says the proposed price is reasonable.\n"
            "- Manual delivery takes less than 2 to 3 hours per audit.\n\n"
            "## Failure criteria\n"
            "Reject or rework the offer if businesses do not care, see it as generic web design, expect free technical support, or if the audit takes too long to deliver.\n\n"
            "## Evidence to record\n"
            "Record business type, role spoken to, pain level, real story, pilot acceptance, price reaction, and objections.\n\n"
            "## Next action\n"
            "Create a 20-business target list, contact 10, and record the result in YTIS as validation evidence.\n"
        ),
    ),
    CardTemplate(
        key="outreach_script_v1",
        title="Outreach script v1",
        card_type="Outreach script",
        status="Validate",
        tags=["Webify", "outreach", "script", "validation"],
        content=(
            "## Purpose\n"
            "A simple first-contact message for testing the Lost Lead Recovery Audit without sounding like a generic agency pitch.\n\n"
            "## Short message\n"
            "Hi, I am testing a small service for local businesses. It checks whether website enquiries are being lost because of broken contact forms, email delivery problems, unclear ownership, or slow follow-up. I am not selling web design or ads. I am looking for a few businesses willing to let me run a simple enquiry reliability check and give them a short report. Would this be useful for your business?\n\n"
            "## More direct version\n"
            "Hi, quick question: do you know for sure that every enquiry from your website contact form reaches the right inbox and gets answered quickly? I am testing a small fixed-scope check for this and looking for a few pilot businesses.\n\n"
            "## Call framing\n"
            "I am trying to understand whether small businesses have hidden problems between the website form and the actual follow-up. I am not assuming your website is broken. I am checking the chain: form, inbox, ownership, response, and tracking.\n\n"
            "## Follow-up question\n"
            "When was the last time someone tested your contact form and confirmed where the enquiry lands?\n\n"
            "## Boundaries / what not to imply\n"
            "Do not imply that the business is definitely losing leads. Do not pitch a redesign, ads, SEO, cybersecurity, or automation. Keep the message diagnostic and low pressure.\n\n"
            "## Validation signal\n"
            "Strong signal if the owner says they are not sure, tells a story about missed enquiries, or agrees to a pilot check.\n\n"
            "## Next action\n"
            "Send to 10 targeted businesses and record reply rate, objections, and pilot acceptance.\n"
        ),
    ),
]

def template_titles() -> list[str]:
    return [template.title for template in WEBIFY_QUICK_TEMPLATES]


def get_template_by_title(title: str) -> CardTemplate | None:
    wanted = (title or "").strip().lower()
    for template in WEBIFY_QUICK_TEMPLATES:
        if template.title.lower() == wanted or template.key.lower() == wanted:
            return template
    return None


def create_template_cards(
    project_root: Path,
    templates: list[CardTemplate] | None = None,
    mission_id: str = "",
    mission_name: str = "",
    source_analysis_id: str = "",
    source_analysis_title: str = "",
) -> tuple[list[KnowledgeCard], list[str]]:
    selected_templates = templates or WEBIFY_QUICK_TEMPLATES
    existing_titles = {card.title.strip().lower() for card in list_cards(project_root)}
    created: list[KnowledgeCard] = []
    skipped: list[str] = []
    for template in selected_templates:
        key = template.title.strip().lower()
        if key in existing_titles:
            skipped.append(template.title)
            continue
        card = save_card(
            project_root=project_root,
            title=template.title,
            card_type=template.card_type,
            content=template.content,
            tags=template.tags,
            status=template.status,
            mission_id=mission_id,
            mission_name=mission_name,
            source_analysis_id=source_analysis_id,
            source_analysis_title=source_analysis_title,
        )
        created.append(card)
        existing_titles.add(key)
    return created, skipped


def _find_card_by_title(project_root: Path, title: str) -> KnowledgeCard | None:
    wanted = title.strip().lower()
    for card in list_cards(project_root):
        if card.title.strip().lower() == wanted:
            return card
    return None


def update_card_from_template(
    card: KnowledgeCard,
    template: CardTemplate,
    mission_id: str = "",
    mission_name: str = "",
    source_analysis_id: str = "",
    source_analysis_title: str = "",
) -> KnowledgeCard:
    data = json.loads(card.metadata_path.read_text(encoding="utf-8-sig"))
    created_at = str(data.get("created_at") or card.created_at or _now())
    updated_at = _now()
    clean_tags = parse_tags(template.tags)
    effective_mission_id = mission_id or str(data.get("mission_id") or card.mission_id or "")
    effective_mission_name = mission_name or str(data.get("mission_name") or card.mission_name or "")
    effective_source_id = source_analysis_id or str(data.get("source_analysis_id") or card.source_analysis_id or "")
    effective_source_title = source_analysis_title or str(data.get("source_analysis_title") or card.source_analysis_title or "")

    atomic_write_text(
        card.card_path,
        _compose_card_markdown(
            title=template.title,
            card_type=template.card_type,
            status=template.status,
            created_at=created_at,
            updated_at=updated_at,
            tags=clean_tags,
            body=template.content,
            mission_id=effective_mission_id,
            mission_name=effective_mission_name,
            source_analysis_id=effective_source_id,
            source_analysis_title=effective_source_title,
        ),
        encoding="utf-8",
    )
    data.update({
        "title": template.title,
        "card_type": template.card_type,
        "status": template.status,
        "tags": clean_tags,
        "mission_id": effective_mission_id,
        "mission_name": effective_mission_name,
        "source_analysis_id": effective_source_id,
        "source_analysis_title": effective_source_title,
        "updated_at": updated_at,
        "summary": _summary(template.content),
    })
    atomic_write_json(card.metadata_path, data)
    return _card_from_data(card.folder, data)


def upgrade_template_cards(
    project_root: Path,
    templates: list[CardTemplate] | None = None,
    mission_id: str = "",
    mission_name: str = "",
    source_analysis_id: str = "",
    source_analysis_title: str = "",
) -> tuple[list[KnowledgeCard], list[str]]:
    selected_templates = templates or WEBIFY_QUICK_TEMPLATES
    upgraded: list[KnowledgeCard] = []
    missing: list[str] = []
    for template in selected_templates:
        card = _find_card_by_title(project_root, template.title)
        if not card:
            missing.append(template.title)
            continue
        upgraded.append(update_card_from_template(
            card=card,
            template=template,
            mission_id=mission_id,
            mission_name=mission_name,
            source_analysis_id=source_analysis_id,
            source_analysis_title=source_analysis_title,
        ))
    return upgraded, missing


def build_card_content_from_analysis(record: Any, analysis_text: str) -> str:
    return (
        f"## Purpose\n"
        f"Capture a reusable point from a completed YTIS/ChatGPT analysis so it can be reviewed, validated, and reused later.\n\n"
        f"## Source context\n"
        f"Source analysis: {getattr(record, 'title', '')}\n\n"
        f"Mission: {getattr(record, 'mission_name', '') or '-'}\n"
        f"Topic: {getattr(record, 'topic', '') or '-'}\n"
        f"Focus: {getattr(record, 'focus_preset', '') or '-'}\n"
        f"Prompt-chain step: {getattr(record, 'chain_step', '') or '-'}\n\n"
        f"## Evidence / summary\n"
        f"{getattr(record, 'summary', '') or '-'}\n\n"
        f"## Reusable point to extract\n"
        f"State the reusable service idea, workflow, warning, validation task, script, or evidence note from this source.\n\n"
        f"## Why it matters\n"
        f"Explain how this point changes a future decision, workflow, offer, outreach message, or guardrail.\n\n"
        f"## Boundaries / uncertainty\n"
        f"List what this source does not prove yet and what must be validated before reuse.\n\n"
        f"## Next action\n"
        f"Define the next practical step: validate, use, archive, or turn into a more specific card.\n\n"
        f"## Source excerpt / full answer\n"
        f"{analysis_text.strip()}\n"
    )


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
    return now_stamp()


def _summary(text: str, max_chars: int = 220) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if len(clean) <= max_chars:
        return clean
    return clean[:max_chars].rstrip() + "..."


def _compose_card_markdown(
    title: str,
    card_type: str,
    status: str,
    created_at: str,
    tags: list[str],
    body: str,
    mission_id: str = "",
    mission_name: str = "",
    source_analysis_id: str = "",
    source_analysis_title: str = "",
    updated_at: str = "",
) -> str:
    md = f"# {title}\n\n"
    md += f"Type: {card_type or 'Other'}\n\n"
    md += f"Status: {status or 'Draft'}\n\n"
    md += f"Created: {created_at}\n\n"
    if updated_at and updated_at != created_at:
        md += f"Updated: {updated_at}\n\n"
    md += f"Tags: {', '.join(tags) if tags else '-'}\n\n"
    if mission_name or mission_id:
        md += f"Mission: {mission_name or '-'}\n\n"
        md += f"Mission ID: `{mission_id or '-'}`\n\n"
    if source_analysis_title or source_analysis_id:
        md += f"Source analysis: {source_analysis_title or '-'}\n\n"
        md += f"Source analysis ID: `{source_analysis_id or '-'}`\n\n"
    md += "---\n\n"
    md += body.strip() + "\n"
    return md


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
    card_stem = f"{_stamp()}_{safe_slug(title_clean)}"
    folder = unique_child_path(cards_root(project_root), card_stem)
    folder.mkdir(parents=True, exist_ok=False)
    card_id = folder.name

    clean_tags = parse_tags(tags)
    card_path = folder / "card.md"
    metadata_path = folder / "metadata.json"

    body = content.strip()
    md = _compose_card_markdown(
        title=title_clean,
        card_type=card_type or "Other",
        status=status or "Draft",
        created_at=created_at,
        tags=clean_tags,
        body=body,
        mission_id=mission_id,
        mission_name=mission_name,
        source_analysis_id=source_analysis_id,
        source_analysis_title=source_analysis_title,
    )
    atomic_write_text(card_path, md, encoding="utf-8")

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
    atomic_write_json(metadata_path, metadata)
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
    updated_at = _now()
    data["status"] = status
    data["updated_at"] = updated_at
    atomic_write_json(card.metadata_path, data)

    if card.card_path.exists():
        try:
            text = card.card_path.read_text(encoding="utf-8-sig", errors="replace")
            text = re.sub(r"^Status: .*?$", f"Status: {status}", text, count=1, flags=re.M)
            if re.search(r"^Updated: .*?$", text, flags=re.M):
                text = re.sub(r"^Updated: .*?$", f"Updated: {updated_at}", text, count=1, flags=re.M)
            else:
                text = re.sub(r"^(Created: .*?\n\n)", r"\1" + f"Updated: {updated_at}\n\n", text, count=1, flags=re.M)
            atomic_write_text(card.card_path, text, encoding="utf-8")
        except Exception:
            pass


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
