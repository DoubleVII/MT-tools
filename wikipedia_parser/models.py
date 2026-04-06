from dataclasses import dataclass, field
from typing import Any, Literal


BlockType = Literal[
    "paragraph",
    "list",
    "table",
    "infobox",
    "quote",
    "heading",
    "unknown",
]


@dataclass
class Block:
    type: BlockType
    text: str | None = None
    items: list[str] | None = None
    caption: str | None = None
    headers: list[str] | None = None
    rows: list[list[str]] | None = None
    data: dict[str, Any] | None = None


@dataclass
class Section:
    index: int
    level: int
    title: str
    blocks: list[Block] = field(default_factory=list)


@dataclass
class Page:
    title: str | None
    lang: str | None
    lead_blocks: list[Block] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    infobox: dict[str, str] = field(default_factory=dict)
    categories: list[str] = field(default_factory=list)
    raw_meta: dict[str, Any] = field(default_factory=dict)
