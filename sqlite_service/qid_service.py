import json
import sqlite3

from .db import get_lang_id
from .normalizer import normalize_name
from .sql import get_sql_name_index_by_norm_name, get_sql_entity_by_qid


def fetch_name_index_by_norm_name(conn, lang_id: int, norm_name: str) -> list[dict]:
    sql = get_sql_name_index_by_norm_name()
    cur = conn.execute(sql, (lang_id, norm_name))

    rows = []
    for row in cur.fetchall():
        rows.append({
            "id": row["id"],
            "qid": row["qid"],
            "name": row["name"],
            "source_type_id": row["source_type_id"],
        })

    return rows


def select_best_match(rows: list[dict], original_title: str) -> dict | None:
    if not rows:
        return None

    if len(rows) == 1:
        return rows[0]

    for row in rows:
        if row["name"] == original_title:
            return row

    return rows[0]


def get_qid_by_lang_title(conn, lang: str, title: str) -> str | None:
    if not lang or not title:
        return None

    lang_id = get_lang_id(lang)
    if lang_id < 0:
        return None

    norm_name = normalize_name(title)
    if not norm_name:
        return None

    rows = fetch_name_index_by_norm_name(conn, lang_id, norm_name)
    if not rows:
        return None

    best_match = select_best_match(rows, title)
    if not best_match:
        return None

    return best_match["qid"]


def get_titles_by_qid_langs(conn, qid: str, langs: list[str]) -> dict[str, str]:
    if not qid or not langs:
        return {}

    sql = get_sql_entity_by_qid()
    cur = conn.execute(sql, (qid,))
    row = cur.fetchone()

    if not row:
        return {}

    sitelinks_json = row["sitelinks_json"]
    if not sitelinks_json:
        return {}

    try:
        sitelinks = json.loads(sitelinks_json)
    except json.JSONDecodeError:
        return {}

    result = {}
    for lang in langs:
        site_key = f"{lang}wiki"
        if site_key in sitelinks:
            site_info = sitelinks[site_key]
            if isinstance(site_info, dict) and "title" in site_info:
                result[lang] = site_info["title"]

    return result
