from flask import Flask, jsonify, request

from kiwix_reader import preload_archives, read_page_by_lang_title
from sqlite_service import (
    search,
    get_entity_by_qid,
    get_qid_by_lang_title,
    get_connection,
    close_connection,
    InvalidQueryError,
    SearchConfig,
)
from .caches import search_cache, zim_cache, entity_cache, qid_cache
from .cache_service import cached
from .config import valid_langs
from .errors import (
    APIError,
    raise_bad_request,
    raise_not_found,
    register_error_handlers,
)

app = Flask(__name__)
register_error_handlers(app)

preload_archives()


@app.teardown_appcontext
def teardown_db(exception):
    close_connection(exception)


@cached(
    cache=search_cache,
    ttl=600,
    key_func=lambda lang, query, limit: (lang, query, limit),
)
def cached_search(lang, query, limit):
    conn = get_connection()
    try:
        return search(conn, lang, query, limit)
    finally:
        close_connection(conn)


@cached(
    cache=zim_cache,
    ttl=600,
    key_func=lambda lang, title: (lang, title),
    cache_none=True,  # TODO: change exception to None
)
def cached_read_page(lang, title):
    return read_page_by_lang_title(lang, title)


@cached(
    cache=entity_cache,
    ttl=600,
    key_func=lambda qid: qid,
    cache_none=True,  # TODO: change exception to None
)
def cached_get_entity_by_qid(qid):
    conn = get_connection()
    try:
        return get_entity_by_qid(conn, qid)
    finally:
        close_connection(conn)


@cached(
    cache=qid_cache,
    ttl=600,
    key_func=lambda lang, title: (lang, title),
    cache_none=True,  # TODO: change exception to None
)
def cached_get_qid_by_lang_title(lang, title):
    conn = get_connection()
    try:
        return get_qid_by_lang_title(conn, lang, title)
    finally:
        close_connection(conn)


def validate_lang(lang, required=True):
    if required and not lang:
        raise_bad_request(
            "MISSING_LANG",
            "Query parameter 'lang' is required.",
            {"parameter": "lang"},
        )

    if not lang:
        return

    if len(lang) != 2:
        raise_bad_request(
            "INVALID_LANG_FORMAT",
            "Query parameter 'lang' must be a 2-letter language code.",
            {"parameter": "lang", "value": lang},
        )

    if lang not in valid_langs:
        raise_bad_request(
            "UNSUPPORTED_LANG",
            f"Language '{lang}' is not supported.",
            {"parameter": "lang", "value": lang},
        )


def require_param(value, name):
    if not value:
        raise_bad_request(
            f"MISSING_{name.upper()}",
            f"Query parameter '{name}' is required.",
            {"parameter": name},
        )


@app.route("/healthz", methods=["GET"])
def healthz():
    return {"ok": True}


@app.route("/search", methods=["GET"])
def search_endpoint():
    lang = (request.args.get("lang") or "").strip()
    query = (request.args.get("query") or "").strip()

    raw_limit = (request.args.get("limit") or "").strip()
    limit = None
    if raw_limit:
        try:
            limit = int(raw_limit)
        except ValueError:
            raise_bad_request(
                "INVALID_LIMIT",
                "Query parameter 'limit' must be an integer.",
                {"parameter": "limit", "value": raw_limit},
            )
        if limit <= 0:
            raise_bad_request(
                "INVALID_LIMIT",
                "Query parameter 'limit' must be greater than 0.",
                {"parameter": "limit", "value": limit},
            )
        if limit > SearchConfig.max_limit:
            raise_bad_request(
                "INVALID_LIMIT",
                f"Query parameter 'limit' must be less than or equal to {SearchConfig.max_limit}.",
                {"parameter": "limit", "value": limit},
            )

    validate_lang(lang)
    require_param(query, "query")

    try:
        search_response = cached_search(lang, query, limit)
        return jsonify(search_response)
    except InvalidQueryError as e:
        # 这是业务层明确的客户端错误，可以返回给用户
        raise_bad_request(
            "INVALID_QUERY",
            str(e),
            {"parameter": "query", "value": query},
        )


@app.route("/read", methods=["GET"])
def read_page_endpoint():
    lang = (request.args.get("lang") or "").strip()
    qid = (request.args.get("qid") or "").strip()
    title = (request.args.get("title") or "").strip()

    validate_lang(lang)

    if not qid and not title:
        raise_bad_request(
            "MISSING_QID_OR_TITLE",
            "Either query parameter 'qid' or 'title' is required.",
            {"parameters": ["qid", "title"]},
        )

    if qid and title:
        raise_bad_request(
            "AMBIGUOUS_IDENTIFIER",
            "Provide only one of 'qid' or 'title', not both.",
            {"parameters": ["qid", "title"]},
        )

    if qid:
        entity = cached_get_entity_by_qid(qid)
        if not entity:
            raise_not_found(
                "ENTITY_NOT_FOUND",
                f"No entity found for qid '{qid}'.",
                {"qid": qid},
            )

        if lang not in entity.sitelinks:
            raise_not_found(
                "SITELINK_NOT_FOUND",
                f"Entity '{qid}' does not have a page for language '{lang}'.",
                {"qid": qid, "lang": lang},
            )

        title = entity.sitelinks.get(lang)
        page = cached_read_page(lang, title)
        if page is None:
            raise_not_found(
                "PAGE_NOT_FOUND",
                f"Page not found for language '{lang}' and qid '{qid}'.",
                {"qid": qid, "lang": lang, "title": title},
            )

        return jsonify(page)

    page = cached_read_page(lang, title)
    if page is None:
        raise_not_found(
            "PAGE_NOT_FOUND",
            f"Page '{title}' not found for language '{lang}'.",
            {"lang": lang, "title": title},
        )

    return jsonify(page)


@app.route("/entity", methods=["GET"])
def get_entity_endpoint():
    qid = (request.args.get("qid") or "").strip()
    lang = (request.args.get("lang") or "").strip()
    title = (request.args.get("title") or "").strip()

    # 明确规则：qid 或 (lang + title) 二选一
    if qid and (lang or title):
        raise_bad_request(
            "AMBIGUOUS_IDENTIFIER",
            "Provide either 'qid' or both 'lang' and 'title', not both forms.",
            {"parameters": ["qid", "lang", "title"]},
        )

    if qid:
        entity = cached_get_entity_by_qid(qid)
        if not entity:
            raise_not_found(
                "ENTITY_NOT_FOUND",
                f"No entity found for qid '{qid}'.",
                {"qid": qid},
            )
        return jsonify(entity)

    if lang or title:
        validate_lang(lang)
        require_param(title, "title")

        qid = cached_get_qid_by_lang_title(lang, title)
        if not qid:
            raise_not_found(
                "QID_NOT_FOUND",
                f"No qid found for title '{title}' in language '{lang}'.",
                {"lang": lang, "title": title},
            )

        entity = cached_get_entity_by_qid(qid)
        if not entity:
            raise_not_found(
                "ENTITY_NOT_FOUND",
                f"No entity found for qid '{qid}'.",
                {"qid": qid, "lang": lang, "title": title},
            )

        return jsonify(entity)

    raise_bad_request(
        "MISSING_QID_OR_LANG_TITLE",
        "Provide either 'qid' or both 'lang' and 'title'.",
        {"parameters": ["qid", "lang", "title"]},
    )


@app.route("/qid", methods=["GET"])
def get_qid_endpoint():
    lang = (request.args.get("lang") or "").strip()
    title = (request.args.get("title") or "").strip()

    validate_lang(lang)
    require_param(title, "title")

    qid = cached_get_qid_by_lang_title(lang, title)
    if not qid:
        raise_not_found(
            "QID_NOT_FOUND",
            f"No qid found for title '{title}' in language '{lang}'.",
            {"lang": lang, "title": title},
        )

    return jsonify(qid)

@app.route("/langs", methods=["GET"])
def get_langs_endpoint():
    return jsonify({"langs": valid_langs})

@app.route("/cache/stats", methods=["GET"])
def cache_stats():
    return jsonify({
        "search_cache": search_cache.stats(),
        "zim_cache": zim_cache.stats(),
        "entity_cache": entity_cache.stats(),
        "qid_cache": qid_cache.stats(),
    })


if __name__ == "__main__":
    # 本地开发用，生产请用 gunicorn
    app.run(host="0.0.0.0", port=23334, debug=True, threaded=True)
