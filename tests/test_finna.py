import pytest

from app_cli import finna


class FakeResponse:
    def __init__(self, payload, status_ok=True):
        self._payload = payload
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise finna.requests.HTTPError("bad status")

    def json(self):
        return self._payload


def test_resolve_title_caches_result(monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return FakeResponse(
            {
                "records": [
                    {
                        "id": "abc123",
                        "title": "Dune",
                        "subjects": [["science fiction"], ["desert planets"]],
                        "rating": {"count": 3, "average": 85},
                    }
                ]
            }
        )

    monkeypatch.setattr(finna.requests, "get", fake_get)

    result = finna.resolve_title("Dune")
    assert result["finna_id"] == "abc123"
    assert result["subjects"] == ["desert planets", "science fiction"]
    assert result["community_rating"] == {"count": 3, "average": 85}

    # Second call should hit the cache, not the network.
    finna.resolve_title("Dune")
    assert len(calls) == 1


def test_resolve_title_no_match_returns_none(monkeypatch):
    monkeypatch.setattr(
        finna.requests, "get", lambda url, params=None, timeout=None: FakeResponse({"records": []})
    )
    assert finna.resolve_title("Some Obscure Title") is None


def test_resolve_title_zero_count_rating_is_none(monkeypatch):
    monkeypatch.setattr(
        finna.requests,
        "get",
        lambda url, params=None, timeout=None: FakeResponse(
            {
                "records": [
                    {
                        "id": "xyz",
                        "title": "Obscure Book",
                        "subjects": [],
                        "rating": {"count": 0, "average": 0},
                    }
                ]
            }
        ),
    )
    result = finna.resolve_title("Obscure Book")
    assert result["community_rating"] is None


def test_resolve_title_raises_on_request_error(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise finna.requests.ConnectionError("network down")

    monkeypatch.setattr(finna.requests, "get", fake_get)
    with pytest.raises(finna.FinnaLookupError):
        finna.resolve_title("Dune")


def test_search_by_subjects_excludes_tracked_and_ranks_by_rating(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return FakeResponse(
            {
                "records": [
                    {
                        "id": "1",
                        "title": "Already Tracked",
                        "authors": {"primary": {"Someone": {}}},
                        "rating": {"count": 1, "average": 50},
                    },
                    {
                        "id": "2",
                        "title": "New Book Low",
                        "authors": {"primary": {"Author Low": {}}},
                        "rating": {"count": 2, "average": 40},
                    },
                    {
                        "id": "3",
                        "title": "New Book High",
                        "authors": {"primary": {"Author High": {}}},
                        "rating": {"count": 5, "average": 90},
                    },
                ]
            }
        )

    monkeypatch.setattr(finna.requests, "get", fake_get)

    results = finna.search_by_subjects(
        ["science fiction"], exclude_titles={"already tracked"}, limit=5
    )
    titles = [r["title"] for r in results]
    assert "Already Tracked" not in titles
    assert titles == ["New Book High", "New Book Low"]


def test_search_by_subjects_handles_authors_primary_as_empty_list(monkeypatch):
    # Finna returns authors.primary as [] (not {}) for records with no
    # primary author, e.g. "Chuggington : Klik-klok" under a real subject
    # facet query — confirmed against the live API.
    monkeypatch.setattr(
        finna.requests,
        "get",
        lambda url, params=None, timeout=None: FakeResponse(
            {
                "records": [
                    {
                        "id": "1",
                        "title": "Authorless Book",
                        "authors": {"primary": []},
                        "rating": {"count": 0, "average": 0},
                    }
                ]
            }
        ),
    )

    results = finna.search_by_subjects(["some subject"], exclude_titles=set(), limit=5)
    assert results == [
        {"title": "Authorless Book", "author": None, "community_rating": None}
    ]


def test_search_by_subjects_skips_failing_subject_and_keeps_others(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        if "broken subject" in params["filter[]"]:
            raise finna.requests.ConnectionError("network down")
        return FakeResponse(
            {
                "records": [
                    {
                        "id": "1",
                        "title": "Working Book",
                        "authors": {"primary": {"Author": {}}},
                        "rating": {"count": 1, "average": 70},
                    }
                ]
            }
        )

    monkeypatch.setattr(finna.requests, "get", fake_get)

    results = finna.search_by_subjects(
        ["broken subject", "good subject"], exclude_titles=set(), limit=5
    )
    titles = [r["title"] for r in results]
    assert titles == ["Working Book"]


def test_summarize_buildings_keeps_city_and_branch_drops_network_and_shelf():
    buildings = [
        {"value": "0/Helmet/", "translated": "Helmet-kirjastot"},
        {"value": "1/Helmet/h/", "translated": "Helsinki"},
        {"value": "2/Helmet/h/h01l/", "translated": "Pasila lapset"},
        {"value": "3/Helmet/h/h01l/2/", "translated": "2"},
    ]
    assert finna._summarize_buildings(buildings) == ["Helsinki", "Pasila lapset"]


def test_summarize_buildings_caps_at_max_locations():
    buildings = [
        {"value": f"2/Net/{i}/", "translated": f"Branch {i}"} for i in range(10)
    ]
    result = finna._summarize_buildings(buildings)
    assert len(result) == finna.MAX_LOCATIONS


def test_summarize_buildings_handles_empty_and_malformed_entries():
    assert finna._summarize_buildings([]) == []
    assert finna._summarize_buildings([{"value": "", "translated": "x"}]) == []


def _title_search_record(**overrides):
    record = {
        "id": "1",
        "title": "Foundation",
        "authors": {"primary": {"Asimov, Isaac": {"role": ["kirjoittaja"]}}},
        "year": "1951",
        "formats": [{"value": "0/Book/", "translated": "Kirja"}],
        "rating": {"count": 12, "average": 88},
        "buildings": [
            {"value": "0/Helmet/", "translated": "Helmet-kirjastot"},
            {"value": "1/Helmet/h/", "translated": "Helsinki"},
            {"value": "2/Helmet/h/h01l/", "translated": "Pasila lapset"},
        ],
    }
    record.update(overrides)
    return record


def test_search_by_title_returns_full_result_shape(monkeypatch):
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["params"] = params
        return FakeResponse({"records": [_title_search_record()]})

    monkeypatch.setattr(finna.requests, "get", fake_get)

    results = finna.search_by_title("Foundation", limit=10)
    assert results == [
        {
            "title": "Foundation",
            "author": "Asimov, Isaac",
            "year": "1951",
            "format": "Kirja",
            "community_rating": {"count": 12, "average": 88},
            "locations": ["Helsinki", "Pasila lapset"],
        }
    ]
    assert captured["params"]["type"] == "Title"
    assert captured["params"]["lookfor"] == "Foundation"


def test_search_by_author_uses_author_search_type(monkeypatch):
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["params"] = params
        return FakeResponse({"records": [_title_search_record()]})

    monkeypatch.setattr(finna.requests, "get", fake_get)

    results = finna.search_by_author("Isaac Asimov", limit=10)
    assert results[0]["author"] == "Asimov, Isaac"
    assert captured["params"]["type"] == "Author"
    assert captured["params"]["lookfor"] == "Isaac Asimov"


def test_search_by_title_returns_empty_list_when_no_matches(monkeypatch):
    monkeypatch.setattr(
        finna.requests, "get", lambda url, params=None, timeout=None: FakeResponse({"records": []})
    )
    assert finna.search_by_title("Some Obscure Title", limit=10) == []


def test_search_by_title_raises_on_request_error(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise finna.requests.ConnectionError("network down")

    monkeypatch.setattr(finna.requests, "get", fake_get)
    with pytest.raises(finna.FinnaLookupError):
        finna.search_by_title("Foundation", limit=10)


def test_search_by_title_handles_missing_year_and_format(monkeypatch):
    record = _title_search_record(year=None, formats=[])
    monkeypatch.setattr(
        finna.requests, "get", lambda url, params=None, timeout=None: FakeResponse({"records": [record]})
    )
    result = finna.search_by_title("Foundation", limit=10)[0]
    assert result["year"] is None
    assert result["format"] is None


def test_search_by_title_handles_authors_primary_as_empty_list(monkeypatch):
    record = _title_search_record(authors={"primary": []})
    monkeypatch.setattr(
        finna.requests, "get", lambda url, params=None, timeout=None: FakeResponse({"records": [record]})
    )
    result = finna.search_by_title("Foundation", limit=10)[0]
    assert result["author"] is None
