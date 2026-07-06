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
