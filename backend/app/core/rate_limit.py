import threading
import time

from fastapi import HTTPException, status

from app.core.config import get_settings


class RateLimiter:
    """Fixed-window, in-process limiter. Sufficient for a single backend instance;
    use a shared store (e.g. Redis) when running several instances."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        if not get_settings().RATE_LIMIT_ENABLED:
            return
        now = time.monotonic()
        with self._lock:
            start, count = self._hits.get(key, (now, 0))
            if now - start >= self.window:
                start, count = now, 0
            count += 1
            self._hits[key] = (start, count)
            if len(self._hits) > 10_000:
                self._hits = {k: v for k, v in self._hits.items() if now - v[0] < self.window}
        if count > self.limit:
            retry_after = int(self.window - (now - start)) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait and try again.",
                headers={"Retry-After": str(retry_after)},
            )

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


login_limiter = RateLimiter(limit=10, window_seconds=60)
register_limiter = RateLimiter(limit=5, window_seconds=60)
upload_limiter = RateLimiter(limit=20, window_seconds=3600)
geocode_limiter = RateLimiter(limit=30, window_seconds=60)
