import os
import pytest
import requests


# =========================
# Config
# =========================

BASE_URL = os.getenv("API_BASE_URL", None)
if not BASE_URL:
    pytest.skip("API_BASE_URL environment variable is not set", allow_module_level=True)

from test.test_server.config import SAMPLE_LANG, SAMPLE_TITLE, SAMPLE_QID, INVALID_LANG, INVALID_LANG_FORMAT, INVALID_QID, INVALID_TITLE


# =========================
# Helpers
# =========================

def build_url(path: str) -> str:
    return f"{BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def get_json(path: str, params=None):
    """
    发请求并尽量解析 JSON。
    返回 (response, payload)
    """
    response = requests.get(build_url(path), params=params, timeout=20)
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    return response, payload


def assert_error_response(response, payload, expected_status, expected_code=None):
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}, payload={payload}"
    )
    assert isinstance(payload, dict), f"Expected dict JSON payload, got: {type(payload)} / {payload}"
    assert "error" in payload, f"Expected 'error' in payload, got: {payload}"

    error = payload["error"]
    assert isinstance(error, dict), f"Expected error object, got: {error}"
    assert "message" in error, f"Expected error.message, got: {payload}"
    assert isinstance(error["message"], str) and error["message"].strip(), (
        f"Expected non-empty error.message, got: {payload}"
    )

    if expected_code is not None:
        assert error.get("code") == expected_code, (
            f"Expected error code {expected_code}, got {error.get('code')}, payload={payload}"
        )


def assert_search_success(payload):
    assert isinstance(payload, dict), f"search payload must be dict, got: {type(payload)} / {payload}"
    assert "total_matches" in payload, f"Missing total_matches in payload: {payload}"
    assert "results" in payload, f"Missing results in payload: {payload}"
    assert isinstance(payload["results"], list), f"results must be list, got: {type(payload['results'])}"

    for item in payload["results"]:
        assert isinstance(item, dict), f"Each result must be dict, got: {item}"
        assert "qid" in item
        assert "lang" in item
        assert "best_match_name" in item
        assert "matched_names" in item
        assert "matched_source_types" in item
        assert "has_wiki_page" in item


def assert_entity_success(payload):
    assert isinstance(payload, dict), f"entity payload must be dict, got: {type(payload)} / {payload}"
    assert "qid" in payload
    assert "labels" in payload
    assert "descriptions" in payload
    assert "sitelinks" in payload
    assert "wikipedia_lang_count" in payload
    assert "sitelink_count_total" in payload
    assert "has_wiki_page" in payload

    assert isinstance(payload["labels"], dict)
    assert isinstance(payload["descriptions"], dict)
    assert isinstance(payload["sitelinks"], dict)
    assert isinstance(payload["has_wiki_page"], dict)
    
    for lang, has_page in payload["has_wiki_page"].items():
        assert isinstance(lang, str), f"has_wiki_page key must be str, got: {type(lang)}"
        assert isinstance(has_page, bool), f"has_wiki_page value must be bool, got: {type(has_page)}"


def assert_qid_success(payload):
    # /qid 当前返回 jsonify(qid)，requests.json() 后通常是字符串
    assert isinstance(payload, str), f"qid payload must be string, got: {type(payload)} / {payload}"
    assert payload.startswith("Q"), f"qid must start with Q, got: {payload}"


def assert_read_success(payload):
    # /read 当前返回 jsonify(page)，requests.json() 后通常是字符串
    assert isinstance(payload, str), f"read payload must be string, got: {type(payload)} / {payload}"
    assert payload.strip(), "read payload should not be empty"

    # 不强制要求一定包含 html 标签，避免不同页面格式差异
    # 但一般会是 HTML 文本
    assert len(payload) > 20, f"read payload seems too short: {payload!r}"


# =========================
# Fixtures
# =========================

@pytest.fixture(scope="session")
def sample_lang():
    return SAMPLE_LANG


@pytest.fixture(scope="session")
def sample_title():
    return SAMPLE_TITLE


@pytest.fixture(scope="session")
def sample_qid():
    return SAMPLE_QID


# =========================
# Healthz
# =========================

def test_healthz():
    response, payload = get_json("/healthz")
    assert response.status_code == 200
    assert isinstance(payload, dict)
    assert payload.get("ok") is True


