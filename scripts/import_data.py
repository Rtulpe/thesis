from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from core.database import initialize_database


YELP_FILE_ALIASES = {
    "business": ("business.json", "yelp_academic_dataset_business.json"),
    "user": ("user.json", "yelp_academic_dataset_user.json"),
    "review": ("review.json", "yelp_academic_dataset_review.json"),
}


def resolve_yelp_files(raw_directory: str | Path) -> dict[str, Path]:
    raw_path = Path(raw_directory)
    resolved: dict[str, Path] = {}
    missing: list[str] = []
    for kind, aliases in YELP_FILE_ALIASES.items():
        for alias in aliases:
            candidate = raw_path / alias
            if candidate.exists():
                resolved[kind] = candidate
                break
        else:
            missing.append(f"{kind} ({' or '.join(aliases)})")
    if missing:
        raise FileNotFoundError(
            f"Missing Yelp files in {raw_path}: {', '.join(missing)}"
        )
    return resolved


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


def import_yelp(
    raw_directory: str | Path,
    database_path: str | Path,
    *,
    cities: set[str] | None = None,
    categories: set[str] | None = None,
    max_businesses: int | None = None,
    max_reviews_per_business: int | None = None,
    enrich_user_metadata: bool = False,
    progress_every: int = 100_000,
    batch_size: int = 1000,
) -> dict[str, int]:
    files = resolve_yelp_files(raw_directory)
    if not cities:
        raise ValueError("cities must contain at least one target city")
    if max_businesses is not None and max_businesses <= 0:
        raise ValueError("max_businesses must be greater than zero")
    if max_reviews_per_business is not None and max_reviews_per_business <= 0:
        raise ValueError("max_reviews_per_business must be greater than zero")
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    if progress_every <= 0:
        raise ValueError("progress_every must be greater than zero")
    initialize_database(database_path)
    counts = {
        "businesses": 0,
        "users": 0,
        "reviews": 0,
        "filtered_businesses": 0,
        "filtered_reviews": 0,
        "skipped": 0,
    }
    selected_businesses: set[str] = set()
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        business_batch: list[tuple[Any, ...]] = []
        for record in _read_json_lines(files["business"]):
            business_id = record.get("business_id")
            name = record.get("name")
            city = record.get("city")
            if not all(isinstance(value, str) and value.strip() for value in (business_id, name, city)):
                counts["skipped"] += 1
                continue
            if city.strip().casefold() not in {item.casefold() for item in cities}:
                counts["filtered_businesses"] += 1
                continue
            record_categories = {
                item.strip().casefold()
                for item in (record.get("categories") or "").split(",")
                if item.strip()
            }
            if categories and not record_categories.intersection(
                {item.casefold() for item in categories}
            ):
                counts["filtered_businesses"] += 1
                continue
            if max_businesses is not None and len(selected_businesses) >= max_businesses:
                counts["filtered_businesses"] += 1
                continue
            try:
                latitude = float(record.get("latitude", 0.0))
                longitude = float(record.get("longitude", 0.0))
                rating = float(record.get("stars", 0.0))
            except (TypeError, ValueError):
                counts["skipped"] += 1
                continue
            business_batch.append((
                business_id,
                name.strip(),
                city.strip(),
                latitude,
                longitude,
                record.get("categories") or "",
                rating,
                _opening_hours(record),
            ))
            selected_businesses.add(business_id)
            if len(business_batch) < batch_size:
                continue
            connection.executemany(
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
                business_batch,
            )
            counts["businesses"] += len(business_batch)
            business_batch.clear()
        if business_batch:
            connection.executemany(
                """
                INSERT INTO venues (
                    venue_id, name, city, latitude, longitude, categories,
                    avg_rating, opening_hours_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(venue_id) DO UPDATE SET
                    name = excluded.name, city = excluded.city,
                    latitude = excluded.latitude, longitude = excluded.longitude,
                    categories = excluded.categories, avg_rating = excluded.avg_rating,
                    opening_hours_json = excluded.opening_hours_json
                """,
                business_batch,
            )
            counts["businesses"] += len(business_batch)
        if not selected_businesses:
            return counts

        imported_users: set[str] = set()
        user_batch: list[tuple[str, None, int]] = []
        interaction_batch: list[tuple[Any, ...]] = []
        review_counts: dict[str, int] = {}
        review_records_scanned = 0
        review_scan_started = time.monotonic()
        for record in _read_json_lines(files["review"]):
            review_records_scanned += 1
            if review_records_scanned % progress_every == 0:
                elapsed = max(time.monotonic() - review_scan_started, 0.001)
                print(
                    (
                        f"import: reviews scanned={review_records_scanned:,} "
                        f"selected={sum(review_counts.values()):,} "
                        f"rate={review_records_scanned / elapsed:,.0f}/s"
                    ),
                    file=sys.stderr,
                    flush=True,
                )
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
            if venue_id not in selected_businesses:
                counts["filtered_reviews"] += 1
                continue
            if (
                max_reviews_per_business is not None
                and review_counts.get(venue_id, 0) >= max_reviews_per_business
            ):
                counts["filtered_reviews"] += 1
                continue
            try:
                rating = float(record.get("stars"))
            except (TypeError, ValueError):
                counts["skipped"] += 1
                continue
            if user_id not in imported_users:
                user_batch.append((user_id, None, 0))
                imported_users.add(user_id)
            interaction_batch.append(
                (
                    user_id,
                    venue_id,
                    rating,
                    text.strip(),
                    _timestamp(record.get("date")),
                    user_id,
                    venue_id,
                    text.strip(),
                )
            )
            if len(user_batch) >= batch_size:
                connection.executemany(
                    """
                    INSERT INTO users (user_id, name, review_count)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO NOTHING
                    """,
                    user_batch,
                )
                counts["users"] += len(user_batch)
                user_batch.clear()
            if len(interaction_batch) >= batch_size:
                if user_batch:
                    connection.executemany(
                        """
                        INSERT INTO users (user_id, name, review_count)
                        VALUES (?, ?, ?)
                        ON CONFLICT(user_id) DO NOTHING
                        """,
                        user_batch,
                    )
                    counts["users"] += len(user_batch)
                    user_batch.clear()
                connection.executemany(
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
                    interaction_batch,
                )
                counts["reviews"] += len(interaction_batch)
                interaction_batch.clear()
            review_counts[venue_id] = review_counts.get(venue_id, 0) + 1
        if user_batch:
            connection.executemany(
                """
                INSERT INTO users (user_id, name, review_count)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO NOTHING
                """,
                user_batch,
            )
            counts["users"] += len(user_batch)
        if interaction_batch:
            connection.executemany(
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
                interaction_batch,
            )
            counts["reviews"] += len(interaction_batch)
        if enrich_user_metadata and imported_users:
            for record in _read_json_lines(files["user"]):
                user_id = record.get("user_id")
                if user_id not in imported_users:
                    continue
                try:
                    review_count = int(record.get("review_count", 0))
                except (TypeError, ValueError):
                    counts["skipped"] += 1
                    continue
                connection.execute(
                    """
                    UPDATE users SET name = ?, review_count = ?
                    WHERE user_id = ?
                    """,
                    (record.get("name"), review_count, user_id),
                )
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
    parser.add_argument("--cities", required=True, help="Comma-separated target cities")
    parser.add_argument("--categories", default=None, help="Comma-separated categories")
    parser.add_argument("--max-businesses", type=int, default=None)
    parser.add_argument("--max-reviews-per-business", type=int, default=None)
    parser.add_argument(
        "--progress-every",
        type=int,
        default=100_000,
        help="Print review-scan progress to stderr every N records",
    )
    parser.add_argument(
        "--enrich-user-metadata",
        action="store_true",
        help="Scan the multi-GB Yelp user file for names and source review counts",
    )
    args = parser.parse_args()
    cities = {city.strip() for city in args.cities.split(",") if city.strip()}
    categories = (
        {category.strip() for category in args.categories.split(",") if category.strip()}
        if args.categories
        else None
    )
    print(json.dumps(
        import_yelp(
            args.input,
            args.database,
            cities=cities,
            categories=categories,
            max_businesses=args.max_businesses,
            max_reviews_per_business=args.max_reviews_per_business,
            enrich_user_metadata=args.enrich_user_metadata,
            progress_every=args.progress_every,
        ),
        indent=2,
    ))


if __name__ == "__main__":
    main()
