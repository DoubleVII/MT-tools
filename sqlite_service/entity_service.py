import json
import sqlite3
from .models import Entity
from .sql import get_sql_entity_by_qid


def parse_entity_row(row: sqlite3.Row) -> dict:
    labels = {}
    descriptions = {}
    sitelinks = {}

    try:
        if row["labels_json"]:
            labels = json.loads(row["labels_json"])
    except json.JSONDecodeError:
        pass

    try:
        if row["descriptions_json"]:
            descriptions = json.loads(row["descriptions_json"])
    except json.JSONDecodeError:
        pass

    try:
        if row["sitelinks_json"]:
            sitelinks = json.loads(row["sitelinks_json"])
    except json.JSONDecodeError:
        pass

    return Entity(
        qid=row["qid"],
        wikipedia_lang_count=row["wikipedia_lang_count"] or 0,
        sitelink_count_total=row["sitelink_count_total"] or 0,
        labels=labels,
        descriptions=descriptions,
        sitelinks=sitelinks,
    )


def get_entity_by_qid(conn, qid: str) -> Entity | None:
    if not qid:
        return None

    sql = get_sql_entity_by_qid()
    cur = conn.execute(sql, (qid,))
    row = cur.fetchone()

    if not row:
        return None

    return parse_entity_row(row)
