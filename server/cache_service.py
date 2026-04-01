import time
import threading
from collections import OrderedDict
from functools import wraps


class CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value, expires_at):
        self.value = value
        self.expires_at = expires_at


class InFlight:
    """
    用于同 key 并发合并（single-flight）：
    同一个 key 在 miss 时，只允许一个线程执行加载函数，
    其他线程等待它完成并复用结果。
    """
    __slots__ = ("event", "result", "error")

    def __init__(self):
        self.event = threading.Event()
        self.result = None
        self.error = None


class ThreadSafeTTLCache:
    """
    线程安全的本地内存缓存：
    - TTL 过期
    - LRU 淘汰
    - 同 key 并发合并
    """

    def __init__(self, maxsize=1024, default_ttl=60):
        self.maxsize = maxsize
        self.default_ttl = default_ttl

        self._lock = threading.RLock()
        self._store = OrderedDict()   # key -> CacheEntry
        self._inflight = {}           # key -> InFlight

        self._hits = 0
        self._misses = 0
        self._loads = 0
        self._evictions = 0
        self._expirations = 0

    def _now(self):
        return time.monotonic()

    def _is_expired(self, entry, now=None):
        if now is None:
            now = self._now()
        return entry.expires_at <= now

    def _delete_no_lock(self, key):
        self._store.pop(key, None)

    def _prune_expired_no_lock(self):
        now = self._now()
        expired_keys = [k for k, entry in self._store.items() if self._is_expired(entry, now)]
        for k in expired_keys:
            self._store.pop(k, None)
            self._expirations += 1

    def _evict_if_needed_no_lock(self):
        while len(self._store) > self.maxsize:
            self._store.popitem(last=False)  # LRU: 弹出最旧的
            self._evictions += 1

    def get(self, key, default=None):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return default

            if self._is_expired(entry):
                self._store.pop(key, None)
                self._misses += 1
                self._expirations += 1
                return default

            # 命中后移动到末尾，表示最近使用
            self._store.move_to_end(key)
            self._hits += 1
            return entry.value

    def set(self, key, value, ttl=None):
        if ttl is None:
            ttl = self.default_ttl
        expires_at = self._now() + ttl

        with self._lock:
            self._store[key] = CacheEntry(value=value, expires_at=expires_at)
            self._store.move_to_end(key)
            self._evict_if_needed_no_lock()

    def delete(self, key):
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        with self._lock:
            self._store.clear()
            self._inflight.clear()

    def has(self, key):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            if self._is_expired(entry):
                self._store.pop(key, None)
                self._expirations += 1
                return False
            return True

    def stats(self):
        with self._lock:
            return {
                "size": len(self._store),
                "maxsize": self.maxsize,
                "default_ttl": self.default_ttl,
                "hits": self._hits,
                "misses": self._misses,
                "loads": self._loads,
                "evictions": self._evictions,
                "expirations": self._expirations,
                "inflight": len(self._inflight),
            }

    def get_or_set(self, key, loader, ttl=None, cache_none=False):
        """
        线程安全读取缓存；如未命中，则调用 loader() 加载。
        对同一个 key，只有一个线程会真的执行 loader，其它线程等待结果。
        """
        # 第一阶段：先尝试命中
        with self._lock:
            entry = self._store.get(key)
            if entry is not None and not self._is_expired(entry):
                self._store.move_to_end(key)
                self._hits += 1
                return entry.value

            if entry is not None and self._is_expired(entry):
                self._store.pop(key, None)
                self._expirations += 1

            self._misses += 1

            # 是否已有线程在加载这个 key
            inflight = self._inflight.get(key)
            if inflight is None:
                inflight = InFlight()
                self._inflight[key] = inflight
                is_loader = True
                self._loads += 1
            else:
                is_loader = False

        # 第二阶段：若不是 loader 线程，等待结果
        if not is_loader:
            inflight.event.wait()
            if inflight.error is not None:
                raise inflight.error
            return inflight.result

        # 第三阶段：真正加载
        try:
            value = loader()
            inflight.result = value

            if value is not None or cache_none:
                self.set(key, value, ttl=ttl)

            return value
        except Exception as e:
            inflight.error = e
            raise
        finally:
            with self._lock:
                inflight.event.set()
                self._inflight.pop(key, None)


def default_key_builder(func, args, kwargs):
    """
    通用默认 key 生成器。
    要求参数可 repr 且结果稳定；更复杂场景建议自行传 key_func。
    """
    return (
        func.__module__,
        func.__qualname__,
        repr(args),
        repr(sorted(kwargs.items(), key=lambda x: x[0])),
    )


def cached(cache, ttl=None, key_func=None, cache_none=False):
    """
    通用装饰器：
    @cached(cache=..., ttl=30)
    def fn(...): ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if key_func is None:
                key = default_key_builder(func, args, kwargs)
            else:
                key = key_func(*args, **kwargs)

            return cache.get_or_set(
                key=key,
                loader=lambda: func(*args, **kwargs),
                ttl=ttl,
                cache_none=cache_none,
            )

        return wrapper
    return decorator
