from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from app_cli import storage

logger = logging.getLogger(__name__)

API_BASE = "https://api.finna.fi/api/v1"
REQUEST_TIMEOUT = 10
MAX_LOCATIONS = 5


class FinnaLookupError(Exception):
    """Raised when a Finna API call fails (network error, bad response, etc.)."""


def _community_rating(record: dict) -> dict | None:
    rating = record.get("rating")
    if not rating or rating.get("count", 0) == 0:
        return None
    return {"count": rating["count"], "average": rating["average"]}


def _primary_authors(record: dict) -> list[str]:
    """Finna returns authors.primary as a dict (name -> role) when there are
    primary authors, but as an empty list when there are none — handle both.
    """
    primary = (record.get("authors") or {}).get("primary") or {}
    if isinstance(primary, dict):
        return list(primary.keys())
    return list(primary)


def _summarize_buildings(buildings: list[dict]) -> list[str]:
    """Finna's `buildings` field is a flat, depth-encoded hierarchy (depth
    prefix in `value`, e.g. "2/Helmet/h/h01l/"): depth 0 is the library
    network/consortium (not location-specific), depth 1 is the city, depth 2
    is the specific branch, and any deeper level seen so far is a
    shelf/collection code, not a place name. Keep city (1) and branch (2),
    drop the network name (0) and anything deeper (3+), capped to
    MAX_LOCATIONS entries.
    """
    names = []
    for entry in buildings or []:
        value = entry.get("value", "")
        depth_str = value.split("/", 1)[0]
        if not depth_str.isdigit():
            continue
        depth = int(depth_str)
        if depth in (1, 2):
            translated = entry.get("translated")
            if translated and translated not in names:
                names.append(translated)
    return names[:MAX_LOCATIONS]


def _format_year(record: dict) -> str | None:
    year = record.get("year")
    return str(year) if year else None


def _format_type(record: dict) -> str | None:
    formats = record.get("formats") or []
    if not formats:
        return None
    return formats[0].get("translated")


def resolve_title(title: str) -> dict | None:
    """Resolve a book title to Finna metadata (subjects, community rating), using
    and updating the local cache. Returns None if Finna has no match for the title.
    """
    cache_key = title.strip().lower()
    data = storage.load_data()
    cached = data["finna_cache"].get(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            f"{API_BASE}/search",
            params={
                "lookfor": title,
                "type": "Title",
                "field[]": ["id", "title", "subjects", "rating"],
                "limit": 1,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise FinnaLookupError(f"Finna lookup failed for '{title}': {exc}") from exc

    records = payload.get("records") or []
    if not records:
        return None

    record = records[0]
    subjects = sorted({heading for chain in record.get("subjects", []) for heading in chain})
    resolved = {
        "finna_id": record.get("id"),
        "subjects": subjects,
        "community_rating": _community_rating(record),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    data["finna_cache"][cache_key] = resolved
    storage.save_data(data)
    return resolved


def search_by_subjects(subjects: list[str], exclude_titles: set[str], limit: int) -> list[dict]:
    """Query Finna for candidate books matching any of the given subjects,
    excluding already-tracked titles. Returns a list of
    {title, author, community_rating} dicts, ranked by Finna's relevance order
    within each subject query.
    """
    candidates: dict[str, dict] = {}
    for subject in subjects:
        try:
            response = requests.get(
                f"{API_BASE}/search",
                params={
                    "filter[]": f'topic_facet:"{subject}"',
                    "field[]": ["id", "title", "authors", "rating"],
                    "limit": limit,
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Skipping subject '%s': Finna search failed: %s", subject, exc)
            continue

        for record in payload.get("records") or []:
            title = record.get("title", "")
            if title.strip().lower() in exclude_titles:
                continue
            if title in candidates:
                continue
            primary_authors = _primary_authors(record)
            candidates[title] = {
                "title": title,
                "author": primary_authors[0] if primary_authors else None,
                "community_rating": _community_rating(record),
            }

    ranked = sorted(
        candidates.values(),
        key=lambda c: (
            c["community_rating"]["average"] if c["community_rating"] else -1
        ),
        reverse=True,
    )
    return ranked[:limit]


def _search_records(lookfor: str, search_type: str, limit: int) -> list[dict]:
    """Shared query helper for search_by_title/search_by_author. Returns
    Finna's raw record dicts, or [] if the query matched nothing. Unlike
    search_by_subjects (which loops over multiple subject queries and skips
    a failing one to preserve partial results), this makes a single request,
    so there's nothing to salvage on failure — raises FinnaLookupError
    instead, which callers must handle (see book_search_title/author in
    cli.py).
    """
    try:
        response = requests.get(
            f"{API_BASE}/search",
            params={
                "lookfor": lookfor,
                "type": search_type,
                "field[]": ["id", "title", "authors", "year", "formats", "rating", "buildings"],
                "limit": limit,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise FinnaLookupError(f"Finna search failed for '{lookfor}': {exc}") from exc

    return payload.get("records") or []


def _record_to_result(record: dict) -> dict:
    primary_authors = _primary_authors(record)
    return {
        "title": record.get("title", ""),
        "author": primary_authors[0] if primary_authors else None,
        "year": _format_year(record),
        "format": _format_type(record),
        "community_rating": _community_rating(record),
        "locations": _summarize_buildings(record.get("buildings", [])),
    }


def search_by_title(title: str, limit: int) -> list[dict]:
    """Search Finna for books matching a title. Title search is often
    ambiguous (many unrelated books share a title), so this returns every
    matching candidate rather than a single best guess — unlike
    resolve_title(), which is a cached, single-result lookup for internal
    recommendation use only.
    """
    records = _search_records(title, "Title", limit)
    return [_record_to_result(r) for r in records]


def search_by_author(author: str, limit: int) -> list[dict]:
    """Search Finna for books by a given author."""
    records = _search_records(author, "Author", limit)
    return [_record_to_result(r) for r in records]
