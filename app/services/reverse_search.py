from __future__ import annotations

import asyncio
from pathlib import Path

from app.engines.google_vision import search_google_vision
from app.engines.tineye import search_tineye
from app.engines.yandex import search_yandex
from app.services.date_extract import infer_published_at


async def reverse_search_frame(frame_path: Path) -> list[dict]:
    google_task = search_google_vision(frame_path)
    yandex_task = search_yandex(frame_path)
    tineye_task = search_tineye(frame_path)

    google_res, yandex_res, tineye_res = await asyncio.gather(
        google_task,
        yandex_task,
        tineye_task,
        return_exceptions=False,
    )

    results = [*google_res, *yandex_res, *tineye_res]

    # enrich with publication dates (best effort)
    sem = asyncio.Semaphore(8)

    async def enrich(item: dict):
        if item.get("publishedAt"):
            return item
        async with sem:
            item["publishedAt"] = await infer_published_at(item["url"])
        return item

    enriched = await asyncio.gather(*[enrich(r) for r in results])
    return enriched
