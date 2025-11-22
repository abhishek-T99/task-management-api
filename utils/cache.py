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
    if request.method != "GET":
        return

    key = _make_cache_key(request, prefix)
    payload = {"data": response.data, "status": response.status_code}
    cache.set(key, payload, timeout)


def invalidate_cache(request, prefix: str):
    key = _make_cache_key(request, prefix)
    cache.delete(key)
