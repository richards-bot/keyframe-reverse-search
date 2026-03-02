from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.settings import settings


def require_api_key(request: Request) -> None:
    if not settings.api_key:
        return
    key = request.headers.get("x-api-key")
    if not key or key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
