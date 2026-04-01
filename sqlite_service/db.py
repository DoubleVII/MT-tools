import json
import sqlite3
import threading

from .config import (
    CONFIG,
    LANG_ID_MAP,
    LANG_FROM_ID_MAP,
    SOURCE_TYPE_ID_MAP,
    SOURCE_TYPE_FROM_ID_MAP,
)


_thread_local = threading.local()
_mappings_loaded = False


def _load_mappings(conn: sqlite3.Connection):
    global _mappings_loaded
    if _mappings_loaded:
        return

    cur = conn.execute(
        "SELECT key, value FROM metadata WHERE key IN ('lang_mapping', 'source_type_mapping')"
    )
    for row in cur.fetchall():
        data = json.loads(row["value"])
        if row["key"] == "lang_mapping":
            LANG_FROM_ID_MAP.update({int(k): v for k, v in data.items()})
            LANG_ID_MAP.update({v: int(k) for k, v in data.items()})
        elif row["key"] == "source_type_mapping":
            SOURCE_TYPE_FROM_ID_MAP.update({int(k): v for k, v in data.items()})
            SOURCE_TYPE_ID_MAP.update({v: int(k) for k, v in data.items()})

    _mappings_loaded = True


def get_lang_id(lang: str) -> int:
    return LANG_ID_MAP.get(lang, -1)


def get_lang_from_id(lang_id: int) -> str:
    return LANG_FROM_ID_MAP.get(lang_id, "unknown")


def get_source_type_id(source_type: str) -> int:
    return SOURCE_TYPE_ID_MAP.get(source_type, -1)


def get_source_type_from_id(source_type_id: int) -> str:
    return SOURCE_TYPE_FROM_ID_MAP.get(source_type_id, "unknown")


def get_connection() -> sqlite3.Connection:
    conn = getattr(_thread_local, "conn", None)
    if conn is None:
        # 只读连接
        uri = f"file:{CONFIG.db_path}?mode=ro"
        conn = sqlite3.connect(
            uri,
            uri=True,
            timeout=CONFIG.sqlite_timeout_sec,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row

        # 只读查询常用 PRAGMA
        conn.execute("PRAGMA query_only = ON")
        conn.execute("PRAGMA foreign_keys = OFF")
        _thread_local.conn = conn

        _load_mappings(conn)

    return conn
