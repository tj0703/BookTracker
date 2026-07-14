from datetime import date

import pytest

from app_cli import books, finna, recommend


def add_rated(title, rating):
    books.add_book(
        books.BookEntry(
            title=title,
            date_completed=date(2026, 1, 1),
            review="Loved it." if rating and rating >= 4 else "It was okay.",
            review_date=date(2026, 1, 2),
            rating=rating,
        )
    )


def test_recommend_locked_below_threshold():
    add_rated("Book One", 5)
    with pytest.raises(recommend.NotEnoughDataError) as exc_info:
        recommend.get_recommendations()
    assert exc_info.value.rated == 1
    assert exc_info.value.threshold == books.RATING_THRESHOLD


def test_recommend_uses_liked_books_and_excludes_tracked(monkeypatch):
    for i in range(books.RATING_THRESHOLD):
        add_rated(f"Book {i}", 5 if i == 0 else 3)

    def fake_resolve_title(title):
        if title == "Book 0":
            return {
                "finna_id": "1",
                "subjects": ["science fiction"],
                "community_rating": None,
                "fetched_at": "2026-01-01T00:00:00+00:00",
            }
        return None

    captured = {}

    def fake_search_by_subjects(subjects, exclude_titles, limit):
        captured["subjects"] = subjects
        captured["exclude_titles"] = exclude_titles
        return [{"title": "Recommended Book", "author": "Someone", "community_rating": None}]

    monkeypatch.setattr(finna, "resolve_title", fake_resolve_title)
    monkeypatch.setattr(finna, "search_by_subjects", fake_search_by_subjects)

    results = recommend.get_recommendations()
    assert results == [{"title": "Recommended Book", "author": "Someone", "community_rating": None}]
    assert captured["subjects"] == ["science fiction"]
    assert "book 0" in captured["exclude_titles"]


# A realistic 10-book library, exercising the full RATING_THRESHOLD gate
# with varied ratings (1-5) rather than the generic "Book 0".."Book 9"
# placeholders used above. Several liked (rating >= LIKED_RATING_MIN) books
# share overlapping subjects so the weighted-aggregation logic in
# get_recommendations() actually has something to aggregate; a couple of
# lower-rated/unrelated-genre books are mixed in to prove they don't
# contribute to the subject weighting (their titles are never resolved).
REALISTIC_BOOKS = [
    ("Dune", 5),
    ("Foundation", 5),
    ("The Left Hand of Darkness", 4),
    ("Neuromancer", 4),
    ("The Hobbit", 5),
    ("Pride and Prejudice", 3),
    ("The Da Vinci Code", 2),
    ("1984", 4),
    ("Brave New World", 3),
    ("The Great Gatsby", 1),
]

# Finna subjects for the liked (rating >= 4) titles only. Deliberately
# overlapping: "science fiction" appears in 5 of the 6 liked books and
# "politics" in 3, so both should outrank subjects that appear in only a
# single liked book.
SUBJECTS_BY_LIKED_TITLE = {
    "Dune": ["science fiction", "desert planets", "politics"],
    "Foundation": ["science fiction", "space opera", "politics"],
    "The Left Hand of Darkness": ["science fiction", "gender", "anthropology"],
    "Neuromancer": ["science fiction", "cyberpunk", "artificial intelligence"],
    "The Hobbit": ["fantasy", "adventure", "dragons"],
    "1984": ["science fiction", "dystopia", "politics"],
}


def test_recommend_aggregates_subject_weights_across_realistic_books(monkeypatch):
    for title, rating in REALISTIC_BOOKS:
        add_rated(title, rating)

    def fake_resolve_title(title):
        # KeyError (test failure) if get_recommendations() ever resolves a
        # title for a book that isn't liked - only liked books should be
        # looked up.
        subjects = SUBJECTS_BY_LIKED_TITLE[title]
        return {
            "finna_id": title,
            "subjects": subjects,
            "community_rating": None,
            "fetched_at": "2026-01-01T00:00:00+00:00",
        }

    captured = {}

    def fake_search_by_subjects(subjects, exclude_titles, limit):
        captured["subjects"] = subjects
        captured["exclude_titles"] = exclude_titles
        captured["limit"] = limit
        return [
            {
                "title": "Hyperion",
                "author": "Dan Simmons",
                "community_rating": {"count": 10, "average": 90},
            }
        ]

    monkeypatch.setattr(finna, "resolve_title", fake_resolve_title)
    monkeypatch.setattr(finna, "search_by_subjects", fake_search_by_subjects)

    results = recommend.get_recommendations()

    assert results == [
        {
            "title": "Hyperion",
            "author": "Dan Simmons",
            "community_rating": {"count": 10, "average": 90},
        }
    ]

    # Weights: science fiction=22 (5 books), politics=14 (3 books), then a
    # 5-way tie at weight 5 (desert planets, space opera, fantasy, adventure,
    # dragons) broken by first-occurrence order, of which only the first 3
    # fit in the top 5.
    assert captured["subjects"] == [
        "science fiction",
        "politics",
        "desert planets",
        "space opera",
        "fantasy",
    ]
    assert captured["limit"] == recommend.RECOMMEND_LIMIT

    # All 10 tracked titles are excluded, not just the liked ones.
    expected_excluded = {title.lower() for title, _rating in REALISTIC_BOOKS}
    assert captured["exclude_titles"] == expected_excluded


def test_recommend_skips_book_whose_lookup_fails(monkeypatch):
    for i in range(books.RATING_THRESHOLD):
        add_rated(f"Book {i}", 5)

    def fake_resolve_title(title):
        if title == "Book 0":
            raise finna.FinnaLookupError("network down")
        return {
            "finna_id": title,
            "subjects": ["science fiction"],
            "community_rating": None,
            "fetched_at": "2026-01-01T00:00:00+00:00",
        }

    captured = {}

    def fake_search_by_subjects(subjects, exclude_titles, limit):
        captured["subjects"] = subjects
        return [{"title": "Recommended Book", "author": "Someone", "community_rating": None}]

    monkeypatch.setattr(finna, "resolve_title", fake_resolve_title)
    monkeypatch.setattr(finna, "search_by_subjects", fake_search_by_subjects)

    results = recommend.get_recommendations()
    assert results == [{"title": "Recommended Book", "author": "Someone", "community_rating": None}]
    assert captured["subjects"] == ["science fiction"]
