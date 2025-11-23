from django.core.cache import cache
from rest_framework.response import Response
import hashlib


def _make_cache_key(request, prefix: str) -> str:
    user_part = f"user:{getattr(request.user, 'pk', 'anon')}"
    path = request.path
    qs = request.META.get("QUERY_STRING", "")
    raw = f"{prefix}|{user_part}|{path}|{qs}"
    return "viewcache:" + hashlib.sha256(raw.encode()).hexdigest()


def get_cached_response(request, prefix: str):
    if request.method != "GET":
        return None

    key = _make_cache_key(request, prefix)
    payload = cache.get(key)
    if not payload:
        return None

    return Response(payload["data"], status=payload.get("status", 200))


def set_cached_response(
    request, prefix: str, response: Response, timeout: int | None = None
):
    key = _make_cache_key(request, prefix)
    payload = {"data": response.data, "status": response.status_code}
    cache.set(key, payload, timeout)


def invalidate_cache(request, prefix: str):
    key = _make_cache_key(request, prefix)
    cache.delete(key)


def _should_bypass_cache(request) -> bool:
    """Check if caching should be bypassed"""
    return request.GET.get("nocache", "false").lower() == "true"


# Generic key-value cache helpers (not tied to a request)
def _make_generic_key(key: str) -> str:
    """Create a stable cache key for generic values."""
    raw = f"genericcache:{key}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached_value(key: str):
    """Return a cached value stored under `key` or None."""
    full_key = "genericcache:" + key
    return cache.get(full_key)


def set_cached_value(key: str, value, timeout: int | None = None):
    full_key = "genericcache:" + key
    cache.set(full_key, value, timeout)


def invalidate_cached_key(key: str):
    full_key = "genericcache:" + key
    cache.delete(full_key)


def invalidate_pattern(prefix: str):
    """Invalidate keys by prefix pattern.

    This is best-effort and supports django-redis (preferred) or falls back to
    attempting to use underlying cache client's `keys`/`scan_iter` methods.
    It swallows errors to avoid raising in production when the backend doesn't
    support key scanning.
    """
    pattern = f"genericcache:{prefix}*"
    try:
        # Try django-redis helper first (recommended when using Redis)
        try:
            from django_redis import get_redis_connection

            conn = get_redis_connection("default")
            # Use scan_iter to avoid blocking Redis
            keys = [k for k in conn.scan_iter(match=pattern)]
            if keys:
                # redis-py returns bytes for keys in Python3; delete accepts them
                conn.delete(*keys)
                return
        except Exception:
            # Fall through to other approaches
            pass

        # Try raw client exposed on cache backend
        try:
            raw = getattr(cache, "_cache", None)
            if raw is not None:
                # redis-py client
                keys = raw.keys(pattern)
                if keys:
                    raw.delete(*keys)
                    return
        except Exception:
            pass

        # No further fallback available; pattern invalidation is best-effort.
    except Exception:
        # Do not raise; invalidation is best-effort only
        return
