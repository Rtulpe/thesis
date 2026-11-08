from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import ToolRegistry, create_registry

DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "user_state.db"


def _connect() -> sqlite3.Connection:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database does not exist: {DATABASE_PATH}")
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_user_profile(user_id: str) -> dict[str, Any]:
    if not user_id or not user_id.strip():
        raise ValueError("user_id must not be empty")
    with _connect() as connection:
        row = connection.execute(
            "SELECT user_id, name, review_count, created_at FROM users "
            "WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Unknown user: {user_id}")
        interaction_count = connection.execute(
            "SELECT COUNT(*) FROM interactions WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
    profile = dict(row)
    profile["interaction_count"] = interaction_count
    return profile


def get_user_history(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    if limit <= 0:
        raise ValueError("limit must be greater than zero")
    get_user_profile(user_id)
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT interactions.interaction_id, interactions.user_id,
                   interactions.venue_id, interactions.rating,
                   interactions.review_text, interactions.created_at,
                   venues.name AS venue_name, venues.city,
                   venues.categories, venues.avg_rating
            FROM interactions
            JOIN venues ON venues.venue_id = interactions.venue_id
            WHERE interactions.user_id = ?
            ORDER BY interactions.created_at DESC, interactions.interaction_id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def record_interaction(
    user_id: str,
    venue_id: str,
    rating: float,
    review_text: str,
) -> bool:
    if not user_id or not user_id.strip():
        raise ValueError("user_id must not be empty")
    if not venue_id or not venue_id.strip():
        raise ValueError("venue_id must not be empty")
    if not 0.0 <= rating <= 5.0:
        raise ValueError("rating must be between 0 and 5")
    if not isinstance(review_text, str) or not review_text.strip():
        raise ValueError("review_text must not be empty")
    timestamp = datetime.now(timezone.utc).isoformat()
    with _connect() as connection:
        try:
            connection.execute(
                """
                INSERT INTO interactions (
                    user_id, venue_id, rating, review_text, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, venue_id, rating, review_text.strip(), timestamp),
            )
        except sqlite3.IntegrityError as error:
            raise ValueError("user_id or venue_id does not exist") from error
        connection.execute(
            "UPDATE users SET review_count = review_count + 1 WHERE user_id = ?",
            (user_id,),
        )
    return True


TOOL_REGISTRY: ToolRegistry = create_registry(
    get_user_profile,
    get_user_history,
    record_interaction,
)
