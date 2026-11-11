from core.optw_solver import optimize_time_window_orienteering


def _matrices():
    nodes = ["__start__", "a", "b", "c"]
    times = {source: {target: 5 for target in nodes} for source in nodes}
    distances = {source: {target: 100 for target in nodes} for source in nodes}
    return times, distances


def test_optw_maximizes_score_under_time_windows():
    times, distances = _matrices()
    result = optimize_time_window_orienteering(
        [
            {"venue_id": "a", "score": 5.0, "opening_time": 540, "closing_time": 720},
            {"venue_id": "b", "score": 9.0, "opening_time": 540, "closing_time": 640},
            {"venue_id": "c", "score": 4.0, "opening_time": 540, "closing_time": 720},
        ],
        times,
        distances,
        540,
        720,
        90,
    )

    assert result["status"] == "feasible"
    assert result["objective_score"] == 9.0
    assert [stop["venue_id"] for stop in result["schedule"]] == ["b"]
    assert set(result["dropped_venues"]) == {"a", "c"}


def test_optw_enforces_distance_and_stop_budgets():
    times, distances = _matrices()
    result = optimize_time_window_orienteering(
        [
            {"venue_id": "a", "score": 5.0, "opening_time": 540, "closing_time": 720},
            {"venue_id": "b", "score": 4.0, "opening_time": 540, "closing_time": 720},
        ],
        times,
        distances,
        540,
        720,
        60,
        max_distance=100,
        max_stops=1,
    )

    assert result["total_distance"] == 100
    assert len(result["schedule"]) == 1


def test_optw_is_deterministic_for_equal_scores():
    times, distances = _matrices()
    kwargs = {
        "candidates": [
            {"venue_id": "b", "score": 1.0, "opening_time": 540, "closing_time": 600},
            {"venue_id": "a", "score": 1.0, "opening_time": 540, "closing_time": 600},
        ],
        "travel_times": times,
        "distances": distances,
        "start_time": 540,
        "end_time": 600,
        "dwell_time": 60,
    }

    assert optimize_time_window_orienteering(**kwargs) == optimize_time_window_orienteering(
        **kwargs
    )
