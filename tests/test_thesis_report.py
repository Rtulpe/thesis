import json

from evaluation.thesis_report import run_thesis_validation, write_thesis_report


def test_thesis_validation_is_reproducible_and_writes_reports(tmp_path):
    def runner(scenario):
        return {
            "status": "feasible",
            "objective_score": 1.0,
            "total_travel_time": 10.0,
            "total_distance": 100.0,
            "violations": [],
        }

    runners = {
        "direct_llm": runner,
        "mcp_vector": runner,
        "optw_repair": runner,
    }
    validation = run_thesis_validation(runners, seed=3, repetitions=1)
    second = run_thesis_validation(runners, seed=3, repetitions=1)

    assert validation == second
    json_path = tmp_path / "reports" / "results.json"
    summary_path = tmp_path / "reports" / "summary.txt"
    write_thesis_report(validation, json_path, summary_path)

    assert json.loads(json_path.read_text()) == validation
    assert "optw_repair:" in summary_path.read_text()
