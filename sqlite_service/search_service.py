import math
import json

from .config import CONFIG, SOURCE_BOOST, SOURCE_WEIGHT
from .db import get_connection, get_lang_id, get_source_type_from_id
from .errors import InvalidQueryError
from .models import SearchResponse, SearchResultItem
from .normalizer import normalize_name, normalize_name_loose, build_fts_query
from .sql import get_sql_exact, get_sql_prefix, get_sql_fts, SQL_ENTITY_INFO_BY_QIDS_TEMPLATE


STAGE_BONUS = {
    "exact": 1000.0,
    "prefix": 300.0,
    "fts": 100.0,
}


def escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def compute_candidate_text_score(stage: str, source_type: str, is_primary: int, fts_rank=None) -> float:
    source_weight = SOURCE_WEIGHT.get(source_type, 0.0)
    score = STAGE_BONUS.get(stage, 0.0)
    score += source_weight * 100.0
    score += 20.0 if is_primary else 0.0

    if stage == "fts" and fts_rank is not None:
        # bm25 越小越好，这里做一个简单反转
        score += max(0.0, 30.0 - float(fts_rank))

    return score

def compute_importance_boost(entity: dict | None) -> float:
    if not entity:
        return 0.0

    wikipedia_lang_count = entity.get("wikipedia_lang_count", 0) or 0
    sitelink_count_total = entity.get("sitelink_count_total", 0) or 0

    boost = (
        0.06 * math.log1p(wikipedia_lang_count) +
        0.03 * math.log1p(sitelink_count_total)
    )
    return min(boost, 0.45)

def compute_final_score(text_score: float, best_source_type: str, entity: dict | None) -> float:
    source_boost = SOURCE_BOOST.get(best_source_type, 0.0)
    importance_boost = compute_importance_boost(entity)
    return text_score * (1.0 + source_boost + importance_boost)

def run_exact_query(conn, lang_id: int, norm: str, loose: str, limit: int):
    sql = get_sql_exact()
    cur = conn.execute(sql, (lang_id, norm, loose, limit))
    rows = []
    for row in cur.fetchall():
        rows.append({
            "qid": row["qid"],
            "name": row["name"],
            "source_type": get_source_type_from_id(row["source_type_id"]),
            "is_primary": row["is_primary"],
            "stage": "exact",
            "fts_rank": None,
        })
    return rows


def run_prefix_query(conn, lang_id: int, norm: str, loose: str, limit: int):
    sql = get_sql_prefix()
    norm_like = escape_like(norm) + "%"
    loose_like = escape_like(loose) + "%"
    cur = conn.execute(sql, (lang_id, norm_like, loose_like, limit))
    rows = []
    for row in cur.fetchall():
        rows.append({
            "qid": row["qid"],
            "name": row["name"],
            "source_type": get_source_type_from_id(row["source_type_id"]),
            "is_primary": row["is_primary"],
            "stage": "prefix",
            "fts_rank": None,
        })
    return rows


def run_fts_query(conn, lang_id: int, fts_query: str, limit: int):
    sql = get_sql_fts()
    cur = conn.execute(sql, (lang_id, fts_query, limit))
    rows = []
    for row in cur.fetchall():
        rows.append({
            "qid": row["qid"],
            "name": row["name"],
            "source_type": get_source_type_from_id(row["source_type_id"]),
            "is_primary": row["is_primary"],
            "stage": "fts",
            "fts_rank": row["fts_rank"],
        })
    return rows


def fetch_entity_info(conn, qids: list[str]) -> dict[str, dict]:
    if not qids:
        return {}

    placeholders = ",".join("?" for _ in qids)
    sql = SQL_ENTITY_INFO_BY_QIDS_TEMPLATE.format(placeholders=placeholders)
    cur = conn.execute(sql, qids)

    out = {}
    for row in cur.fetchall():
        out[row["qid"]] = {
            "wikipedia_lang_count": row["wikipedia_lang_count"] or 0,
            "sitelink_count_total": row["sitelink_count_total"] or 0,
            "labels_json": row["labels_json"] or "",
            "descriptions_json": row["descriptions_json"] or "",
            "sitelinks_json": row["sitelinks_json"] or "",
        }
    return out

def get_entity_description(entity: dict | None, lang: str) -> str | None:
    if not entity:
        return None

    try:
        descriptions = json.loads(entity["descriptions_json"])
    except json.JSONDecodeError:
        return None

    return descriptions.get(lang, None)

