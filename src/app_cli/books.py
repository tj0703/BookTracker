from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date

from app_cli import storage

RATING_THRESHOLD = 10
LIKED_RATING_MIN = 4


@dataclass
class BookEntry:
    title: str
    date_completed: date
    review: str
    review_date: date
    rating: int | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date_completed"] = self.date_completed.isoformat()
        d["review_date"] = self.review_date.isoformat()
        return d

    @staticmethod
    def from_dict(d: dict) -> "BookEntry":
        return BookEntry(
            title=d["title"],
            date_completed=date.fromisoformat(d["date_completed"]),
            review=d["review"],
            review_date=date.fromisoformat(d["review_date"]),
            rating=d.get("rating"),
        )


def add_book(entry: BookEntry) -> None:
    data = storage.load_data()
    data["books"].append(entry.to_dict())
    storage.save_data(data)


def list_books() -> list[BookEntry]:
    data = storage.load_data()
    return [BookEntry.from_dict(d) for d in data["books"]]


def rated_count() -> int:
    return sum(1 for b in list_books() if b.rating is not None)


def liked_books() -> list[BookEntry]:
    return [b for b in list_books() if b.rating is not None and b.rating >= LIKED_RATING_MIN]


def tracked_titles() -> set[str]:
    return {b.title.strip().lower() for b in list_books()}
