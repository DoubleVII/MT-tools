from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class SearchResultItem:
    qid: str
    title: str
    lang: str
    score: float
    best_match_name: str
    best_match_source_type: str
    matched_names: list[str]
    matched_source_types: list[str]
    description: str | None = None
    label: str | None = None
    has_wiki_page: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResponse:
    total_matches: int
    results: list[dict[str, Any]]


@dataclass
class Entity:
    qid: str
    wikipedia_lang_count: int
    sitelink_count_total: int
    labels: dict[str, str]
    descriptions: dict[str, str]
    sitelinks: dict[str, str]
    has_wiki_page: dict[str, bool]