from __future__ import annotations

import logging
from collections import defaultdict

from app_cli import books, finna

RECOMMEND_LIMIT = 5

logger = logging.getLogger(__name__)


class NotEnoughDataError(Exception):
    def __init__(self, rated: int, threshold: int):
        self.rated = rated
        self.threshold = threshold
        super().__init__(f"Only {rated}/{threshold} rated books - recommendations locked.")


def get_recommendations() -> list[dict]:
    rated = books.rated_count()
    if rated < books.RATING_THRESHOLD:
        raise NotEnoughDataError(rated, books.RATING_THRESHOLD)

    liked = books.liked_books()
    subject_weight: dict[str, int] = defaultdict(int)
    for book in liked:
        try:
            resolved = finna.resolve_title(book.title)
        except finna.FinnaLookupError:
            logger.warning("Skipping '%s': Finna lookup failed.", book.title)
            continue
        if resolved is None:
            continue
        for subject in resolved["subjects"]:
            subject_weight[subject] += book.rating

    if not subject_weight:
        return []

    top_subjects = [
        subject
        for subject, _ in sorted(subject_weight.items(), key=lambda kv: kv[1], reverse=True)[:5]
    ]

    return finna.search_by_subjects(
        top_subjects, books.tracked_titles(), RECOMMEND_LIMIT
    )
