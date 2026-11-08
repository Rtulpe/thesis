from __future__ import annotations

import math
import re
import sqlite3
from pathlib import Path
from typing import Any

from .contracts import ToolRegistry, create_registry

DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "user_state.db"
VIBE_DIMENSIONS = (
    "culture",
    "history",
    "food",
    "nature",
    "nightlife",
    "local",
)
VIBE_TERMS = {
    "culture": {"culture", "art", "museum", "music", "gallery", "theatre"},
    "history": {"history", "historic", "heritage", "exhibit", "exhibits"},
    "food": {"food", "restaurant", "market", "taste", "cuisine"},
    "nature": {"nature", "park", "garden", "outdoors", "lake"},
    "nightlife": {"nightlife", "bar", "club", "concert", "party"},
    "local": {"local", "neighborhood", "neighbourhood", "community"},
}
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _connect() -> sqlite3.Connection:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database does not exist: {DATABASE_PATH}")
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _normalize(values: list[float]) -> list[float]:
    total = sum(values)
    if total == 0:
        return [1.0 / len(values)] * len(values)
    return [value / total for value in values]


def _vibe_from_text(text: str) -> dict[str, Any]:
    tokens = set(TOKEN_PATTERN.findall(text.lower()))
    raw_values = [
        float(len(tokens & VIBE_TERMS[dimension])) for dimension in VIBE_DIMENSIONS
    ]
    embedding = _normalize(raw_values)
    return {
        "dimensions": dict(zip(VIBE_DIMENSIONS, embedding)),
        "embedding": embedding,
    }


def _venue_profile_rows(venue_id: str) -> list[sqlite3.Row]:
    with _connect() as connection:
        venue = connection.execute(
            "SELECT venue_id FROM venues WHERE venue_id = ?", (venue_id,)
        ).fetchone()
        if venue is None:
            raise ValueError(f"Unknown venue: {venue_id}")
        return connection.execute(
            "SELECT review_text FROM interactions WHERE venue_id = ? "
            "ORDER BY interaction_id",
            (venue_id,),
        ).fetchall()


def _user_review_text(user_id: str) -> str:
    with _connect() as connection:
        user = connection.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if user is None:
            raise ValueError(f"Unknown user: {user_id}")
        rows = connection.execute(
            "SELECT review_text FROM interactions WHERE user_id = ? "
            "ORDER BY interaction_id",
            (user_id,),
        ).fetchall()
    if not rows:
        raise ValueError(f"User has no review history: {user_id}")
    return " ".join(row["review_text"] for row in rows)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(
        sum(value * value for value in right)
    )
    if denominator == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / denominator


def extract_text_vibe(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must not be empty")
    return _vibe_from_text(text)


def get_visitor_profile(venue_id: str) -> dict[str, Any]:
    rows = _venue_profile_rows(venue_id)
    if not rows:
        embedding = _normalize([0.0] * len(VIBE_DIMENSIONS))
    else:
        embeddings = [_vibe_from_text(row["review_text"])["embedding"] for row in rows]
        embedding = _normalize(
            [sum(values[index] for values in embeddings) for index in range(len(VIBE_DIMENSIONS))]
        )
    return {
        "venue_id": venue_id,
        "review_count": len(rows),
        "dimensions": dict(zip(VIBE_DIMENSIONS, embedding)),
        "embedding": embedding,
    }


def score_venue_compatibility(
    user_text_or_id: str,
    candidate_venue_ids: list[str],
) -> list[dict[str, Any]]:
    if not isinstance(user_text_or_id, str) or not user_text_or_id.strip():
        raise ValueError("user_text_or_id must not be empty")
    if not candidate_venue_ids:
        raise ValueError("candidate_venue_ids must not be empty")
    if len(set(candidate_venue_ids)) != len(candidate_venue_ids):
        raise ValueError("candidate_venue_ids must not contain duplicates")

    with _connect() as connection:
        user = connection.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_text_or_id,)
        ).fetchone()
    user_text = (
        _user_review_text(user_text_or_id)
        if user is not None
        else user_text_or_id
    )
    user_embedding = _vibe_from_text(user_text)["embedding"]
    results = []
    for venue_id in candidate_venue_ids:
        profile = get_visitor_profile(venue_id)
        results.append(
            {
                "venue_id": venue_id,
                "score": round(
                    max(0.0, min(1.0, _cosine_similarity(user_embedding, profile["embedding"]))),
                    6,
                ),
            }
        )
    return sorted(results, key=lambda item: (-item["score"], item["venue_id"]))


TOOL_REGISTRY: ToolRegistry = create_registry(
    extract_text_vibe,
    get_visitor_profile,
    score_venue_compatibility,
)
