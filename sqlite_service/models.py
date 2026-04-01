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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResponse:
    total_matches: int
    results: list[dict[str, Any]]
