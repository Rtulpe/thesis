import pytest

from core.database import initialize_database
from mcp_servers import itinerary_server, logistics_server


@pytest.fixture
def database_path(tmp_path, monkeypatch):
    path = tmp_path / "user_state.db"
    initialize_database(path, seed=True)
    monkeypatch.setattr(itinerary_server, "DATABASE_PATH", path)
    monkeypatch.setattr(logistics_server, "DATABASE_PATH", path)
    return path


def test_build_feasible_itinerary_preserves_rank_and_constraints(database_path):
    result = itinerary_server.build_feasible_itinerary(
        ["venue_museum", "venue_market"],
        start_time="09:00",
        end_time="18:00",
        dwell_time_minutes=90,
    )

    assert result["status"] == "feasible"
    assert result["total_visited"] == 2
    assert [stop["venue_id"] for stop in result["schedule"]] == [
        "venue_museum",
        "venue_market",
    ]
    assert result["schedule"][0]["arrival_time"] == "09:00"
    assert result["schedule"][0]["departure_time"] == "10:30"
    assert result["schedule"][1]["arrival_time"] >= "10:30"
    assert result["dropped_venues"] == []


def test_build_feasible_itinerary_drops_candidates_that_cannot_fit(database_path):
    result = itinerary_server.build_feasible_itinerary(
        ["venue_museum", "venue_market"],
        start_time="16:00",
        end_time="18:00",
        dwell_time_minutes=90,
    )

    assert result["status"] == "feasible"
    assert result["total_visited"] == 1
    assert result["schedule"][0]["venue_id"] == "venue_market"
    assert result["dropped_venues"] == ["venue_museum"]


def test_build_feasible_itinerary_accounts_for_start_location(database_path):
    result = itinerary_server.build_feasible_itinerary(
        ["venue_museum"],
        start_time="09:00",
        end_time="18:00",
        dwell_time_minutes=90,
        start_location={"latitude": 52.3760, "longitude": 4.9000},
    )

    assert result["total_visited"] == 1
    assert result["schedule"][0]["travel_time_from_prev"] > 0
    assert result["schedule"][0]["arrival_time"] > "09:00"


def test_build_feasible_itinerary_rejects_invalid_constraints(database_path):
    with pytest.raises(ValueError, match="start_time"):
        itinerary_server.build_feasible_itinerary(
            ["venue_museum"], "invalid", "18:00"
        )
    with pytest.raises(ValueError, match="end_time"):
        itinerary_server.build_feasible_itinerary(
            ["venue_museum"], "10:00", "09:00"
        )
    with pytest.raises(ValueError, match="dwell_time_minutes"):
        itinerary_server.build_feasible_itinerary(
            ["venue_museum"], "10:00", "18:00", dwell_time_minutes=0
        )
