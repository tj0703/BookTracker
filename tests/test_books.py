from datetime import date

from app_cli import books


def make_entry(title, rating=None):
    return books.BookEntry(
        title=title,
        date_completed=date(2026, 1, 1),
        review="Great read.",
        review_date=date(2026, 1, 2),
        rating=rating,
    )


def test_add_and_list_book():
    books.add_book(make_entry("Dune"))
    entries = books.list_books()
    assert len(entries) == 1
    assert entries[0].title == "Dune"
    assert entries[0].rating is None


def test_rated_count_ignores_unrated():
    books.add_book(make_entry("Dune", rating=5))
    books.add_book(make_entry("Foundation"))
    assert books.rated_count() == 1


def test_liked_books_filters_by_min_rating():
    books.add_book(make_entry("Dune", rating=5))
    books.add_book(make_entry("Foundation", rating=3))
    books.add_book(make_entry("Neuromancer", rating=4))
    liked = {b.title for b in books.liked_books()}
    assert liked == {"Dune", "Neuromancer"}


def test_tracked_titles_case_insensitive():
    books.add_book(make_entry("Dune"))
    assert "dune" in books.tracked_titles()
