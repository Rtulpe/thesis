from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any

from .contracts import ToolRegistry, create_registry

DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "user_state.db"
DEFAULT_DAY = "mon"


def _connect() -> sqlite3.Connection:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database does not exist: {DATABASE_PATH}")
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _parse_time(value: str, field: str) -> int:
    try:
        hours, minutes = value.split(":")
        if len(hours) != 2 or len(minutes) != 2:
            raise ValueError
        hour, minute = int(hours), int(minutes)
    except (AttributeError, ValueError):
        raise ValueError(f"{field} must use HH:MM format") from None
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"{field} must use a valid 24-hour time")
    return hour * 60 + minute


def _format_time(minutes: float) -> str:
    total_minutes = int(math.ceil(minutes))
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def _distance_meters(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    radius_m = 6_371_000
    lat_a, lat_b = math.radians(latitude_a), math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lon = math.radians(longitude_b - longitude_a)
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * radius_m * math.asin(math.sqrt(value))


def _load_venues(venue_ids: list[str]) -> dict[str, sqlite3.Row]:
    if not venue_ids:
        raise ValueError("candidate_venue_ids must not be empty")
    if len(set(venue_ids)) != len(venue_ids):
        raise ValueError("candidate_venue_ids must not contain duplicates")
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


def _travel_minutes(
    source: dict[str, float] | sqlite3.Row,
    destination: sqlite3.Row,
) -> float:
    distance = _distance_meters(
        source["latitude"],
        source["longitude"],
        destination["latitude"],
        destination["longitude"],
    )
    return distance / (5_000 / 60)


def build_feasible_itinerary(
    candidate_venue_ids: list[str],
    start_time: str,
    end_time: str,
    dwell_time_minutes: int = 90,
    start_location: dict[str, Any] | None = None,
) -> dict[str, Any]:
    start_minutes = _parse_time(start_time, "start_time")
    end_minutes = _parse_time(end_time, "end_time")
    if end_minutes <= start_minutes:
        raise ValueError("end_time must be after start_time")
    if dwell_time_minutes <= 0:
        raise ValueError("dwell_time_minutes must be greater than zero")
    if start_location is not None:
        if set(start_location) != {"latitude", "longitude"}:
            raise ValueError("start_location requires latitude and longitude")
        try:
            float(start_location["latitude"])
            float(start_location["longitude"])
        except (TypeError, ValueError):
            raise ValueError("start_location coordinates must be numeric") from None

    venues = _load_venues(candidate_venue_ids)
    current_time = float(start_minutes)
    previous: dict[str, float] | sqlite3.Row | None = start_location
    schedule: list[dict[str, Any]] = []
    dropped: list[str] = []

    for venue_id in candidate_venue_ids:
        venue = venues[venue_id]
        travel_time = (
            0.0
            if previous is None
            else _travel_minutes(previous, venue)
        )
        arrival = current_time + travel_time
        hours = json.loads(venue["opening_hours_json"]).get(DEFAULT_DAY)
        if not hours:
            dropped.append(venue_id)
            continue
        opening = _parse_time(hours[0], "opening time")
        closing = _parse_time(hours[1], "closing time")
        arrival = max(arrival, opening)
        departure = arrival + dwell_time_minutes
        if departure > closing or departure > end_minutes:
            dropped.append(venue_id)
            continue
        schedule.append(
            {
                "stop_number": len(schedule) + 1,
                "venue_id": venue_id,
                "arrival_time": _format_time(arrival),
                "departure_time": _format_time(departure),
                "travel_time_from_prev": round(travel_time, 2),
                "binding_reason": (
                    "Selected high-rank candidate; initial stop."
                    if not schedule
                    else "Selected by rank while satisfying time and opening constraints."
                ),
            }
        )
        current_time = departure
        previous = venue

    return {
        "status": "feasible" if schedule else "infeasible",
        "total_visited": len(schedule),
        "schedule": schedule,
        "dropped_venues": dropped,
    }


TOOL_REGISTRY: ToolRegistry = create_registry(build_feasible_itinerary)
