from selectolax.parser import Node


def first_existing_css(node: Node, selectors: list[str]) -> Node | None:
    for sel in selectors:
        found = node.css_first(sel)
        if found is not None:
            return found
    return None


def safe_text(node: Node | None, separator: str = " ") -> str:
    if node is None:
        return ""
    return node.text(separator=separator, strip=True) or ""


def get_attr(node: Node | None, name: str, default: str | None = None) -> str | None:
    if node is None:
        return default
    return node.attributes.get(name, default)
