import math
import json
import time

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



def compute_candidate_text_score(stage: str, source_type: str, fts_rank=None) -> float:
    source_weight = SOURCE_WEIGHT.get(source_type, 0.0)
    score = STAGE_BONUS.get(stage, 0.0)
    score += source_weight * 100.0

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


def dedup_stage_rows(rows: list[dict]) -> list[dict]:
    """
    UNION ALL 会让同一条 name_index 记录在两个分支都命中时重复返回。
    这里做轻量去重，避免重复计分。
    """
    seen = set()
    out = []

    for row in rows:
        key = (
            row["qid"],
            row["name"],
            row["source_type"],
            row["stage"],
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(row)

    return out


def run_exact_query(conn, lang_id: int, norm: str, loose: str, limit: int):
    sql = get_sql_exact()
    cur = conn.execute(sql, (lang_id, norm, lang_id, loose, limit))
    rows = []
    for row in cur.fetchall():
        rows.append({
            "qid": row["qid"],
            "name": row["name"],
            "source_type": get_source_type_from_id(row["source_type_id"]),
            "stage": "exact",
            "fts_rank": None,
        })
    return dedup_stage_rows(rows)


def build_prefix_range(prefix: str) -> tuple[str, str]:
    if not prefix:
        raise ValueError("prefix must not be empty")

    chars = list(prefix)
    for i in range(len(chars) - 1, -1, -1):
        code = ord(chars[i])
        if code < 0x10FFFF:
            chars[i] = chr(code + 1)
            return prefix, "".join(chars[:i + 1])

    raise ValueError("failed to build prefix upper bound")

def run_prefix_query(conn, lang_id: int, norm: str, loose: str, limit: int):
    sql = get_sql_prefix()

    try:
        norm_lo, norm_hi = build_prefix_range(norm)
        loose_lo, loose_hi = build_prefix_range(loose)
    except ValueError as e:
        return []

    cur = conn.execute(
        sql,
        (
            lang_id, norm_lo, norm_hi,
            lang_id, loose_lo, loose_hi,
            limit,
        )
    )

    rows = []
    for row in cur.fetchall():
        rows.append({
            "qid": row["qid"],
            "name": row["name"],
            "source_type": get_source_type_from_id(row["source_type_id"]),
            "stage": "prefix",
            "fts_rank": None,
        })
    return dedup_stage_rows(rows)



def build_lang_fts_query(lang_id: int, fts_query: str) -> str:
    """
    把 lang_id 合并进 FTS MATCH 表达式。
    FTS5 中 lang_id 是独立列，因此可直接作为列过滤。
    """
    return f'lang_id:{lang_id} AND ({fts_query})'


def run_fts_query(conn, lang_id: int, fts_query: str, limit: int):
    sql = get_sql_fts()
    match_query = build_lang_fts_query(lang_id, fts_query)
    cur = conn.execute(sql, (match_query, limit))
    rows = []
    for row in cur.fetchall():
        rows.append({
            "qid": row["qid"],
            "name": row["name"],
            "source_type": get_source_type_from_id(row["source_type_id"]),
            "stage": "fts",
            "fts_rank": row["fts_rank"],
        })
    return dedup_stage_rows(rows)


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


def get_entity_title(entity: dict | None, lang: str) -> str | None:
    if not entity:
        return None
    try:
        titles = json.loads(entity["sitelinks_json"])
    except json.JSONDecodeError:
        return None
    return titles.get(lang, None)

def merge_candidates(lang: str, candidates: list[dict], entity_info_map: dict[str, dict], limit: int) -> SearchResponse:
    grouped = {}

    for c in candidates:
        qid = c["qid"]
        text_score = compute_candidate_text_score(
            stage=c["stage"],
            source_type=c["source_type"],
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
        
        entity_title = get_entity_title(entity, lang)
        assert title == entity_title, f"Title mismatch: {title} != {entity_title}"
        
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
    t0 = time.perf_counter()
    exact_rows = run_exact_query(
        conn,
        lang_id,
        norm or "",
        loose or "",
        CONFIG.exact_overfetch,
    )
    t1 = time.perf_counter()
    print(f"exact end, cost: {(t1 - t0) * 1000:.2f}ms, rows: {len(exact_rows)}")
    candidates.extend(exact_rows)

    # 2) prefix
    prefix_seed = norm or loose or ""
    if len(prefix_seed) >= CONFIG.min_prefix_len:
        t0 = time.perf_counter()
        prefix_rows = run_prefix_query(
            conn,
            lang_id,
            norm or "",
            loose or "",
            CONFIG.prefix_overfetch,
        )
        t1 = time.perf_counter()
        print(f"prefix end, cost: {(t1 - t0) * 1000:.2f}ms, rows: {len(prefix_rows)}")
        candidates.extend(prefix_rows)
    else:
        print("prefix skipped (query too short)")

    # 3) fts
    fts_query = build_fts_query(query)
    if fts_query:
        t0 = time.perf_counter()
        fts_rows = run_fts_query(
            conn,
            lang_id,
            fts_query,
            CONFIG.fts_overfetch,
        )
        t1 = time.perf_counter()
        print(f"fts end, cost: {(t1 - t0) * 1000:.2f}ms, rows: {len(fts_rows)}")
        candidates.extend(fts_rows)
    else:
        print("fts skipped (empty query)")

    # 去掉完全没结果的情况
    if not candidates:
        return SearchResponse(total_matches=0, results=[])


    qids = list(dict.fromkeys(c["qid"] for c in candidates))
    entity_info_map = fetch_entity_info(conn, qids)

    return merge_candidates(lang, candidates, entity_info_map, limit)
