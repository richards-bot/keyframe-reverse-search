from __future__ import annotations

from app.models import SearchResult


def rank_results(results: list[dict] | list[SearchResult]) -> list[dict]:
    normalized: list[SearchResult] = []
    for item in results:
        if isinstance(item, SearchResult):
            sr = item
        else:
            sr = SearchResult.model_validate(item)
        if sr.url:
            normalized.append(sr)

    normalized.sort(key=lambda x: (x.publishedAt or "9999-12-31T00:00:00+00:00", -float(x.score or 0)))
    return [item.model_dump(mode="json") for item in normalized]
