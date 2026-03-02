from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

DATE_META_KEYS = [
    "article:published_time",
    "og:published_time",
    "publish-date",
    "date",
    "parsely-pub-date",
    "dc.date",
]


async def infer_published_at(url: str, timeout_s: float = 6.0) -> str | None:
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_s) as client:
            r = await client.get(url)
            if r.status_code >= 400:
                return None
    except Exception:
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    for key in DATE_META_KEYS:
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            try:
                dt = date_parser.parse(tag["content"])
                return dt.isoformat()
            except Exception:
                continue

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    for script in scripts:
        text = script.get_text(strip=True)
        if "datePublished" in text:
            try:
                idx = text.index("datePublished")
                snippet = text[idx : idx + 200]
                maybe = snippet.split(":", 1)[1].split(",", 1)[0].strip().strip('"{}[]')
                dt = date_parser.parse(maybe)
                return dt.isoformat()
            except Exception:
                continue

    return None
