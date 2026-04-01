# sql.py

def get_sql_exact_ids() -> str:
    return """
SELECT
    id,
    source_type_id
FROM (
    SELECT
        ni.id,
        ni.source_type_id
    FROM name_index ni
    WHERE ni.lang_id = ?
      AND ni.norm_name = ?

    UNION ALL

    SELECT
        ni.id,
        ni.source_type_id
    FROM name_index ni
    WHERE ni.lang_id = ?
      AND ni.norm_name_loose = ?
)
ORDER BY source_type_id ASC
LIMIT ?
"""


def get_sql_prefix_ids() -> str:
    return """
SELECT
    id,
    source_type_id
FROM (
    SELECT
        ni.id,
        ni.source_type_id
    FROM name_index ni
    WHERE ni.lang_id = ?
      AND ni.norm_name >= ?
      AND ni.norm_name < ?

    UNION ALL

    SELECT
        ni.id,
        ni.source_type_id
    FROM name_index ni
    WHERE ni.lang_id = ?
      AND ni.norm_name_loose >= ?
      AND ni.norm_name_loose < ?
)
ORDER BY source_type_id ASC
LIMIT ?
"""


def get_sql_fts_ids() -> str:
    return """
SELECT
    rowid AS id,
    bm25(name_fts) AS fts_rank
FROM name_fts
WHERE name_fts MATCH ?
ORDER BY fts_rank
LIMIT ?
"""


SQL_NAME_INDEX_BY_IDS_TEMPLATE = """
SELECT
    ni.id,
    ni.qid,
    ni.name,
    ni.source_type_id
FROM name_index ni
WHERE ni.id IN ({placeholders})
"""

SQL_ENTITY_INFO_BY_QIDS_TEMPLATE = """
SELECT
    e.qid,
    e.wikipedia_lang_count,
    e.sitelink_count_total,
    e.labels_json,
    e.descriptions_json,
    e.sitelinks_json
FROM entity_info e
WHERE e.qid IN ({placeholders})
"""
