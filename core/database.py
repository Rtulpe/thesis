from __future__ import annotations

import json
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    review_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS venues (
    venue_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    categories TEXT NOT NULL,
    avg_rating REAL NOT NULL,
    opening_hours_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interactions (
    interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    venue_id TEXT NOT NULL,
    rating REAL NOT NULL,
    review_text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(venue_id) REFERENCES venues(venue_id)
);
"""

SEED_USERS = (
    ("user_demo", "Demo Traveller", 1),
)

SEED_VENUES = (
    (
        "venue_museum",
        "City History Museum",
        "Amsterdam",
        52.3731,
        4.8922,
        "museum,history,culture",
        4.5,
        json.dumps({"mon": ["09:00", "17:00"], "tue": ["09:00", "17:00"]}),
    ),
    (
        "venue_market",
        "Canal Market",
        "Amsterdam",
        52.3760,
        4.9000,
        "market,food,local",
        4.2,
        json.dumps({"mon": ["10:00", "18:00"], "tue": ["10:00", "18:00"]}),
    ),
)

SEED_INTERACTIONS = (
    (
        "user_demo",
        "venue_museum",
        5.0,
        "I enjoy thoughtful history exhibits and local culture.",
        "2026-01-15T12:00:00",
    ),
)


def initialize_database(database_path: str | Path, *, seed: bool = False) -> None:
    """Create the user-state schema and optionally insert idempotent demo data."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)
        if seed:
            connection.executemany(
                """
                INSERT OR IGNORE INTO users (user_id, name, review_count)
                VALUES (?, ?, ?)
                """,
                SEED_USERS,
            )
            connection.executemany(
                """
                INSERT OR IGNORE INTO venues (
                    venue_id, name, city, latitude, longitude, categories,
                    avg_rating, opening_hours_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                SEED_VENUES,
            )
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
                [
                    interaction + (
                        interaction[0],
                        interaction[1],
                        interaction[3],
                    )
                    for interaction in SEED_INTERACTIONS
                ],
            )
            connection.execute(
                """
                UPDATE users
                SET review_count = (
                    SELECT COUNT(*)
                    FROM interactions
                    WHERE interactions.user_id = users.user_id
                )
                """
            )
