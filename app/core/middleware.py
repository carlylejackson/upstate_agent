import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["x-request-id"] = request_id
        response.headers["x-process-time-ms"] = f"{duration_ms:.2f}"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory fixed-window limiter for single-process deployments.
    For multi-instance production, replace with shared-store limiter (Redis).
    """

    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._redis = None
        self._redis_enabled = False
        redis_url = getattr(self.settings, "redis_url", None)
        if redis_url:
            try:
                from redis import Redis

                self._redis = Redis.from_url(redis_url, decode_responses=True)
                self._redis_enabled = True
            except Exception:  # noqa: BLE001
                self._redis = None
                self._redis_enabled = False

    async def dispatch(self, request: Request, call_next):
        if not self.settings.rate_limit_enabled:
            return await call_next(request)

        path = request.url.path
        if path in self.settings.rate_limit_exempt_paths_list or path.startswith("/widget/"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{path}"
        now = time.time()
        window_seconds = 60
        max_requests = max(1, self.settings.rate_limit_requests_per_minute)

        if self._redis_enabled and self._redis is not None:
            try:
                redis_key = f"ratelimit:{key}:{int(now // window_seconds)}"
                count = self._redis.incr(redis_key)
                if count == 1:
                    self._redis.expire(redis_key, window_seconds)
                if count > max_requests:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Rate limit exceeded. Please retry shortly.",
                            "limit_per_minute": max_requests,
                        },
                    )
                return await call_next(request)
            except Exception:  # noqa: BLE001
                pass

        with self._lock:
            bucket = self._buckets[key]
            while bucket and (now - bucket[0]) > window_seconds:
                bucket.popleft()
            if len(bucket) >= max_requests:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Please retry shortly.",
                        "limit_per_minute": max_requests,
                    },
                )
            bucket.append(now)

        return await call_next(request)
