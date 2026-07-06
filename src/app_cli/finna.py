from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from app_cli import storage

logger = logging.getLogger(__name__)

API_BASE = "https://api.finna.fi/api/v1"
REQUEST_TIMEOUT = 10


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
