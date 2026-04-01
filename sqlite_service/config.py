from dataclasses import dataclass


@dataclass(frozen=True)
class SearchConfig:
    db_path: str = "/home/zfs01/yangs/data/wikidata/wikidata_search_db.v9.sqlite.bkp"
    default_limit: int = 20
    max_limit: int = 50

    exact_overfetch: int = 80
    prefix_overfetch: int = 80
    fts_overfetch: int = 120

    min_prefix_len: int = 2
    sqlite_timeout_sec: float = 5.0


CONFIG = SearchConfig()

SOURCE_WEIGHT = {
    "title": 1.00,
    "redirect": 0.90,
    "alias": 0.75,
    "label": 0.72,
}

SOURCE_BOOST = {
    "title": 0.30,
    "redirect": 0.18,
    "alias": 0.10,
    "label": 0.08,
}

LANG_ID_MAP: dict[str, int] = {}
LANG_FROM_ID_MAP: dict[int, str] = {}
SOURCE_TYPE_ID_MAP: dict[str, int] = {}
SOURCE_TYPE_FROM_ID_MAP: dict[int, str] = {}