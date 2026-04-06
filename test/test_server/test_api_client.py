import pytest

from server.app import app
from test.test_server.config import SAMPLE_LANG, SAMPLE_TITLE, SAMPLE_QID, INVALID_LANG, INVALID_LANG_FORMAT, INVALID_QID, INVALID_TITLE


# =========================
# Fixtures
# =========================

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# =========================
# Helpers
# =========================

def assert_error_response(resp, expected_status, expected_code=None):
    assert resp.status_code == expected_status, resp.get_data(as_text=True)

    payload = resp.get_json()
    assert isinstance(payload, dict), payload
    assert "error" in payload, payload
    assert isinstance(payload["error"], dict), payload

    error = payload["error"]
    assert "message" in error, payload
    assert isinstance(error["message"], str)
    assert error["message"].strip()

    if expected_code is not None:
        assert error.get("code") == expected_code, payload

    return payload


def assert_search_success(payload):
    assert isinstance(payload, dict), payload
    assert "total_matches" in payload, payload
    assert "results" in payload, payload
    assert isinstance(payload["results"], list), payload

    for item in payload["results"]:
        assert isinstance(item, dict), item
        assert "qid" in item
        assert "lang" in item
        assert "best_match_name" in item
        assert "matched_names" in item
        assert "matched_source_types" in item
        assert "has_wiki_page" in item


def assert_entity_success(payload):
    assert isinstance(payload, dict), payload
    assert "qid" in payload
    assert "wikipedia_lang_count" in payload
    assert "sitelink_count_total" in payload
    assert "labels" in payload
    assert "descriptions" in payload
    assert "sitelinks" in payload

    assert isinstance(payload["labels"], dict)
    assert isinstance(payload["descriptions"], dict)
    assert isinstance(payload["sitelinks"], dict)


def assert_qid_success(payload):
    assert isinstance(payload, str), payload
    assert payload.startswith("Q"), payload


def assert_read_success(payload):
    assert isinstance(payload, str), payload
    assert payload.strip()
    assert len(payload) > 20


# =========================
# Healthz
# =========================

def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


# =========================
# /search
# =========================

def test_search_success(client):
    resp = client.get("/search", query_string={
        "lang": SAMPLE_LANG,
        "query": SAMPLE_TITLE,
    })
    assert resp.status_code == 200, resp.get_data(as_text=True)
    payload = resp.get_json()
    assert_search_success(payload)


def test_search_success_with_limit(client):
    resp = client.get("/search", query_string={
        "lang": SAMPLE_LANG,
        "query": SAMPLE_TITLE,
        "limit": 3,
    })
    assert resp.status_code == 200, resp.get_data(as_text=True)
    payload = resp.get_json()
    assert_search_success(payload)


def test_search_missing_lang(client):
    resp = client.get("/search", query_string={
        "query": SAMPLE_TITLE,
    })
    assert_error_response(resp, 400, "MISSING_LANG")


def test_search_missing_query(client):
    resp = client.get("/search", query_string={
        "lang": SAMPLE_LANG,
    })
    assert_error_response(resp, 400, "MISSING_QUERY")


def test_search_invalid_lang_format(client):
    resp = client.get("/search", query_string={
        "lang": INVALID_LANG_FORMAT,
        "query": SAMPLE_TITLE,
    })
    assert_error_response(resp, 400, "INVALID_LANG_FORMAT")


def test_search_unsupported_lang(client):
    resp = client.get("/search", query_string={
        "lang": INVALID_LANG,
        "query": SAMPLE_TITLE,
    })
    assert_error_response(resp, 400, "UNSUPPORTED_LANG")


@pytest.mark.parametrize("limit", ["abc", "1.5", "0", "-1"])
def test_search_invalid_limit(client, limit):
    resp = client.get("/search", query_string={
        "lang": SAMPLE_LANG,
        "query": SAMPLE_TITLE,
        "limit": limit,
    })
    assert_error_response(resp, 400, "INVALID_LIMIT")


# =========================
# /read
# =========================

def test_read_by_qid_success(client):
    resp = client.get("/read", query_string={
        "lang": SAMPLE_LANG,
        "qid": SAMPLE_QID,
    })
    assert resp.status_code == 200, resp.get_data(as_text=True)
    payload = resp.get_json()
    assert_read_success(payload)


def test_read_by_title_success(client):
    resp = client.get("/read", query_string={
        "lang": SAMPLE_LANG,
        "title": SAMPLE_TITLE,
    })
    assert resp.status_code == 200, resp.get_data(as_text=True)
    payload = resp.get_json()
    assert_read_success(payload)


def test_read_missing_lang(client):
    resp = client.get("/read", query_string={
        "qid": SAMPLE_QID,
    })
    assert_error_response(resp, 400, "MISSING_LANG")


def test_read_missing_qid_or_title(client):
    resp = client.get("/read", query_string={
        "lang": SAMPLE_LANG,
    })
    assert_error_response(resp, 400, "MISSING_QID_OR_TITLE")


def test_read_ambiguous_identifier(client):
    resp = client.get("/read", query_string={
        "lang": SAMPLE_LANG,
        "qid": SAMPLE_QID,
        "title": SAMPLE_TITLE,
    })
    assert_error_response(resp, 400, "AMBIGUOUS_IDENTIFIER")