# =========================
# /search
# =========================

def test_search_success(sample_lang, sample_title):
    response, payload = get_json("/search", {
        "lang": sample_lang,
        "query": sample_title,
    })
    assert response.status_code == 200, payload
    assert_search_success(payload)


def test_search_success_with_limit(sample_lang, sample_title):
    response, payload = get_json("/search", {
        "lang": sample_lang,
        "query": sample_title,
        "limit": 3,
    })
    assert response.status_code == 200, payload
    assert_search_success(payload)


def test_search_missing_lang(sample_title):
    response, payload = get_json("/search", {
        "query": sample_title,
    })
    assert_error_response(response, payload, 400, "MISSING_LANG")


def test_search_missing_query(sample_lang):
    response, payload = get_json("/search", {
        "lang": sample_lang,
    })
    assert_error_response(response, payload, 400, "MISSING_QUERY")


def test_search_invalid_lang_format(sample_title):
    response, payload = get_json("/search", {
        "lang": INVALID_LANG_FORMAT,
        "query": sample_title,
    })
    assert_error_response(response, payload, 400, "INVALID_LANG_FORMAT")


def test_search_unsupported_lang(sample_title):
    response, payload = get_json("/search", {
        "lang": INVALID_LANG,
        "query": sample_title,
    })
    # 如果你的 INVALID_LANG 恰好被加入 valid_langs，这个测试会失败，届时改一下测试数据即可
    assert_error_response(response, payload, 400, "UNSUPPORTED_LANG")


@pytest.mark.parametrize("limit", ["abc", "1.5", "0", "-1"])
def test_search_invalid_limit(sample_lang, sample_title, limit):
    response, payload = get_json("/search", {
        "lang": sample_lang,
        "query": sample_title,
        "limit": limit,
    })
    assert_error_response(response, payload, 400, "INVALID_LIMIT")


# =========================
# /read
# =========================

def test_read_by_qid_success(sample_lang, sample_qid):
    response, payload = get_json("/read", {
        "lang": sample_lang,
        "qid": sample_qid,
    })
    assert response.status_code == 200, payload
    assert_read_success(payload)


def test_read_by_title_success(sample_lang, sample_title):
    response, payload = get_json("/read", {
        "lang": sample_lang,
        "title": sample_title,
    })
    assert response.status_code == 200, payload
    assert_read_success(payload)


def test_read_missing_lang(sample_qid):
    response, payload = get_json("/read", {
        "qid": sample_qid,
    })
    assert_error_response(response, payload, 400, "MISSING_LANG")


def test_read_missing_qid_or_title(sample_lang):
    response, payload = get_json("/read", {
        "lang": sample_lang,
    })
    assert_error_response(response, payload, 400, "MISSING_QID_OR_TITLE")


def test_read_ambiguous_identifier(sample_lang, sample_qid, sample_title):
    response, payload = get_json("/read", {
        "lang": sample_lang,
        "qid": sample_qid,
        "title": sample_title,
    })
    assert_error_response(response, payload, 400, "AMBIGUOUS_IDENTIFIER")


def test_read_invalid_lang_format(sample_qid):
    response, payload = get_json("/read", {
        "lang": INVALID_LANG_FORMAT,
        "qid": sample_qid,
    })
    assert_error_response(response, payload, 400, "INVALID_LANG_FORMAT")


def test_read_unsupported_lang(sample_qid):
    response, payload = get_json("/read", {
        "lang": INVALID_LANG,
        "qid": sample_qid,
    })
    assert_error_response(response, payload, 400, "UNSUPPORTED_LANG")


def test_read_invalid_qid_not_found(sample_lang):
    response, payload = get_json("/read", {
        "lang": sample_lang,
        "qid": INVALID_QID,
    })
    # 这里按你改造后的逻辑，先查 entity，不存在则 ENTITY_NOT_FOUND
    assert_error_response(response, payload, 404, "ENTITY_NOT_FOUND")


def test_read_invalid_title_not_found(sample_lang):
    response, payload = get_json("/read", {
        "lang": sample_lang,
        "title": INVALID_TITLE,
    })
    assert_error_response(response, payload, 404, "PAGE_NOT_FOUND")


# =========================
# /entity
# =========================

