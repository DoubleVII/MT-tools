from selectolax.parser import HTMLParser, Node

from .models import Block, Page, Section
from .normalize import normalize_multiline_text, normalize_section_title, normalize_text
from .selectors import (
    CONTENT_ROOT_SELECTORS,
    DROP_SELECTORS,
    HEADING_TAGS,
    LIST_TAGS,
    PARAGRAPH_TAGS,
    SKIP_BLOCK_SELECTORS,
)
from .utils import first_existing_css, safe_text

def debug_root_children(root):
    rows = []
    for i, child in enumerate(root.iter()):
        if child.parent != root:
            continue
        tag = child.tag
        cls = child.attributes.get("class", "")
        text = (child.text(strip=True) or "")[:120]
        rows.append((i, tag, cls, text))
    return rows

class WikipediaHTMLExtractor:
    def __init__(self, lang: str | None = None):
        self.lang = lang


    def parse_page(self, html: str, title: str | None = None) -> Page:
        tree = HTMLParser(html)
        root = first_existing_css(tree, CONTENT_ROOT_SELECTORS)
        
        if root is None:
            # fallback: 整页解析
            root = tree.body or tree.root

        self._drop_noise(root)

        page = Page(
            title=title or self._extract_title(tree),
            lang=self.lang,
        )

        # 先尝试抽 infobox
        infobox = self._extract_infobox(root)
        if infobox:
            page.infobox = infobox

        self._extract_sections_and_lead(root, page)
        return page

    def _extract_title(self, tree: HTMLParser) -> str | None:
        title_node = tree.css_first("title")
        if title_node:
            raw = safe_text(title_node)
            # 常见 title 格式: "YouTube - Wikipedia"
            raw = raw.replace(" - Wikipedia", "").strip()
            return raw or None

        h1 = tree.css_first("h1")
        if h1:
            return normalize_text(safe_text(h1))
        return None

    def _drop_noise(self, root: Node) -> None:
        for selector in DROP_SELECTORS:
            for node in root.css(selector):
                node.decompose()

    def _extract_infobox(self, root: Node) -> dict[str, str]:
        table = root.css_first("table.infobox")
        if table is None:
            return {}

        data: dict[str, str] = {}

        for tr in table.css("tr"):
            th = tr.css_first("th")
            td = tr.css_first("td")
            if th is None or td is None:
                continue

            key = normalize_text(safe_text(th))
            val = normalize_text(safe_text(td))

            if not key or not val:
                continue

            if len(key) > 80:
                continue

            data[key] = val

        return data

    def _extract_sections_and_lead(self, root: Node, page: Page) -> None:
        current_section: Section | None = None
        section_index = 0

        for child in root.iter():
            # 只处理直接子节点，避免深层重复
            if child.parent != root:
                continue

            if self._should_skip_block(child):
                continue

            tag = (child.tag or "").lower()

            cls = child.attributes.get("class") or ""
            is_heading = tag in HEADING_TAGS or "mw-heading" in cls.split()

            if is_heading:
                title = self._extract_heading_text(child)
                if not title:
                    continue

                level = None
                if tag in HEADING_TAGS:
                    level = int(tag[1])
                else:
                    for c in cls.split():
                        if c.startswith("mw-heading") and c[len("mw-heading"):].isdigit():
                            level = int(c[len("mw-heading"):])
                            break
                if level is None:
                    level = 2

                current_section = Section(
                    index=section_index,
                    level=level,
                    title=title,
                    blocks=[],
                )
                page.sections.append(current_section)
                section_index += 1
                continue

            block = self._extract_block(child)
            if block is None:
                continue

            if current_section is None:
                page.lead_blocks.append(block)
            else:
                current_section.blocks.append(block)

    def _should_skip_block(self, node: Node) -> bool:
        for selector in SKIP_BLOCK_SELECTORS:
            # selectolax 没有 matches(selector)，这里用一个简单办法：
            # 看该节点是否能被父级查询到并且自己属于结果之一
            parent = node.parent
            if parent is None:
                continue
            matches = parent.css(selector)
            if any(m == node for m in matches):
                return True
        return False

    def _extract_heading_text(self, node: Node) -> str:
        # Wikipedia 标题里常有 span.mw-headline
        headline = node.css_first(".mw-headline")
        if headline:
            return normalize_text(safe_text(headline))
        return normalize_text(safe_text(node))

    def _extract_block(self, node: Node) -> Block | None:
        tag = (node.tag or "").lower()

        if tag in PARAGRAPH_TAGS:
            text = normalize_text(safe_text(node))
            if not text:
                return None
            return Block(type="paragraph", text=text)

        if tag in LIST_TAGS:
            items = []
            for li in node.css("li"):
                txt = normalize_text(safe_text(li))
                if txt:
                    items.append(txt)
            if not items:
                return None
            return Block(type="list", items=items)

        if tag == "table":
            classes = node.attributes.get("class", "")
            if "infobox" in classes:
                # infobox 已单独提取，这里不作为正文块重复返回
                return None

            if "wikitable" in classes:
                table_block = self._extract_wikitable(node)
                return table_block

            return None

        if tag == "div":
            # 对一些嵌套 div，尝试提取里面最重要的 p/ul/ol
            nested_paragraphs = []
            for p in node.css("p"):
                txt = normalize_text(safe_text(p))
                if txt:
                    nested_paragraphs.append(txt)

            if nested_paragraphs:
                text = "\n\n".join(nested_paragraphs[:3])
                return Block(type="paragraph", text=text)

        return None

    def _extract_wikitable(self, node: Node) -> Block | None:
        caption_node = node.css_first("caption")
        caption = normalize_text(safe_text(caption_node)) if caption_node else None

        headers = []
        header_row = node.css_first("tr")
        if header_row:
            ths = header_row.css("th")
            headers = [normalize_text(safe_text(th)) for th in ths if normalize_text(safe_text(th))]

        rows = []
        for tr in node.css("tr")[1:6]:  # 只取前几行，防止过大
            cells = tr.css("th, td")
            row = [normalize_text(safe_text(c)) for c in cells]
            row = [c for c in row if c]
            if row:
                rows.append(row)

        if not headers and not rows and not caption:
            return None

        return Block(
            type="table",
            caption=caption,
            headers=headers or None,
            rows=rows or None,
        )

    def find_section(self, page: Page, section: str | None = None, section_index: int | None = None) -> Section | None:
        if section_index is not None:
            for sec in page.sections:
                if sec.index == section_index:
                    return sec
            return None

        if section:
            normalized = normalize_section_title(section)
            for sec in page.sections:
                if normalize_section_title(sec.title) == normalized:
                    return sec

            # 简单包含匹配
            for sec in page.sections:
                sec_norm = normalize_section_title(sec.title)
                if normalized in sec_norm or sec_norm in normalized:
                    return sec

        return None

    def collect_section_blocks(self, page: Page, target: Section) -> list[Block]:
        blocks = list(target.blocks)

        started = False
        for sec in page.sections:
            if sec.index == target.index:
                started = True
                continue

            if not started:
                continue

            if sec.level <= target.level:
                break

            blocks.extend(sec.blocks)

        return blocks

