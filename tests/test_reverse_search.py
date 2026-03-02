import pytest

from app.services import reverse_search


@pytest.mark.asyncio
async def test_reverse_search_isolates_engine_failures(monkeypatch, tmp_path):
    async def ok(_):
        return [{"engine": "ok", "url": "https://example.com", "score": 1}]

    async def boom(_):
        raise RuntimeError("engine down")

    async def no_date(_):
        return None

    monkeypatch.setattr(reverse_search, "search_google_vision", ok)
    monkeypatch.setattr(reverse_search, "search_yandex", boom)
    monkeypatch.setattr(reverse_search, "search_tineye", ok)
    monkeypatch.setattr(reverse_search, "infer_published_at", no_date)

    fp = tmp_path / "f.jpg"
    fp.write_bytes(b"x")

    out = await reverse_search.reverse_search_frame(fp)
    assert len(out) == 2
    assert all(item["engine"] == "ok" for item in out)
