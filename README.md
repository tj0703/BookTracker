# BookTracker

A Python CLI application for tracking books you've read and getting
recommendations, powered by the [Finna](https://www.finna.fi/) library API.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Commands

### `app-cli hello [NAME]`

Print a greeting. `NAME` defaults to `world`.

```bash
app-cli hello
# Hello, world!

app-cli hello Tanvi
# Hello, Tanvi!
```

### `app-cli book add`

Record a book you've finished reading.

| Option | Required | Description |
|---|---|---|
| `--title` | yes | Book title. |
| `--completed` | yes | Date reading was completed. Accepts `YYYY-MM-DD`, `DD/MM/YYYY`, or `YYYY/MM/DD`. |
| `--review` | yes | Your review of the book. |
| `--review-date` | yes | Date the review was written. Same accepted formats as `--completed`. |
| `--rating` | no | Your personal rating, `1`-`5`. |

```bash
app-cli book add --title "Dune" --completed 2026-01-01 --review "Loved it." --review-date 2026-01-02 --rating 5

app-cli book add --title "Foundation" --completed 26/07/2026 --review "Solid, but slow start." --review-date 27/07/2026 --rating 4
```

Note: 2-digit-year dates (e.g. `26/07/06`) are rejected rather than
guessed at, since they're ambiguous between `DD/MM/YY` and `YY/MM/DD` —
use a 4-digit year instead.

### `app-cli book list`

List all tracked books with their completion date and rating.

```bash
app-cli book list
# Dune - completed 2026-01-01, rating: 5/5
# Foundation - completed 2026-07-26, rating: 4/5
```

### `app-cli book recommend`

Suggest books based on the subjects of your highly-rated (4-5) tracked
books, via the Finna API. Requires at least 10 rated books; until then it
reports your progress toward that threshold.

```bash
app-cli book recommend
# Rated books: 2/10 - recommendations unlock at 10.

# ... after 10 rated books:
app-cli book recommend
# Some Book - Some Author | Finna rating: 88/100 (4 rating(s))
```

### `app-cli book search title <TITLE>`

Search Finna's catalog by title. Title search is often ambiguous (many
unrelated books share a title), so every matching candidate is shown, not
just one guess. Each result includes year, format, Finna's community
rating, and — when known — which library/branch in Finland holds it.

| Option | Required | Description |
|---|---|---|
| `--limit` | no | Max results to show. Default `10`. |

```bash
app-cli book search title "Foundation" --limit 2
# Foundation / Foundation and empire ; Second foundation - Asimov, Isaac | 2010 | Kirja | Finna rating: no rating available | Available: Kristiinankaupunki, Kristiinankaupungin kirjasto
# Foundation ; Foundation and empire ; Second foundation - Asimov, Isaac | 2010 | Kirja | Finna rating: 80/100 (2 rating(s)) | Available: Hanko, Hangon kaupunginkirjasto
```

### `app-cli book search author <AUTHOR>`

List books by a given author, in the same format as `book search title`.

| Option | Required | Description |
|---|---|---|
| `--limit` | no | Max results to show. Default `10`. |

```bash
app-cli book search author "Isaac Asimov" --limit 2
# Konec vecnosti : Roman - Asimov, Isaac | 2000 | Kirja | Finna rating: no rating available | Available: Kesälahti, Kiteen kirjasto
# Sami bogi ; Kamesek v nebe ; Zvjozdy kak pyl ; Kosmitseskije tetsenija - Asimov, Isaac | 1999 | Kirja | Finna rating: no rating available | Available: Helsinki, Rikhardinkatu
```

Note: results are shown as Finna returns them, including Finnish-language
titles/subjects — no translation layer is applied. The `Available:` field
is omitted entirely when Finna has no location data for a record (e.g.
online-only resources).

## Development

```bash
pytest
```

Run the live-network Finna smoke tests (excluded by default):

```bash
pytest -m e2e_live
```

Run the fresh-install packaging check:

```bash
python tests/e2e/check_fresh_install.py
```
