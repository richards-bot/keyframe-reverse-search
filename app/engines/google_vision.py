from __future__ import annotations

import base64
import os
from pathlib import Path

import httpx


async def search_google_vision(frame_path: Path) -> list[dict]:
    api_key = os.getenv("GOOGLE_VISION_API_KEY")
    if not api_key:
        return []

    image_b64 = base64.b64encode(frame_path.read_bytes()).decode("utf-8")
    payload = {
        "requests": [
            {
                "image": {"content": image_b64},
                "features": [{"type": "WEB_DETECTION", "maxResults": 10}],
            }
        ]
    }

    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    out = []
    responses = data.get("responses", [])
    if not responses:
        return out

    web = responses[0].get("webDetection", {})
    for p in web.get("pagesWithMatchingImages", []):
        out.append(
            {
                "engine": "google_vision",
                "url": p.get("url"),
                "score": p.get("score", 0),
            }
        )
    return out