def test_read_invalid_lang_format(client):
    resp = client.get("/read", query_string={
        "lang": INVALID_LANG_FORMAT,
        "qid": SAMPLE_QID,
    })
    assert_error_response(resp, 400, "INVALID_LANG_FORMAT")


def test_read_unsupported_lang(client):
    resp = client.get("/read", query_string={
        "lang": INVALID_LANG,
        "qid": SAMPLE_QID,
    })
    assert_error_response(resp, 400, "UNSUPPORTED_LANG")


def test_read_invalid_qid_not_found(client):
    resp = client.get("/read", query_string={
        "lang": SAMPLE_LANG,
        "qid": INVALID_QID,
    })
    assert_error_response(resp, 404, "ENTITY_NOT_FOUND")


def test_read_invalid_title_not_found(client):
    resp = client.get("/read", query_string={
        "lang": SAMPLE_LANG,
        "title": INVALID_TITLE,
    })
    assert_error_response(resp, 404, "PAGE_NOT_FOUND")


# =========================
# /entity
# =========================

def test_entity_by_qid_success(client):
    resp = client.get("/entity", query_string={
        "qid": SAMPLE_QID,
    })
    assert resp.status_code == 200, resp.get_data(as_text=True)
    payload = resp.get_json()
    assert_entity_success(payload)
    assert payload["qid"] == SAMPLE_QID


def test_entity_by_title_success(client):
    resp = client.get("/entity", query_string={
        "lang": SAMPLE_LANG,
        "title": SAMPLE_TITLE,
    })
    assert resp.status_code == 200, resp.get_data(as_text=True)
    payload = resp.get_json()
    assert_entity_success(payload)


def test_entity_missing_all_params(client):
    resp = client.get("/entity")
    assert_error_response(resp, 400, "MISSING_QID_OR_LANG_TITLE")


def test_entity_ambiguous_identifier(client):
    resp = client.get("/entity", query_string={
        "qid": SAMPLE_QID,
        "lang": SAMPLE_LANG,
        "title": SAMPLE_TITLE,
    })
    assert_error_response(resp, 400, "AMBIGUOUS_IDENTIFIER")


def test_entity_missing_title_when_lang_provided(client):
    resp = client.get("/entity", query_string={
        "lang": SAMPLE_LANG,
    })
    assert_error_response(resp, 400, "MISSING_TITLE")


def test_entity_invalid_lang_format(client):
    resp = client.get("/entity", query_string={
        "lang": INVALID_LANG_FORMAT,
        "title": SAMPLE_TITLE,
    })
    assert_error_response(resp, 400, "INVALID_LANG_FORMAT")


def test_entity_unsupported_lang(client):
    resp = client.get("/entity", query_string={
        "lang": INVALID_LANG,
        "title": SAMPLE_TITLE,
    })
    assert_error_response(resp, 400, "UNSUPPORTED_LANG")


def test_entity_invalid_qid_not_found(client):
    resp = client.get("/entity", query_string={
        "qid": INVALID_QID,
    })
    assert_error_response(resp, 404, "ENTITY_NOT_FOUND")


def test_entity_invalid_title_not_found(client):
    resp = client.get("/entity", query_string={
        "lang": SAMPLE_LANG,
        "title": INVALID_TITLE,
    })
    assert_error_response(resp, 404, "QID_NOT_FOUND")


# =========================
# /qid
# =========================

def test_qid_success(client):
    resp = client.get("/qid", query_string={
        "lang": SAMPLE_LANG,
        "title": SAMPLE_TITLE,
    })
    assert resp.status_code == 200, resp.get_data(as_text=True)
    payload = resp.get_json()
    assert_qid_success(payload)


def test_qid_missing_lang(client):
    resp = client.get("/qid", query_string={
        "title": SAMPLE_TITLE,
    })
    assert_error_response(resp, 400, "MISSING_LANG")


def test_qid_missing_title(client):
    resp = client.get("/qid", query_string={
        "lang": SAMPLE_LANG,
    })
    assert_error_response(resp, 400, "MISSING_TITLE")


def test_qid_invalid_lang_format(client):
    resp = client.get("/qid", query_string={
        "lang": INVALID_LANG_FORMAT,
        "title": SAMPLE_TITLE,
    })
    assert_error_response(resp, 400, "INVALID_LANG_FORMAT")


def test_qid_unsupported_lang(client):
    resp = client.get("/qid", query_string={
        "lang": INVALID_LANG,
        "title": SAMPLE_TITLE,
    })
    assert_error_response(resp, 400, "UNSUPPORTED_LANG")


def test_qid_invalid_title_not_found(client):
    resp = client.get("/qid", query_string={
        "lang": SAMPLE_LANG,
        "title": INVALID_TITLE,
    })
    assert_error_response(resp, 404, "QID_NOT_FOUND")


# =========================
# /cache/stats
# =========================

def test_cache_stats(client):
    resp = client.get("/cache/stats")
    assert resp.status_code == 200, resp.get_data(as_text=True)
    payload = resp.get_json()

    assert isinstance(payload, dict)
    assert "search_cache" in payload
    assert "zim_cache" in payload

    if "entity_cache" in payload:
        assert isinstance(payload["entity_cache"], dict)
    if "qid_cache" in payload:
        assert isinstance(payload["qid_cache"], dict)
