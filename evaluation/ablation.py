"""Three-configuration thesis ablation runner."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any


ConfigurationRunner = Callable[[dict[str, Any]], dict[str, Any]]
CONFIGURATIONS = ("direct_llm", "mcp_vector", "optw_repair")


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def run_ablation(
    scenarios: Iterable[dict[str, Any]],
    runners: dict[str, ConfigurationRunner],
) -> dict[str, Any]:
    """Run comparable configuration runners over the same scenario fixtures."""
    missing = set(CONFIGURATIONS) - set(runners)
    if missing:
        raise ValueError(f"missing configuration runners: {', '.join(sorted(missing))}")
    scenario_list = list(scenarios)
    reports: dict[str, dict[str, Any]] = {}
    for configuration in CONFIGURATIONS:
        results: list[dict[str, Any]] = []
        validities: list[float] = []
        preference_scores: list[float] = []
        travel_times: list[float] = []
        travel_distances: list[float] = []
        for scenario in scenario_list:
            result = runners[configuration](scenario)
            violations = result.get("violations", [])
            validities.append(float(not violations and result.get("status") == "feasible"))
            preference_scores.append(float(result.get("objective_score", 0.0)))
            travel_times.append(float(result.get("total_travel_time", 0.0)))
            travel_distances.append(float(result.get("total_distance", 0.0)))
            results.append(
                {
                    "scenario_id": scenario.get("scenario_id"),
                    "result": result,
                }
            )
        reports[configuration] = {
            "scenario_count": len(scenario_list),
            "itinerary_validity_rate": _mean(validities),
            "cumulative_preference_score": round(sum(preference_scores), 6),
            "mean_preference_score": _mean(preference_scores),
            "mean_travel_time": _mean(travel_times),
            "mean_travel_distance": _mean(travel_distances),
            "results": results,
        }
    return {
        "scenario_count": len(scenario_list),
        "configurations": reports,
    }