def test_entity_by_qid_success(sample_qid):
    response, payload = get_json("/entity", {
        "qid": sample_qid,
    })
    assert response.status_code == 200, payload
    assert_entity_success(payload)
    assert payload["qid"] == sample_qid


def test_entity_by_title_success(sample_lang, sample_title):
    response, payload = get_json("/entity", {
        "lang": sample_lang,
        "title": sample_title,
    })
    assert response.status_code == 200, payload
    assert_entity_success(payload)


def test_entity_missing_all_params():
    response, payload = get_json("/entity")
    assert_error_response(response, payload, 400, "MISSING_QID_OR_LANG_TITLE")


def test_entity_ambiguous_identifier(sample_lang, sample_title, sample_qid):
    response, payload = get_json("/entity", {
        "qid": sample_qid,
        "lang": sample_lang,
        "title": sample_title,
    })
    assert_error_response(response, payload, 400, "AMBIGUOUS_IDENTIFIER")


def test_entity_missing_title_when_lang_provided(sample_lang):
    response, payload = get_json("/entity", {
        "lang": sample_lang,
    })
    assert_error_response(response, payload, 400, "MISSING_TITLE")


def test_entity_invalid_lang_format(sample_title):
    response, payload = get_json("/entity", {
        "lang": INVALID_LANG_FORMAT,
        "title": sample_title,
    })
    assert_error_response(response, payload, 400, "INVALID_LANG_FORMAT")


def test_entity_unsupported_lang(sample_title):
    response, payload = get_json("/entity", {
        "lang": INVALID_LANG,
        "title": sample_title,
    })
    assert_error_response(response, payload, 400, "UNSUPPORTED_LANG")


def test_entity_invalid_qid_not_found():
    response, payload = get_json("/entity", {
        "qid": INVALID_QID,
    })
    assert_error_response(response, payload, 404, "ENTITY_NOT_FOUND")


def test_entity_invalid_title_not_found(sample_lang):
    response, payload = get_json("/entity", {
        "lang": sample_lang,
        "title": INVALID_TITLE,
    })
    # 先查 qid，不存在时是 QID_NOT_FOUND
    assert_error_response(response, payload, 404, "QID_NOT_FOUND")


# =========================
# /qid
# =========================

def test_qid_success(sample_lang, sample_title):
    response, payload = get_json("/qid", {
        "lang": sample_lang,
        "title": sample_title,
    })
    assert response.status_code == 200, payload
    assert_qid_success(payload)


def test_qid_missing_lang(sample_title):
    response, payload = get_json("/qid", {
        "title": sample_title,
    })
    assert_error_response(response, payload, 400, "MISSING_LANG")


def test_qid_missing_title(sample_lang):
    response, payload = get_json("/qid", {
        "lang": sample_lang,
    })
    assert_error_response(response, payload, 400, "MISSING_TITLE")


def test_qid_invalid_lang_format(sample_title):
    response, payload = get_json("/qid", {
        "lang": INVALID_LANG_FORMAT,
        "title": sample_title,
    })
    assert_error_response(response, payload, 400, "INVALID_LANG_FORMAT")


def test_qid_unsupported_lang(sample_title):
    response, payload = get_json("/qid", {
        "lang": INVALID_LANG,
        "title": sample_title,
    })
    assert_error_response(response, payload, 400, "UNSUPPORTED_LANG")


def test_qid_invalid_title_not_found(sample_lang):
    response, payload = get_json("/qid", {
        "lang": sample_lang,
        "title": INVALID_TITLE,
    })
    assert_error_response(response, payload, 404, "QID_NOT_FOUND")


# =========================
# /cache/stats
# =========================

def test_cache_stats():
    response, payload = get_json("/cache/stats")
    assert response.status_code == 200, payload
    assert isinstance(payload, dict)

    assert "search_cache" in payload
    assert "zim_cache" in payload

    # 如果你 app.py 已经把 entity_cache/qid_cache 也返回了，则这里也顺便校验
    if "entity_cache" in payload:
        assert isinstance(payload["entity_cache"], dict)
    if "qid_cache" in payload:
        assert isinstance(payload["qid_cache"], dict)

    assert isinstance(payload["search_cache"], dict)
    assert isinstance(payload["zim_cache"], dict)
