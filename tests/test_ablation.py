import pytest

from evaluation.ablation import run_ablation


def test_ablation_runs_all_configurations_on_shared_scenarios():
    scenarios = [{"scenario_id": "s1"}]

    def runner(scenario):
        return {
            "status": "feasible",
            "objective_score": 0.8,
            "total_travel_time": 12,
            "total_distance": 500,
            "violations": [],
        }

    report = run_ablation(
        scenarios,
        {
            "direct_llm": runner,
            "mcp_vector": runner,
            "optw_repair": runner,
        },
    )

    assert report["scenario_count"] == 1
    assert set(report["configurations"]) == {
        "direct_llm",
        "mcp_vector",
        "optw_repair",
    }
    assert report["configurations"]["optw_repair"]["itinerary_validity_rate"] == 1.0
    assert report["configurations"]["optw_repair"]["cumulative_preference_score"] == 0.8


def test_ablation_requires_all_thesis_configurations():
    with pytest.raises(ValueError, match="missing configuration"):
        run_ablation([], {"direct_llm": lambda scenario: {}})
