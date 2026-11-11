"""Deterministic exact solver for small time-window orienteering instances."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OPTWResult:
    status: str
    objective_score: float
    total_travel_time: float
    total_distance: float
    schedule: list[dict[str, Any]]
    dropped_venues: list[str]
    solver: str = "exact-branch-and-bound"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "objective_score": round(self.objective_score, 6),
            "total_travel_time": round(self.total_travel_time, 3),
            "total_distance": round(self.total_distance, 3),
            "schedule": self.schedule,
            "dropped_venues": self.dropped_venues,
            "solver": self.solver,
        }


def optimize_time_window_orienteering(
    candidates: list[dict[str, Any]],
    travel_times: dict[str, dict[str, float]],
    distances: dict[str, dict[str, float]],
    start_time: int,
    end_time: int,
    dwell_time: int,
    *,
    start_node: str = "__start__",
    max_distance: float | None = None,
    max_stops: int | None = None,
) -> dict[str, Any]:
    """Solve a small OPTW instance exactly with deterministic depth-first search."""
    if not candidates:
        raise ValueError("candidates must not be empty")
    if end_time <= start_time:
        raise ValueError("end_time must be after start_time")
    if dwell_time <= 0:
        raise ValueError("dwell_time must be greater than zero")
    if max_distance is not None and max_distance < 0:
        raise ValueError("max_distance must not be negative")
    if max_stops is not None and max_stops <= 0:
        raise ValueError("max_stops must be greater than zero")

    candidate_ids = [candidate.get("venue_id") for candidate in candidates]
    if any(not isinstance(venue_id, str) or not venue_id for venue_id in candidate_ids):
        raise ValueError("each candidate requires a venue_id")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("candidate venue_ids must be unique")
    by_id = {candidate["venue_id"]: candidate for candidate in candidates}
    for candidate in candidates:
        if not isinstance(candidate.get("score"), (int, float)):
            raise ValueError(f"candidate score is invalid: {candidate['venue_id']}")
        opening = candidate.get("opening_time")
        closing = candidate.get("closing_time")
        if not isinstance(opening, int) or not isinstance(closing, int):
            raise ValueError(f"candidate window is invalid: {candidate['venue_id']}")
        if closing <= opening:
            raise ValueError(f"candidate window is invalid: {candidate['venue_id']}")

    def matrix_value(
        matrix: dict[str, dict[str, float]], source: str, target: str
    ) -> float:
        try:
            value = float(matrix[source][target])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"missing matrix value: {source}->{target}") from None
        if value < 0:
            raise ValueError(f"matrix value must not be negative: {source}->{target}")
        return value

    best: tuple[float, float, float, tuple[str, ...], list[dict[str, Any]]] = (
        0.0,
        0.0,
        0.0,
        (),
        [],
    )

    def search(
        current: str,
        current_time: float,
        visited: frozenset[str],
        score: float,
        travel_time: float,
        distance: float,
        schedule: list[dict[str, Any]],
    ) -> None:
        nonlocal best
        ids = tuple(stop["venue_id"] for stop in schedule)
        candidate = (score, -travel_time, -distance, tuple(ids), schedule)
        best_ids = best[4]
        if (
            candidate[:4] > (best[0], -best[1], -best[2], best[3])
            or (candidate[:4] == (best[0], -best[1], -best[2], best[3]) and ids < tuple(
                stop["venue_id"] for stop in best_ids
            ))
        ):
            best = (score, travel_time, distance, ids, [*schedule])

        if max_stops is not None and len(schedule) >= max_stops:
            return
        for venue_id in sorted(set(candidate_ids) - visited):
            venue = by_id[venue_id]
            leg_time = matrix_value(travel_times, current, venue_id)
            leg_distance = matrix_value(distances, current, venue_id)
            next_distance = distance + leg_distance
            if max_distance is not None and next_distance > max_distance:
                continue
            arrival = max(current_time + leg_time, venue["opening_time"])
            departure = arrival + dwell_time
            if departure > venue["closing_time"] or departure > end_time:
                continue
            search(
                venue_id,
                departure,
                visited | {venue_id},
                score + float(venue["score"]),
                travel_time + leg_time,
                next_distance,
                [
                    *schedule,
                    {
                        "stop_number": len(schedule) + 1,
                        "venue_id": venue_id,
                        "arrival_time": int(arrival),
                        "departure_time": int(departure),
                        "travel_time_from_prev": round(leg_time, 3),
                        "distance_from_prev": round(leg_distance, 3),
                    },
                ],
            )

    search(start_node, float(start_time), frozenset(), 0.0, 0.0, 0.0, [])
    selected = set(best[3])
    return OPTWResult(
        status="feasible" if best[4] else "infeasible",
        objective_score=best[0],
        total_travel_time=best[1],
        total_distance=best[2],
        schedule=best[4],
        dropped_venues=[venue_id for venue_id in candidate_ids if venue_id not in selected],
    ).as_dict()
