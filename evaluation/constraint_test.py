from __future__ import annotations

from typing import Any


def _minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def evaluate_itinerary_constraints(
    itinerary: dict[str, Any],
    start_time: str,
    end_time: str,
    dwell_time_minutes: int,
) -> dict[str, Any]:
    start = _minutes(start_time)
    end = _minutes(end_time)
    violations: list[dict[str, Any]] = []
    previous_departure = start
    for index, stop in enumerate(itinerary.get("schedule", []), start=1):
        arrival = _minutes(stop["arrival_time"])
        departure = _minutes(stop["departure_time"])
        if arrival < previous_departure:
            violations.append({"stop": index, "reason": "arrival_before_previous_departure"})
        if departure - arrival < dwell_time_minutes:
            violations.append({"stop": index, "reason": "dwell_time_violation"})
        if arrival < start or departure > end:
            violations.append({"stop": index, "reason": "itinerary_window_violation"})
        previous_departure = departure
    return {
        "valid": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }
