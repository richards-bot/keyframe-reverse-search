from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.engines.google_vision import search_google_vision
from app.engines.tineye import search_tineye
from app.engines.yandex import search_yandex
from app.models import SearchResult
from app.services.date_extract import infer_published_at

logger = logging.getLogger(__name__)


async def reverse_search_frame(frame_path: Path) -> list[dict]:
    engines = {
        "google_vision": search_google_vision(frame_path),
        "yandex": search_yandex(frame_path),
        "tineye": search_tineye(frame_path),
    }

    gathered = await asyncio.gather(*engines.values(), return_exceptions=True)

    results: list[SearchResult] = []
    for engine_name, engine_result in zip(engines.keys(), gathered):
        if isinstance(engine_result, Exception):
            logger.warning("Engine %s failed for %s: %s", engine_name, frame_path, engine_result)
            continue
        for row in engine_result:
            try:
                results.append(SearchResult.model_validate(row))
            except Exception:
                logger.warning("Invalid row from engine %s: %s", engine_name, row)

    sem = asyncio.Semaphore(8)

    async def enrich(item: SearchResult) -> SearchResult:
        if item.publishedAt or not item.url:
            return item
        async with sem:
            try:
                published = await infer_published_at(item.url)
            except Exception:
                published = None
        return item.model_copy(update={"publishedAt": published})

    enriched = await asyncio.gather(*[enrich(r) for r in results])
    return [r.model_dump(mode="json") for r in enriched]
