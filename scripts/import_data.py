from __future__ import annotations

import argparse
import json
import random
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from core.database import initialize_database


YELP_FILES = ("business.json", "user.json", "review.json")


def _read_json_lines(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from error
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: record must be an object")
            yield record


def _opening_hours(record: dict[str, Any]) -> str:
    hours = record.get("hours")
    if not isinstance(hours, dict):
        return "{}"
    normalized: dict[str, list[str]] = {}
    for day, value in hours.items():
        if not isinstance(value, str) or "-" not in value:
            continue
        opening, closing = (part.strip() for part in value.split("-", 1))
        normalized[day[:3].lower()] = [opening, closing]
    return json.dumps(normalized, sort_keys=True)


def _timestamp(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value
    return datetime.now(timezone.utc).isoformat()


def import_yelp(raw_directory: str | Path, database_path: str | Path) -> dict[str, int]:
    raw_path = Path(raw_directory)
    missing = [name for name in YELP_FILES if not (raw_path / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing Yelp files in {raw_path}: {', '.join(missing)}"
        )
    initialize_database(database_path)
    counts = {"businesses": 0, "users": 0, "reviews": 0, "skipped": 0}
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for record in _read_json_lines(raw_path / "business.json"):
            business_id = record.get("business_id")
            name = record.get("name")
            city = record.get("city")
            if not all(isinstance(value, str) and value.strip() for value in (business_id, name, city)):
                counts["skipped"] += 1
                continue
            try:
                latitude = float(record.get("latitude", 0.0))
                longitude = float(record.get("longitude", 0.0))
                rating = float(record.get("stars", 0.0))
            except (TypeError, ValueError):
                counts["skipped"] += 1
                continue
            connection.execute(
                """
                INSERT INTO venues (
                    venue_id, name, city, latitude, longitude, categories,
                    avg_rating, opening_hours_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(venue_id) DO UPDATE SET
                    name = excluded.name,
                    city = excluded.city,
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    categories = excluded.categories,
                    avg_rating = excluded.avg_rating,
                    opening_hours_json = excluded.opening_hours_json
                """,
                (
                    business_id,
                    name.strip(),
                    city.strip(),
                    latitude,
                    longitude,
                    record.get("categories") or "",
                    rating,
                    _opening_hours(record),
                ),
            )
            counts["businesses"] += 1
        for record in _read_json_lines(raw_path / "user.json"):
            user_id = record.get("user_id")
            if not isinstance(user_id, str) or not user_id.strip():
                counts["skipped"] += 1
                continue
            try:
                review_count = int(record.get("review_count", 0))
            except (TypeError, ValueError):
                counts["skipped"] += 1
                continue
            connection.execute(
                """
                INSERT INTO users (user_id, name, review_count)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    name = excluded.name,
                    review_count = excluded.review_count
                """,
                (user_id, record.get("name"), review_count),
            )
            counts["users"] += 1
        for record in _read_json_lines(raw_path / "review.json"):
            review_id = record.get("review_id")
            user_id = record.get("user_id")
            venue_id = record.get("business_id")
            text = record.get("text")
            if not all(
                isinstance(value, str) and value.strip()
                for value in (review_id, user_id, venue_id, text)
            ):
                counts["skipped"] += 1
                continue
            try:
                rating = float(record.get("stars"))
            except (TypeError, ValueError):
                counts["skipped"] += 1
                continue
            exists = connection.execute(
                "SELECT 1 FROM users WHERE user_id = ? AND EXISTS "
                "(SELECT 1 FROM venues WHERE venue_id = ?)",
                (user_id, venue_id),
            ).fetchone()
            if exists is None:
                counts["skipped"] += 1
                continue
            connection.execute(
                """
                INSERT INTO interactions (
                    user_id, venue_id, rating, review_text, created_at
                )
                SELECT ?, ?, ?, ?, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM interactions
                    WHERE user_id = ? AND venue_id = ? AND review_text = ?
                )
                """,
                (
                    user_id,
                    venue_id,
                    rating,
                    text.strip(),
                    _timestamp(record.get("date")),
                    user_id,
                    venue_id,
                    text.strip(),
                ),
            )
            counts["reviews"] += 1
        connection.execute(
            """
            UPDATE users
            SET review_count = (
                SELECT COUNT(*) FROM interactions
                WHERE interactions.user_id = users.user_id
            )
            """
        )
    return counts


def split_mbti_users(
    records: Iterable[dict[str, Any]],
    *,
    test_fraction: float = 0.2,
    seed: int = 42,
) -> dict[str, list[dict[str, Any]]]:
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between zero and one")
    grouped: dict[str, dict[str, Any]] = {}
    for record in records:
        user_id = record.get("user_id")
        if isinstance(user_id, str) and user_id.strip():
            grouped[user_id] = record
    users = list(grouped.values())
    random.Random(seed).shuffle(users)
    test_size = round(len(users) * test_fraction)
    return {"train": users[test_size:], "test": users[:test_size]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Yelp Open Dataset JSONL files")
    parser.add_argument("--input", type=Path, default=Path("data/raw/yelp"))
    parser.add_argument("--database", type=Path, default=Path("data/user_state.db"))
    args = parser.parse_args()
    print(json.dumps(import_yelp(args.input, args.database), indent=2))


if __name__ == "__main__":
    main()
