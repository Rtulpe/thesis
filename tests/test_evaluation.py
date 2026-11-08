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
