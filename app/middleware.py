from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.settings import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.events: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable):
        # Keep docs/static unrestricted
        if request.url.path.startswith("/docs") or request.url.path.startswith("/openapi") or request.url.path.startswith("/static"):
            return await call_next(request)

        now = time.time()
        key = request.client.host if request.client else "unknown"
        q = self.events[key]

        window = settings.rate_limit_window_seconds
        while q and q[0] <= now - window:
            q.popleft()

        if len(q) >= settings.rate_limit_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "retryAfterSeconds": int(window - (now - q[0])) if q else window},
            )

        q.append(now)
        return await call_next(request)
