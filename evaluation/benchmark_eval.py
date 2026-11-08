from __future__ import annotations

import json
import time
from pathlib import Path
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


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _latency_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0}
    return {
        "count": len(values),
        "mean": round(sum(values) / len(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def benchmark_methods(
    requests: Iterable[dict[str, Any]],
    methods: dict[str, Callable[..., dict[str, Any]]],
) -> dict[str, Any]:
    """Compare planner callables using shared feasibility and relevance metrics.

    Requests may include ``relevant_venue_ids`` and ``candidate_venue_ids``.
    Relevance is measured as the fraction of selected venues in the relevant set;
    coverage is measured against the candidate set when supplied.
    """
    if not methods:
        raise ValueError("at least one method is required")
    request_list = list(requests)
    reports: dict[str, dict[str, Any]] = {}
    for method_name, planner in methods.items():
        method_results: list[dict[str, Any]] = []
        latencies: list[float] = []
        valid_count = 0
        feasible_count = 0
        violation_total = 0
        relevant_selected = 0
        relevant_total = 0
        visited_total = 0
        candidate_total = 0
        for request in request_list:
            planner_request = {
                key: value
                for key, value in request.items()
                if key not in {"relevant_venue_ids", "candidate_venue_ids"}
            }
            started = time.perf_counter()
            result = planner(**planner_request)
            latency_ms = (time.perf_counter() - started) * 1000
            constraint_report = evaluate_itinerary_constraints(
                result,
                request["start_time"],
                request["end_time"],
                request["dwell_time_minutes"],
            )
            schedule_ids = {
                stop["venue_id"] for stop in result.get("schedule", [])
            }
            relevant_ids = set(request.get("relevant_venue_ids", []))
            candidate_ids = set(request.get("candidate_venue_ids", []))
            relevant_selected += len(schedule_ids & relevant_ids)
            relevant_total += len(schedule_ids)
            visited_total += len(schedule_ids)
            candidate_total += len(candidate_ids)
            valid_count += int(constraint_report["valid"])
            feasible_count += int(result.get("status") == "feasible")
            violation_total += constraint_report["violation_count"]
            latencies.append(latency_ms)
            method_results.append(
                {
                    "result": result,
                    "constraints": constraint_report,
                    "latency_ms": round(latency_ms, 3),
                }
            )
        reports[method_name] = {
            "request_count": len(request_list),
            "feasibility_rate": _rate(feasible_count, len(request_list)),
            "constraint_validity_rate": _rate(valid_count, len(request_list)),
            "constraint_violation_rate": _rate(
                int(violation_total > 0), len(request_list)
            ),
            "constraint_violation_count": violation_total,
            "relevance_rate": _rate(relevant_selected, relevant_total),
            "coverage_rate": _rate(visited_total, candidate_total),
            "visited_total": visited_total,
            "latency_ms": _latency_summary(latencies),
            "tool_call_total": sum(
                item["result"].get("tool_calls", 0) for item in method_results
            ),
            "results": method_results,
        }
    return {
        "request_count": len(request_list),
        "methods": reports,
    }


def write_benchmark_report(report: dict[str, Any], output_path: str | Path) -> None:
    """Write a benchmark report as indented JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
