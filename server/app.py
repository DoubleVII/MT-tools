from flask import Flask, jsonify, request

from sqlite_service import search, get_connection, close_connection
from .caches import search_cache
from .cache_service import cached

app = Flask(__name__)


@app.teardown_appcontext
def teardown_db(exception):
    close_connection(exception)

@cached(
    cache=search_cache,
    ttl=600,
    key_func=lambda lang, query, limit: ("search", lang, query, limit),
)
def cached_search(lang, query, limit):
    conn = get_connection()
    try:
        return search(conn, lang, query, limit)
    finally:
        close_connection(conn)

@app.route("/healthz", methods=["GET"])
def healthz():
    return {"ok": True}

@app.route("/search", methods=["GET"])
def search_endpoint():
    lang = (request.args.get("lang") or "").strip()
    query = (request.args.get("query") or "").strip()
    limit = request.args.get("limit", None, type=int)

    if not lang:
        return jsonify({"error": "missing 'lang'"}), 400
    if not query:
        return jsonify({"error": "missing 'query'"}), 400

    try:
        search_response = cached_search(lang, query, limit)
    except Exception as e:
        return jsonify({"error": f"Unexpected server error: {e}"}), 500

    return jsonify(search_response)


@app.route("/cache/stats", methods=["GET"])
def cache_stats():
    return jsonify({
        "search_cache": search_cache.stats(),
    })

if __name__ == "__main__":
    # 本地开发用，生产请用 gunicorn
    app.run(host="0.0.0.0", port=23334, debug=True, threaded=True)
