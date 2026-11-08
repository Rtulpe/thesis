from __future__ import annotations

from typing import Any, Callable, Iterable

from .constraint_test import evaluate_itinerary_constraints


def compare_itinerary_methods(
    itineraries: Iterable[dict[str, Any]],
    start_time: str,
    end_time: str,
    dwell_time_minutes: int,
) -> dict[str, Any]:
    reports = [
        evaluate_itinerary_constraints(
            itinerary,
            start_time,
            end_time,
            dwell_time_minutes,
        )
        for itinerary in itineraries
    ]
    return {
        "itinerary_count": len(reports),
        "valid_count": sum(report["valid"] for report in reports),
        "violation_count": sum(report["violation_count"] for report in reports),
        "reports": reports,
    }


def evaluate_recommender(
    planner: Callable[..., dict[str, Any]],
    requests: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    results = [planner(**request) for request in requests]
    return {
        "request_count": len(results),
        "feasible_count": sum(result.get("status") == "feasible" for result in results),
        "visited_total": sum(result.get("total_visited", 0) for result in results),
        "results": results,
    }
