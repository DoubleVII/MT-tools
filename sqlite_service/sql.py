from .config import SOURCE_WEIGHT, SOURCE_TYPE_ID_MAP


def _build_source_type_case() -> str:
    lines = []
    for source_type, weight in SOURCE_WEIGHT.items():
        source_type_id = SOURCE_TYPE_ID_MAP.get(source_type, -1)
        lines.append(f"        WHEN {source_type_id} THEN {weight:.2f}")
    lines.append("        ELSE 0.0")
    return "\n".join(lines)


def get_sql_exact() -> str:
    source_type_case = _build_source_type_case()
    return f"""
SELECT
    ni.qid,
    ni.name,
    ni.source_type_id,
    ni.is_primary
FROM name_index ni
WHERE ni.lang_id = ?
  AND (
        ni.norm_name = ?
        OR ni.norm_name_loose = ?
      )
ORDER BY
    CASE ni.source_type_id
{source_type_case}
    END DESC
LIMIT ?
"""


def get_sql_prefix() -> str:
    source_type_case = _build_source_type_case()
    return f"""
SELECT
    ni.qid,
    ni.name,
    ni.source_type_id,
    ni.is_primary
FROM name_index ni
WHERE ni.lang_id = ?
  AND (
        ni.norm_name LIKE ? ESCAPE '\\'
        OR ni.norm_name_loose LIKE ? ESCAPE '\\'
      )
ORDER BY
    CASE ni.source_type_id
{source_type_case}
    END DESC
LIMIT ?
"""


def get_sql_fts() -> str:
    return """
SELECT
    ni.qid,
    ni.name,
    ni.source_type_id,
    ni.is_primary,
    bm25(name_fts) AS fts_rank
FROM name_fts nf
JOIN name_index ni ON nf.rowid = ni.id
WHERE nf.lang_id = ?
  AND name_fts MATCH ?
ORDER BY fts_rank
LIMIT ?
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
