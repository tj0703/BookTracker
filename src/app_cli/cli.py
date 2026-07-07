import sys

import click

from app_cli import __version__
from app_cli import books
from app_cli import finna
from app_cli import recommend

# Finna's catalog includes non-Latin titles/authors (Cyrillic, CJK, etc.).
# The default console encoding on Windows (e.g. cp1252) can't represent
# those and raises UnicodeEncodeError on print. Force UTF-8 with a
# replacement fallback so the CLI never crashes on output, regardless of
# the terminal's codepage.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


@click.group()
@click.version_option(__version__)
def main():
    """app-cli: a Python command-line application."""


@main.command()
@click.argument("name", default="world")
def hello(name):
    """Print a greeting."""
    click.echo(f"Hello, {name}!")


@main.group()
def book():
    """Track books you've read and get recommendations."""


# Only unambiguous formats (4-digit year) are accepted. 2-digit-year inputs
# like "26/07/06" are genuinely ambiguous (DD/MM/YY vs YY/MM/DD) and a wrong
# guess would silently store the wrong date, so they're rejected rather than
# guessed at.
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]
DATE_FORMATS_HELP = "YYYY-MM-DD, DD/MM/YYYY, or YYYY/MM/DD"


@book.command("add")
@click.option("--title", required=True, help="Book title.")
@click.option(
    "--completed",
    "date_completed",
    required=True,
    type=click.DateTime(formats=DATE_FORMATS),
    help=f"Date reading was completed ({DATE_FORMATS_HELP}).",
)
@click.option("--review", required=True, help="Your review of the book.")
@click.option(
    "--review-date",
    "review_date",
    required=True,
    type=click.DateTime(formats=DATE_FORMATS),
    help=f"Date the review was written ({DATE_FORMATS_HELP}).",
)
@click.option(
    "--rating",
    type=click.IntRange(1, 5),
    default=None,
    help="Your personal rating, 1-5 (optional).",
)
def book_add(title, date_completed, review, review_date, rating):
    """Add a book entry."""
    entry = books.BookEntry(
        title=title,
        date_completed=date_completed.date(),
        review=review,
        review_date=review_date.date(),
        rating=rating,
    )
    books.add_book(entry)
    click.echo(f"Added '{title}'.")

    rated = books.rated_count()
    if rated < books.RATING_THRESHOLD:
        click.echo(
            f"Rated books: {rated}/{books.RATING_THRESHOLD} - "
            "recommendations unlock at "
            f"{books.RATING_THRESHOLD}."
        )


@book.command("list")
def book_list():
    """List tracked books."""
    entries = books.list_books()
    if not entries:
        click.echo("No books tracked yet.")
        return
    for entry in entries:
        rating_str = f"{entry.rating}/5" if entry.rating is not None else "unrated"
        click.echo(
            f"{entry.title} - completed {entry.date_completed.isoformat()}, "
            f"rating: {rating_str}"
        )


@book.command("recommend")
def book_recommend():
    """Suggest books based on your highly-rated tracked books."""
    try:
        candidates = recommend.get_recommendations()
    except recommend.NotEnoughDataError as exc:
        click.echo(
            f"Rated books: {exc.rated}/{exc.threshold} - "
            "recommendations unlock at "
            f"{exc.threshold}."
        )
        return
    except finna.FinnaLookupError as exc:
        click.echo(f"Could not fetch recommendations: {exc}", err=True)
        return

    if not candidates:
        click.echo("No recommendations found yet - try tracking more rated books.")
        return

    for candidate in candidates:
        author = candidate["author"] or "Unknown author"
        community = candidate["community_rating"]
        community_str = (
            f"{community['average']}/100 ({community['count']} rating(s))"
            if community
            else "no rating available"
        )
        click.echo(
            f"{candidate['title']} - {author} | Finna rating: {community_str}"
        )


DEFAULT_SEARCH_LIMIT = 10


def _format_search_result(result: dict) -> str:
    author = result["author"] or "Unknown author"
    parts = [f"{result['title']} - {author}"]
    if result["year"]:
        parts.append(result["year"])
    if result["format"]:
        parts.append(result["format"])

    community = result["community_rating"]
    community_str = (
        f"{community['average']}/100 ({community['count']} rating(s))"
        if community
        else "no rating available"
    )
    parts.append(f"Finna rating: {community_str}")

    line = " | ".join(parts)
    if result["locations"]:
        line += f" | Available: {', '.join(result['locations'])}"
    return line


@book.group("search")
def book_search():
    """Search Finna's catalog by title or author."""


@book_search.command("title")
@click.argument("title")
@click.option("--limit", type=int, default=DEFAULT_SEARCH_LIMIT, help="Max results to show.")
def book_search_title(title, limit):
    """Search for books by title."""
    try:
        results = finna.search_by_title(title, limit)
    except finna.FinnaLookupError as exc:
        click.echo(f"Could not search Finna: {exc}", err=True)
        return

    if not results:
        click.echo(f"No matches found for '{title}'.")
        return

    for result in results:
        click.echo(_format_search_result(result))


@book_search.command("author")
@click.argument("author")
@click.option("--limit", type=int, default=DEFAULT_SEARCH_LIMIT, help="Max results to show.")
def book_search_author(author, limit):
    """List books by an author."""
    try:
        results = finna.search_by_author(author, limit)
    except finna.FinnaLookupError as exc:
        click.echo(f"Could not search Finna: {exc}", err=True)
        return

    if not results:
        click.echo(f"No matches found for '{author}'.")
        return

    for result in results:
        click.echo(_format_search_result(result))


if __name__ == "__main__":
    main()
