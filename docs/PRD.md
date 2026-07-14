# PRD: BookTracker CLI

## Summary

BookTracker is a local, single-user Python CLI for logging books you've
read (with review + rating), and for discovering what to read next based
on what you've rated highly. Recommendations and catalog search are
powered by the [Finna](https://www.finna.fi/) API, Finland's national
library discovery service.

## Problem

Readers who finish a lot of books lose track of what they read, what they
thought of it, and struggle to find a next book that matches their taste
rather than generic bestseller lists. Existing tools (Goodreads, etc.) are
cloud-hosted, account-gated, and not scriptable. There's no lightweight,
local, script-friendly way to log reading history and get taste-based
recommendations sourced from a real library catalog.

## Goals

- Let a user record books they've finished, with a review and optional
  rating, in a few seconds from the terminal.
- Surface personalized recommendations once there's enough rating data to
  make them meaningful, rather than guessing from sparse data.
- Let users search a real library catalog (Finna) by title or author,
  including which physical branch holds a copy.
- Keep everything local: no account, no server, no telemetry.

## Non-goals

- Not a general-purpose library/catalog browser — Finna coverage (esp.
  non-Finnish libraries) is out of BookTracker's control.
- Not multi-user or networked — single local JSON file, one reader.
- Not a recommendation engine beyond subject-overlap matching; no ML
  ranking, collaborative filtering, or cross-user signal.
- No GUI/web UI — CLI only.
- No editing or deleting existing entries (see Open Questions).

## Target user

A single developer/reader comfortable with a terminal, who wants their
reading log as a plain local file (scriptable, greppable, backed up
however they like) rather than locked in a web account.

## User stories

1. As a reader, I finish a book and log it with my review and rating in
   one command, so I don't forget my reaction later.
2. As a reader, I list my tracked books to recall what I've read and how
   I rated it.
3. As a reader, once I've rated enough books, I ask for recommendations
   and get titles related to the subjects of books I loved.
4. As a reader, I search a title or author to check if a library near me
   (in Finland) holds a copy before I buy it.

## Features (current, shipped)

### `app-cli book add`
Records a finished book: `--title`, `--completed` (date), `--review`,
`--review-date`, `--rating` (1-5, optional). Dates accept `YYYY-MM-DD`,
`DD/MM/YYYY`, or `YYYY/MM/DD`; 2-digit years are rejected as ambiguous
rather than guessed. Immediately reports rated-book progress toward the
recommendation unlock threshold.

### `app-cli book list`
Lists all tracked books with completion date and rating (or `unrated`).

### `app-cli book recommend`
Suggests up to 5 books based on the Finna subjects of the user's
highly-rated (4-5) tracked books, weighted by rating. Requires at least
**10 rated books**; below that it reports progress (`N/10`) instead of
guessing from thin data. Already-tracked titles are excluded from
suggestions.

### `app-cli book search title <TITLE>` / `book search author <AUTHOR>`
Searches Finna's catalog directly (no local data required). Returns every
matching candidate — title search is often ambiguous — with year, format,
Finna community rating, and, when known, which Finnish library
branch(es) hold a copy. `--limit` caps result count (default 10).

### Cross-cutting
- Local JSON storage (`books.json` in the OS app-data dir, overridable via
  `APP_CLI_DATA_DIR`) — no server, no account.
- UTF-8-safe output for non-Latin titles/authors regardless of terminal
  codepage.
- Finna errors are caught and reported as a clean CLI message, never a
  raw traceback.

## Success metrics

Since this is a personal/local tool, "success" is qualitative rather than
analytics-driven (no telemetry is collected, by design):
- Logging a book takes one command, no more than the 4 required fields.
- Recommendation quality feels relevant once the 10-rated-book threshold
  is hit (subjectively judged by the user, not measured).
- Zero crashes/tracebacks surfaced to the user for expected error paths
  (bad dates, Finna downtime, no matches).

## Technical constraints & decisions

- **Storage**: single local JSON file, read-modify-write per command. Not
  designed for concurrent access — fine for a single-user local CLI.
- **Recommendation gate**: fixed threshold of 10 rated books
  (`RATING_THRESHOLD`), "liked" defined as rating >= 4
  (`LIKED_RATING_MIN`). Chosen to avoid noisy recommendations from 1-2
  data points.
- **Data source**: Finna API only — catalog coverage and community
  ratings are whatever Finna returns; no cross-referencing with other
  sources (Goodreads, OpenLibrary, etc.).
- **Date parsing**: only unambiguous formats accepted; a 2-digit year
  is rejected rather than guessed, since `DD/MM/YY` vs `YY/MM/DD` cannot
  be disambiguated safely.

## Open questions / candidate future work

- **Edit/delete entries**: currently there's no way to correct or remove
  a logged book short of hand-editing `books.json`. Worth a
  `book edit`/`book remove` command if this becomes a real pain point.
- **Re-rating**: no command to update a rating after the fact (e.g. after
  reflecting further) without re-adding.
- **Export**: no `book export` (CSV/Goodreads-import format) — ties into
  "no vendor lock-in" but currently the user must read raw JSON.
- **Non-Finnish catalogs**: Finna is Finland-specific; recommendations
  and location data have no meaning for users elsewhere. Out of scope
  unless a second provider is added later.
- **Recommendation tuning**: threshold (10) and liked-rating floor (4)
  are fixed constants, not configurable. Revisit if real usage shows
  they're wrong for typical reading volume.
