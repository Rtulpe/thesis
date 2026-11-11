"""Bounded closed-loop itinerary repair policy."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .trace import ExecutionTrace

Optimizer = Callable[[list[str], dict[str, float]], dict[str, Any]]
SubstituteProvider = Callable[[str, set[str]], list[dict[str, Any]]]


def repair_itinerary(
    candidate_venue_ids: list[str],
    compatibility_scores: dict[str, float],
    violations: list[dict[str, Any]],
    optimize: Optimizer,
    find_substitutes: SubstituteProvider,
    *,
    max_attempts: int = 3,
    execution_trace: ExecutionTrace | None = None,
) -> dict[str, Any]:
    """Repair an infeasible itinerary through bounded substitute re-optimization."""
    if not candidate_venue_ids:
        raise ValueError("candidate_venue_ids must not be empty")
    if set(candidate_venue_ids) != set(compatibility_scores):
        raise ValueError("compatibility_scores must match candidate_venue_ids")
    if max_attempts <= 0:
        raise ValueError("max_attempts must be greater than zero")

    candidates = list(candidate_venue_ids)
    scores = dict(compatibility_scores)
    attempt_trace: list[dict[str, Any]] = []
    current_violations = list(violations)

    for attempt in range(1, max_attempts + 1):
        if execution_trace is not None:
            execution_trace.record(
                "optimizer_call",
                attempt=attempt,
                candidate_venue_ids=list(candidates),
            )
        result = optimize(candidates, scores)
        current_violations = list(result.get("violations", current_violations))
        if execution_trace is not None:
            execution_trace.record(
                "solver_result",
                attempt=attempt,
                status=result.get("status"),
                violations=current_violations,
            )
        attempt_trace.append(
            {
                "attempt": attempt,
                "candidate_venue_ids": list(candidates),
                "violations": current_violations,
                "status": result.get("status"),
            }
        )
        if result.get("status") == "feasible" and not current_violations:
            response = {
                "status": "repaired" if attempt > 1 else "feasible",
                "attempts": attempt,
                "result": result,
                "trace": attempt_trace,
                "termination_reason": "feasible",
            }
            if execution_trace is not None:
                execution_trace.record(
                    "repair_termination",
                    reason="feasible",
                    status=response["status"],
                )
                response["execution_trace"] = execution_trace.as_dict()
            return response
        if attempt == max_attempts:
            break

        violation_codes = {
            violation.get("code")
            for violation in current_violations
            if isinstance(violation, dict) and violation.get("code")
        }
        if not violation_codes:
            break
        existing = set(candidates)
        substitutes: list[dict[str, Any]] = []
        for code in sorted(violation_codes):
            if execution_trace is not None:
                execution_trace.record(
                    "substitute_lookup",
                    attempt=attempt,
                    violation_code=code,
                )
            substitutes.extend(find_substitutes(code, existing))
        added = 0
        for substitute in substitutes:
            venue_id = substitute.get("venue_id")
            score = substitute.get("score")
            if (
                isinstance(venue_id, str)
                and venue_id not in existing
                and isinstance(score, (int, float))
            ):
                candidates.append(venue_id)
                scores[venue_id] = float(score)
                existing.add(venue_id)
                added += 1
        attempt_trace[-1]["substitutes_added"] = added
        if execution_trace is not None:
            execution_trace.record(
                "substitutes_added",
                attempt=attempt,
                count=added,
                venue_ids=list(candidates[len(candidate_venue_ids) :]),
            )
        if not added:
            response = {
                "status": "unrepaired",
                "attempts": attempt,
                "result": result,
                "trace": attempt_trace,
                "termination_reason": "no_substitute",
            }
            if execution_trace is not None:
                execution_trace.record(
                    "repair_termination",
                    reason="no_substitute",
                    status="unrepaired",
                )
                response["execution_trace"] = execution_trace.as_dict()
            return response

    response = {
        "status": "unrepaired",
        "attempts": len(attempt_trace),
        "result": result,
        "trace": attempt_trace,
        "termination_reason": "max_attempts",
    }
    if execution_trace is not None:
        execution_trace.record(
            "repair_termination",
            reason="max_attempts",
            status="unrepaired",
        )
        response["execution_trace"] = execution_trace.as_dict()
    return response
