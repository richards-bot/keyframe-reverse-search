from app.services.ranking import rank_results


def test_rank_results_orders_by_earliest_then_score_desc():
    results = [
        {"engine": "a", "url": "https://a", "score": 0.1, "publishedAt": "2024-01-02T00:00:00+00:00"},
        {"engine": "b", "url": "https://b", "score": 0.8, "publishedAt": "2024-01-01T00:00:00+00:00"},
        {"engine": "c", "url": "https://c", "score": 0.9, "publishedAt": "2024-01-01T00:00:00+00:00"},
    ]

    ranked = rank_results(results)
    assert [r["engine"] for r in ranked] == ["c", "b", "a"]


def test_rank_results_filters_missing_url():
    ranked = rank_results([
        {"engine": "a", "url": None, "score": 1},
        {"engine": "b", "url": "https://ok", "score": 1},
    ])
    assert len(ranked) == 1
    assert ranked[0]["engine"] == "b"
