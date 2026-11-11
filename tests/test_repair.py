from core.repair import repair_itinerary
from core.trace import ExecutionTrace


def test_repair_adds_substitute_and_reoptimizes():
    calls = []

    def optimize(candidates, scores):
        calls.append(list(candidates))
        if "replacement" in candidates:
            return {
                "status": "feasible",
                "violations": [],
                "schedule": [{"venue_id": "replacement"}],
            }
        return {
            "status": "infeasible",
            "violations": [{"code": "NO_FEASIBLE_ITINERARY"}],
        }

    result = repair_itinerary(
        ["original"],
        {"original": 0.5},
        [{"code": "NO_FEASIBLE_ITINERARY"}],
        optimize,
        lambda code, existing: [{"venue_id": "replacement", "score": 0.9}],
    )

    assert result["status"] == "repaired"
    assert result["attempts"] == 2
    assert calls == [["original"], ["original", "replacement"]]
    assert result["trace"][0]["substitutes_added"] == 1


def test_repair_terminates_when_no_substitute_exists():
    result = repair_itinerary(
        ["original"],
        {"original": 0.5},
        [{"code": "TRAVEL_TIME_BUDGET_EXCEEDED"}],
        lambda candidates, scores: {
            "status": "infeasible",
            "violations": [{"code": "TRAVEL_TIME_BUDGET_EXCEEDED"}],
        },
        lambda code, existing: [],
    )

    assert result["status"] == "unrepaired"
    assert result["termination_reason"] == "no_substitute"
    assert result["attempts"] == 1


def test_repair_respects_attempt_limit():
    result = repair_itinerary(
        ["original"],
        {"original": 0.5},
        [{"code": "NO_FEASIBLE_ITINERARY"}],
        lambda candidates, scores: {
            "status": "infeasible",
            "violations": [{"code": "NO_FEASIBLE_ITINERARY"}],
        },
        lambda code, existing: [
            {"venue_id": f"replacement-{len(existing)}", "score": 0.1}
        ],
        max_attempts=2,
    )

    assert result["termination_reason"] == "max_attempts"
    assert result["attempts"] == 2


def test_repair_returns_structured_execution_trace():
    execution_trace = ExecutionTrace()
    result = repair_itinerary(
        ["original"],
        {"original": 0.5},
        [{"code": "NO_FEASIBLE_ITINERARY"}],
        lambda candidates, scores: {
            "status": "infeasible",
            "violations": [{"code": "NO_FEASIBLE_ITINERARY"}],
        },
        lambda code, existing: [],
        execution_trace=execution_trace,
    )

    events = result["execution_trace"]["events"]
    assert [event["event"] for event in events] == [
        "optimizer_call",
        "solver_result",
        "substitute_lookup",
        "substitutes_added",
        "repair_termination",
    ]
