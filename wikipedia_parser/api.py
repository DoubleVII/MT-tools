from .extractor import WikipediaHTMLExtractor
from .renderers import render_full, render_outline, render_section, render_summary, render_blocks


def read_wikipedia_html(
    html: str,
    *,
    lang: str | None = None,
    title: str | None = None,
    mode: str = "summary",
    section: str | None = None,
    section_index: int | None = None,
    max_chars: int = 2000,
    include_infobox: bool = True,
) -> dict:
    extractor = WikipediaHTMLExtractor(lang=lang)
    page = extractor.parse_page(html, title=title)

    result = {
        "title": page.title,
        "lang": page.lang,
        "mode": mode,
        "infobox": page.infobox if include_infobox else None,
        "sections": [
            {"index": sec.index, "level": sec.level, "title": sec.title}
            for sec in page.sections
        ],
    }

    if mode == "meta":
        result["content"] = ""
        result["truncated"] = False
        return result

    if mode == "summary":
        content, truncated = render_summary(
            page,
            max_chars=max_chars,
            include_infobox=include_infobox,
        )
        result["content"] = content
        result["truncated"] = truncated
        return result

    if mode == "outline":
        result["outline"] = render_outline(page)["sections"]
        result["content"] = ""
        result["truncated"] = False
        return result

    if mode == "section":
        sec = extractor.find_section(page, section=section, section_index=section_index)
        if sec is None:
            result["error"] = "section_not_found"
            result["content"] = ""
            result["truncated"] = False
            return result

        # content, truncated = render_section(sec, max_chars=max_chars)
        blocks = extractor.collect_section_blocks(page, sec)
        content, truncated = render_blocks(blocks, max_chars=max_chars)

        result["section"] = {
            "index": sec.index,
            "level": sec.level,
            "title": sec.title,
        }
        result["content"] = content
        result["truncated"] = truncated
        return result

    if mode == "full":
        content, truncated = render_full(
            page,
            max_chars=max_chars,
            include_infobox=include_infobox,
        )
        result["content"] = content
        result["truncated"] = truncated
        return result

    if mode == "blocks":
        result["lead_blocks"] = [block.__dict__ for block in page.lead_blocks]
        result["section_blocks"] = [
            {
                "index": sec.index,
                "level": sec.level,
                "title": sec.title,
                "blocks": [block.__dict__ for block in sec.blocks],
            }
            for sec in page.sections
        ]
        result["content"] = ""
        result["truncated"] = False
        return result

    result["error"] = "unsupported_mode"
    result["content"] = ""
    result["truncated"] = False
    return result
