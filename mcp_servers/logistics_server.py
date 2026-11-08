from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any

from .contracts import ToolRegistry, create_registry

DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "user_state.db"
TRAVEL_MODE_SPEEDS_KMH = {
    "walking": 5.0,
    "cycling": 15.0,
    "driving": 30.0,
}
VALID_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


def _connect() -> sqlite3.Connection:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database does not exist: {DATABASE_PATH}")
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _parse_time(time_str: str) -> int:
    try:
        hours, minutes = time_str.split(":")
        if len(hours) != 2 or len(minutes) != 2:
            raise ValueError
        hour = int(hours)
        minute = int(minutes)
    except (AttributeError, ValueError):
        raise ValueError("time_str must use HH:MM format") from None
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("time_str must use a valid 24-hour time")
    return hour * 60 + minute


def _haversine_meters(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    radius_m = 6_371_000
    lat_a, lat_b = math.radians(latitude_a), math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lon = math.radians(longitude_b - longitude_a)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * radius_m * math.asin(math.sqrt(haversine))


def _venue_rows(venue_ids: list[str]) -> dict[str, sqlite3.Row]:
    if not venue_ids:
        raise ValueError("venue_ids must contain at least one venue")
    if len(set(venue_ids)) != len(venue_ids):
        raise ValueError("venue_ids must not contain duplicates")
    placeholders = ",".join("?" for _ in venue_ids)
    with _connect() as connection:
        rows = connection.execute(
            f"SELECT * FROM venues WHERE venue_id IN ({placeholders})",
            venue_ids,
        ).fetchall()
    venues = {row["venue_id"]: row for row in rows}
    missing = [venue_id for venue_id in venue_ids if venue_id not in venues]
    if missing:
        raise ValueError(f"Unknown venue: {missing[0]}")
    return venues


def get_city_venues(
    city: str,
    category_filter: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    if not city or not city.strip():
        raise ValueError("city must not be empty")
    if limit <= 0:
        raise ValueError("limit must be greater than zero")
    category = category_filter.strip().lower() if category_filter else None
    if category_filter is not None and not category:
        raise ValueError("category_filter must not be empty")

    query = "SELECT * FROM venues WHERE city = ?"
    parameters: list[Any] = [city.strip()]
    if category:
        query += " AND (',' || lower(categories) || ',') LIKE ?"
        parameters.append(f"%,{category},%")
    query += " ORDER BY venue_id LIMIT ?"
    parameters.append(limit)

    with _connect() as connection:
        rows = connection.execute(query, parameters).fetchall()
    venues = []
    for row in rows:
        venue = dict(row)
        venue["opening_hours"] = json.loads(row["opening_hours_json"])
        venues.append(venue)
    return venues


def calculate_travel_matrix(
    venue_ids: list[str],
    travel_mode: str = "walking",
) -> dict[str, Any]:
    if travel_mode not in TRAVEL_MODE_SPEEDS_KMH:
        raise ValueError(f"Unsupported travel_mode: {travel_mode}")
    venues = _venue_rows(venue_ids)
    distances: dict[str, dict[str, float]] = {}
    travel_times: dict[str, dict[str, float]] = {}
    speed_m_per_minute = TRAVEL_MODE_SPEEDS_KMH[travel_mode] * 1000 / 60
    for source_id in venue_ids:
        distances[source_id] = {}
        travel_times[source_id] = {}
        for destination_id in venue_ids:
            if source_id == destination_id:
                distance = 0.0
            else:
                source = venues[source_id]
                destination = venues[destination_id]
                distance = _haversine_meters(
                    source["latitude"],
                    source["longitude"],
                    destination["latitude"],
                    destination["longitude"],
                )
            distances[source_id][destination_id] = distance
            travel_times[source_id][destination_id] = distance / speed_m_per_minute
    return {"travel_times": travel_times, "distances": distances}


def check_venue_open_status(
    venue_id: str,
    day_of_week: str,
    time_str: str,
) -> bool:
    day = day_of_week.strip().lower() if day_of_week else ""
    if day not in VALID_DAYS:
        raise ValueError("day_of_week must be a three-letter lowercase day")
    minute = _parse_time(time_str)
    venue = _venue_rows([venue_id])[venue_id]
    opening_hours = json.loads(venue["opening_hours_json"])
    window = opening_hours.get(day)
    if not window:
        return False
    opening = _parse_time(window[0])
    closing = _parse_time(window[1])
    return opening <= minute <= closing


TOOL_REGISTRY: ToolRegistry = create_registry(
    get_city_venues,
    calculate_travel_matrix,
    check_venue_open_status,
)