def merge_candidates(lang: str, candidates: list[dict], entity_info_map: dict[str, dict], limit: int) -> SearchResponse:
    grouped = {}

    for c in candidates:
        qid = c["qid"]
        text_score = compute_candidate_text_score(
            stage=c["stage"],
            source_type=c["source_type"],
            is_primary=c["is_primary"],
            fts_rank=c["fts_rank"],
        )

        entry = grouped.get(qid)
        if entry is None:
            entry = {
                "qid": qid,
                "text_score": 0.0,
                "best_match_name": c["name"],
                "best_match_source_type": c["source_type"],
                "best_match_text_score": text_score,
                "matched_names": [],
                "matched_source_types": [],
                "seen_names": set(),
                "seen_source_types": set(),
            }
            grouped[qid] = entry

        entry["text_score"] += text_score

        if text_score > entry["best_match_text_score"]:
            entry["best_match_text_score"] = text_score
            entry["best_match_name"] = c["name"]
            entry["best_match_source_type"] = c["source_type"]

        if c["name"] not in entry["seen_names"]:
            entry["seen_names"].add(c["name"])
            entry["matched_names"].append(c["name"])

        if c["source_type"] not in entry["seen_source_types"]:
            entry["seen_source_types"].add(c["source_type"])
            entry["matched_source_types"].append(c["source_type"])

    ranked = []
    for entry in grouped.values():
        entity = entity_info_map.get(entry["qid"])
        final_score = compute_final_score(
            text_score=entry["text_score"],
            best_source_type=entry["best_match_source_type"],
            entity=entity,
        )
        entry["final_score"] = final_score
        entry["entity_info"] = entity or {
            "wikipedia_lang_count": 0,
            "sitelink_count_total": 0,
        }
        ranked.append(entry)

    ranked.sort(
        key=lambda x: (
            -x["final_score"],
            -x["text_score"],
            x["best_match_source_type"] != "title",
            x["best_match_name"],
            x["qid"],
        )
    )

    results = []
    for entry in ranked[:limit]:
        entity = entity_info_map.get(entry["qid"])
        title = entry["best_match_name"]
        
        if entity and entity.get("sitelinks_json"):
            try:
                sitelinks = json.loads(entity["sitelinks_json"])
                if lang in sitelinks:
                    title = sitelinks[lang]
            except (json.JSONDecodeError, KeyError):
                pass
        
        item = SearchResultItem(
            qid=entry["qid"],
            title=title,
            lang=lang,
            score=round(entry["final_score"], 3),
            best_match_name=entry["best_match_name"],
            best_match_source_type=entry["best_match_source_type"],
            matched_names=entry["matched_names"][:10],
            matched_source_types=entry["matched_source_types"],
            description=get_entity_description(entry["entity_info"], lang),
        ).to_dict()

        item["text_score"] = round(entry["text_score"], 3)
        item["importance"] = entry["entity_info"]
        results.append(item)

    return SearchResponse(
        total_matches=len(grouped),
        results=results,
    )



def search(lang: str, query: str, limit: int | None = None) -> SearchResponse:
    if not lang:
        raise InvalidQueryError("Missing required parameter: lang")
    if not query or not query.strip():
        raise InvalidQueryError("Missing required parameter: query")

    limit = limit or CONFIG.default_limit
    limit = max(1, min(limit, CONFIG.max_limit))

    conn = get_connection()

    lang_id = get_lang_id(lang)
    if lang_id < 0:
        raise InvalidQueryError(f"Unsupported language: {lang}")

    norm = normalize_name(query)
    loose = normalize_name_loose(query)

    if not norm and not loose:
        raise InvalidQueryError("Query is empty after normalization")

    
    candidates = []

    # 1) exact
    exact_rows = run_exact_query(
        conn,
        lang_id,
        norm or "",
        loose or "",
        CONFIG.exact_overfetch,
    )
    candidates.extend(exact_rows)
    print(f"exact end")

    # 2) prefix
    prefix_seed = norm or loose or ""
    if len(prefix_seed) >= CONFIG.min_prefix_len:
        prefix_rows = run_prefix_query(
            conn,
            lang_id,
            norm or "",
            loose or "",
            CONFIG.prefix_overfetch,
        )
        candidates.extend(prefix_rows)
    print(f"prefix end")

    # 3) fts
    fts_query = build_fts_query(query)
    if fts_query:
        fts_rows = run_fts_query(
            conn,
            lang_id,
            fts_query,
            CONFIG.fts_overfetch,
        )
        candidates.extend(fts_rows)
    print(f"fts end")

    # 去掉完全没结果的情况
    if not candidates:
        return SearchResponse(total_matches=0, results=[])


    qids = list(dict.fromkeys(c["qid"] for c in candidates))
    entity_info_map = fetch_entity_info(conn, qids)

    return merge_candidates(lang, candidates, entity_info_map, limit)
