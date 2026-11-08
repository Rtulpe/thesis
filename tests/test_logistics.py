import json

import pytest

from core.database import initialize_database
from mcp_servers import logistics_server


@pytest.fixture
def database_path(tmp_path, monkeypatch):
    path = tmp_path / "user_state.db"
    initialize_database(path, seed=True)
    monkeypatch.setattr(logistics_server, "DATABASE_PATH", path)
    return path


def test_get_city_venues_filters_exact_city_and_category(database_path):
    venues = logistics_server.get_city_venues(
        "Amsterdam",
        category_filter="culture",
        limit=10,
    )

    assert [venue["venue_id"] for venue in venues] == ["venue_museum"]
    assert venues[0]["city"] == "Amsterdam"
    assert isinstance(venues[0]["opening_hours"], dict)


def test_get_city_venues_rejects_invalid_limit(database_path):
    with pytest.raises(ValueError, match="limit"):
        logistics_server.get_city_venues("Amsterdam", limit=0)


def test_calculate_travel_matrix_is_symmetric_and_contains_zero_diagonal(
    database_path,
):
    matrix = logistics_server.calculate_travel_matrix(
        ["venue_museum", "venue_market"],
        travel_mode="walking",
    )

    assert set(matrix) == {"travel_times", "distances"}
    assert matrix["travel_times"]["venue_museum"]["venue_museum"] == 0
    assert matrix["distances"]["venue_market"]["venue_market"] == 0
    assert matrix["distances"]["venue_museum"]["venue_market"] == pytest.approx(
        matrix["distances"]["venue_market"]["venue_museum"]
    )
    assert matrix["travel_times"]["venue_museum"]["venue_market"] > 0


def test_calculate_travel_matrix_rejects_unknown_mode_or_venue(database_path):
    with pytest.raises(ValueError, match="travel_mode"):
        logistics_server.calculate_travel_matrix(
            ["venue_museum"],
            travel_mode="teleportation",
        )

    with pytest.raises(ValueError, match="venue"):
        logistics_server.calculate_travel_matrix(["missing"])


def test_calculate_travel_matrix_uses_cached_route(database_path, monkeypatch):
    class CachedRoute:
        def get(self, source, destination, mode):
            return {
                "distance_meters": 1234.0,
                "duration_minutes": 12.5,
                "source": "cache",
            }

    monkeypatch.setattr(logistics_server, "ROUTE_CACHE", CachedRoute())
    monkeypatch.setattr(logistics_server, "OSRM_ROUTER", None)
    matrix = logistics_server.calculate_travel_matrix(
        ["venue_museum", "venue_market"],
        travel_mode="walking",
    )

    assert matrix["distances"]["venue_museum"]["venue_market"] == 1234.0
    assert matrix["travel_times"]["venue_museum"]["venue_market"] == 12.5


def test_check_venue_open_status_includes_opening_boundaries(database_path):
    assert logistics_server.check_venue_open_status(
        "venue_museum", "mon", "09:00"
    )
    assert logistics_server.check_venue_open_status(
        "venue_museum", "mon", "17:00"
    )
    assert not logistics_server.check_venue_open_status(
        "venue_museum", "mon", "17:01"
    )


def test_check_venue_open_status_rejects_invalid_inputs(database_path):
    with pytest.raises(ValueError, match="day_of_week"):
        logistics_server.check_venue_open_status("venue_museum", "monday", "10:00")

    with pytest.raises(ValueError, match="time_str"):
        logistics_server.check_venue_open_status("venue_museum", "mon", "invalid")


def test_seed_opening_hours_are_valid_json(database_path):
    venues = logistics_server.get_city_venues("Amsterdam")
    assert json.loads(venues[0]["opening_hours_json"]) == venues[0]["opening_hours"]
