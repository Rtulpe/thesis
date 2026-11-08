from evaluation.benchmark_eval import benchmark_methods
from evaluation.constraint_test import evaluate_itinerary_constraints


def test_constraint_evaluation_reports_zero_violations_for_valid_schedule():
    itinerary = {
        "schedule": [
            {
                "arrival_time": "09:00",
                "departure_time": "10:30",
            },
            {
                "arrival_time": "11:00",
                "departure_time": "12:30",
            },
        ]
    }

    report = evaluate_itinerary_constraints(itinerary, "09:00", "18:00", 90)

    assert report["violation_count"] == 0
    assert report["valid"] is True


def test_constraint_evaluation_counts_invalid_time_order():
    itinerary = {
        "schedule": [
            {
                "arrival_time": "10:00",
                "departure_time": "09:00",
            }
        ]
    }

    report = evaluate_itinerary_constraints(itinerary, "09:00", "18:00", 90)

    assert report["violation_count"] == 1
    assert report["valid"] is False


def test_benchmark_methods_reports_metrics_for_dynamic_and_baseline_planners():
    requests = [
        {
            "start_time": "09:00",
            "end_time": "18:00",
            "dwell_time_minutes": 90,
            "relevant_venue_ids": ["v1"],
        }
    ]

    def dynamic(**request):
        return {
            "status": "feasible",
            "schedule": [
                {
                    "venue_id": "v1",
                    "arrival_time": "09:00",
                    "departure_time": "10:30",
                }
            ],
            "total_visited": 1,
        }

    def baseline(**request):
        return {
            "status": "feasible",
            "schedule": [
                {
                    "venue_id": "v2",
                    "arrival_time": "09:00",
                    "departure_time": "10:00",
                }
            ],
            "total_visited": 1,
        }

    report = benchmark_methods(
        requests,
        {"dynamic": dynamic, "popularity": baseline},
    )

    assert report["request_count"] == 1
    assert report["methods"]["dynamic"]["feasibility_rate"] == 1.0
    assert report["methods"]["dynamic"]["relevance_rate"] == 1.0
    assert report["methods"]["popularity"]["constraint_violation_rate"] == 1.0
    assert report["methods"]["popularity"]["relevance_rate"] == 0.0
    assert report["methods"]["dynamic"]["latency_ms"]["count"] == 1


def test_benchmark_methods_rejects_empty_methods():
    try:
        benchmark_methods([], {})
    except ValueError as error:
        assert "at least one method" in str(error)
    else:
        raise AssertionError("Expected empty methods to be rejected")
