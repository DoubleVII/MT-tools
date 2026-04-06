from .models import Block, Page, Section
from .normalize import truncate_text


def block_to_text(block: Block) -> str:
    if block.type == "paragraph":
        return block.text or ""

    if block.type == "list":
        items = block.items or []
        return "\n".join(f"- {item}" for item in items)

    if block.type == "table":
        parts = []
        if block.caption:
            parts.append(f"Table: {block.caption}")
        if block.headers:
            parts.append(" | ".join(block.headers))
        if block.rows:
            for row in block.rows:
                parts.append(" | ".join(row))
        return "\n".join(parts)

    return block.text or ""


def render_summary(page: Page, max_chars: int = 2000, include_infobox: bool = True) -> tuple[str, bool]:
    parts = []

    if include_infobox and page.infobox:
        infobox_items = []
        for k, v in list(page.infobox.items())[:8]:
            infobox_items.append(f"{k}: {v}")
        if infobox_items:
            parts.append("Infobox:\n" + "\n".join(infobox_items))

    lead_texts = [block_to_text(b) for b in page.lead_blocks if block_to_text(b)]
    if lead_texts:
        parts.append("\n\n".join(lead_texts))

    content = "\n\n".join(parts).strip()
    return truncate_text(content, max_chars)


def render_outline(page: Page) -> dict:
    return {
        "title": page.title,
        "lang": page.lang,
        "sections": [
            {
                "index": sec.index,
                "level": sec.level,
                "title": sec.title,
                "preview": _section_preview(sec, 240),
                "block_count": len(sec.blocks),
            }
            for sec in page.sections
        ],
    }


def render_section(section: Section, max_chars: int = 2000) -> tuple[str, bool]:
    parts = []
    for block in section.blocks:
        text = block_to_text(block)
        if text:
            parts.append(text)
    content = "\n\n".join(parts).strip()
    return truncate_text(content, max_chars)


def render_blocks(blocks: list[Block], max_chars: int = 2000) -> tuple[str, bool]:
    parts = []
    total = 0

    for block in blocks:
        text = block.text.strip()
        if not text:
            continue

        extra = len(text) + (2 if parts else 0)
        if total + extra > max_chars:
            remain = max_chars - total
            if remain > 0:
                if parts:
                    parts.append("\n\n")
                parts.append(text[:remain])
            return "".join(parts), True

        if parts:
            parts.append("\n\n")
        parts.append(text)
        total += extra

    return "".join(parts), False


def render_full(page: Page, max_chars: int = 4000, include_infobox: bool = True) -> tuple[str, bool]:
    parts = []

    if include_infobox and page.infobox:
        infobox_items = []
        for k, v in list(page.infobox.items())[:12]:
            infobox_items.append(f"{k}: {v}")
        if infobox_items:
            parts.append("Infobox:\n" + "\n".join(infobox_items))

    lead_texts = [block_to_text(b) for b in page.lead_blocks if block_to_text(b)]
    if lead_texts:
        parts.append("Lead:\n" + "\n\n".join(lead_texts))

    for sec in page.sections:
        section_text = []
        for block in sec.blocks:
            txt = block_to_text(block)
            if txt:
                section_text.append(txt)

        if section_text:
            parts.append(f"{sec.title}\n" + "\n\n".join(section_text))

    content = "\n\n".join(parts).strip()
    return truncate_text(content, max_chars)


def _section_preview(section: Section, max_chars: int) -> str:
    texts = []
    for block in section.blocks[:3]:
        txt = block_to_text(block)
        if txt:
            texts.append(txt)
    preview = "\n\n".join(texts).strip()
    preview, _ = truncate_text(preview, max_chars)
    return preview
