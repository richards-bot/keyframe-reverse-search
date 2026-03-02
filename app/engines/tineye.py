from __future__ import annotations

import os
from pathlib import Path

import httpx


async def search_tineye(frame_path: Path) -> list[dict]:
    base_url = os.getenv("TINEYE_API_URL")
    user = os.getenv("TINEYE_API_USER")
    key = os.getenv("TINEYE_API_KEY")
    if not (base_url and user and key):
        return []

    files = {"image_upload": (frame_path.name, frame_path.read_bytes(), "image/jpeg")}
    params = {"sort": "crawl_date", "order": "asc", "limit": "20"}

    async with httpx.AsyncClient(timeout=30, auth=(user, key)) as client:
        resp = await client.post(base_url, params=params, files=files)
        resp.raise_for_status()
        data = resp.json()

    out = []
    for m in data.get("results", {}).get("matches", []):
        for back in m.get("backlinks", []):
            out.append(
                {
                    "engine": "tineye",
                    "url": back.get("url"),
                    "score": m.get("score", 0),
                    "publishedAt": back.get("crawl_date"),
                }
            )
    return out
