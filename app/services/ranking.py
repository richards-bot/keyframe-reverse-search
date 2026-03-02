from __future__ import annotations


def rank_results(results: list[dict]) -> list[dict]:
    cleaned = [r for r in results if r.get("url")]
    for r in cleaned:
        r.setdefault("publishedAt", None)
        r.setdefault("score", 0)

    cleaned.sort(key=lambda x: (x.get("publishedAt") or "9999-12-31T00:00:00+00:00", -float(x.get("score", 0))))
    return cleaned
