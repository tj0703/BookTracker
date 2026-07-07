import pytest

from app_cli import finna

pytestmark = pytest.mark.e2e_live


def test_resolve_title_against_real_finna_api():
    result = finna.resolve_title("Harry Potter")

    assert result is not None, "expected a real match from Finna for a well-known title"
    assert result["finna_id"]
    assert isinstance(result["subjects"], list)
    assert len(result["subjects"]) > 0
    assert result["community_rating"] is None or set(result["community_rating"]) == {
        "count",
        "average",
    }


def test_search_by_subjects_against_real_finna_api():
    resolved = finna.resolve_title("Harry Potter")
    assert resolved is not None

    candidates = finna.search_by_subjects(
        resolved["subjects"][:1], exclude_titles=set(), limit=3
    )

    assert isinstance(candidates, list)
    for candidate in candidates:
        assert "title" in candidate
        assert "author" in candidate
        assert "community_rating" in candidate


def test_search_by_title_against_real_finna_api():
    results = finna.search_by_title("Harry Potter", limit=5)

    assert isinstance(results, list)
    assert len(results) > 0, "expected real matches from Finna for a well-known title"
    for result in results:
        assert set(result) == {
            "title",
            "author",
            "year",
            "format",
            "community_rating",
            "locations",
        }
        assert isinstance(result["locations"], list)
        assert len(result["locations"]) <= finna.MAX_LOCATIONS
        assert result["community_rating"] is None or set(result["community_rating"]) == {
            "count",
            "average",
        }


def test_search_by_author_against_real_finna_api():
    results = finna.search_by_author("Tove Jansson", limit=5)

    assert isinstance(results, list)
    assert len(results) > 0, "expected real matches from Finna for a well-known author"
    for result in results:
        assert set(result) == {
            "title",
            "author",
            "year",
            "format",
            "community_rating",
            "locations",
        }


def test_search_by_title_no_match_returns_empty_list_against_real_api():
    results = finna.search_by_title("asdkjfhalskdjfhalskdjfhqwerty", limit=5)
    assert results == []
