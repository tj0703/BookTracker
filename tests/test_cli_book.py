from datetime import date

from click.testing import CliRunner

from app_cli import books, finna
from app_cli.cli import main


def test_book_add_and_list():
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "book",
            "add",
            "--title",
            "Dune",
            "--completed",
            "2026-01-01",
            "--review",
            "Loved it.",
            "--review-date",
            "2026-01-02",
            "--rating",
            "5",
        ],
    )
    assert result.exit_code == 0
    assert "Added 'Dune'." in result.output
    assert "Rated books: 1/10" in result.output

    result = runner.invoke(main, ["book", "list"])
    assert result.exit_code == 0
    assert "Dune" in result.output
    assert "rating: 5/5" in result.output


def test_book_add_accepts_alternate_unambiguous_date_formats():
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "book",
            "add",
            "--title",
            "Dune",
            "--completed",
            "26/07/2026",
            "--review",
            "Loved it.",
            "--review-date",
            "2026/07/27",
        ],
    )
    assert result.exit_code == 0

    result = runner.invoke(main, ["book", "list"])
    assert "completed 2026-07-26" in result.output


def test_book_add_rejects_ambiguous_two_digit_year_date():
    # "26/07/06" could mean DD/MM/YY (26 Jul 2006) or YY/MM/DD (6 Jul 2026) —
    # ambiguous, so it must be rejected rather than silently guessed at.
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "book",
            "add",
            "--title",
            "Dune",
            "--completed",
            "26/07/06",
            "--review",
            "Loved it.",
            "--review-date",
            "2026-01-02",
        ],
    )
    assert result.exit_code != 0
    assert "does not match the formats" in result.output


def test_book_add_rejects_bad_rating():
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "book",
            "add",
            "--title",
            "Dune",
            "--completed",
            "2026-01-01",
            "--review",
            "Loved it.",
            "--review-date",
            "2026-01-02",
            "--rating",
            "9",
        ],
    )
    assert result.exit_code != 0


def test_book_recommend_reports_gate_progress():
    runner = CliRunner()
    result = runner.invoke(main, ["book", "recommend"])
    assert result.exit_code == 0
    assert "Rated books: 0/10" in result.output


def test_book_recommend_shows_candidates(monkeypatch):
    for i in range(books.RATING_THRESHOLD):
        books.add_book(
            books.BookEntry(
                title=f"Book {i}",
                date_completed=date(2026, 1, 1),
                review="Loved it.",
                review_date=date(2026, 1, 2),
                rating=5,
            )
        )

    monkeypatch.setattr(
        finna,
        "resolve_title",
        lambda title: {
            "finna_id": "1",
            "subjects": ["science fiction"],
            "community_rating": None,
            "fetched_at": "2026-01-01T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        finna,
        "search_by_subjects",
        lambda subjects, exclude_titles, limit: [
            {
                "title": "New Book",
                "author": "Some Author",
                "community_rating": {"count": 4, "average": 88},
            }
        ],
    )

    runner = CliRunner()
    result = runner.invoke(main, ["book", "recommend"])
    assert result.exit_code == 0
    assert "New Book - Some Author" in result.output
    assert "88/100 (4 rating(s))" in result.output
