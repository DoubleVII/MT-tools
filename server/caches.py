from .cache_service import ThreadSafeTTLCache

# 通用 API 缓存
# api_cache = ThreadSafeTTLCache(maxsize=5000, default_ttl=600)

# 如果你希望不同业务分不同缓存，也可以拆开：
search_cache = ThreadSafeTTLCache(maxsize=5000, default_ttl=600)
zim_cache = ThreadSafeTTLCache(maxsize=2000, default_ttl=600)
entity_cache = ThreadSafeTTLCache(maxsize=2000, default_ttl=600)
qid_cache = ThreadSafeTTLCache(maxsize=5000, default_ttl=600)