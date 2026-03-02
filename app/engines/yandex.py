from __future__ import annotations

import os
from pathlib import Path

import httpx


async def search_yandex(frame_path: Path) -> list[dict]:
    """
    MVP adapter using SerpAPI's Yandex Images engine as a practical API bridge.
    Set SERPAPI_KEY to enable.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return []

    params = {
        "engine": "yandex_images",
        "api_key": api_key,
        "url": f"file://{frame_path}",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get("https://serpapi.com/search", params=params)
        if resp.status_code >= 400:
            return []
        data = resp.json()

    out = []
    for item in data.get("image_results", []):
        out.append(
            {
                "engine": "yandex",
                "url": item.get("link") or item.get("source"),
                "score": item.get("position", 0),
            }
        )
    return out
