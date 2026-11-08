from agent.orchestrator import TravelOrchestrator
from core.database import initialize_database
from mcp_servers import itinerary_server, logistics_server, profiler_server, user_state_server


def test_concrete_servers_produce_an_end_to_end_itinerary(tmp_path, monkeypatch):
    database_path = tmp_path / "user_state.db"
    initialize_database(database_path, seed=True)
    for module in (
        itinerary_server,
        logistics_server,
        profiler_server,
        user_state_server,
    ):
        monkeypatch.setattr(module, "DATABASE_PATH", database_path)

    class ConcreteTools:
        get_user_profile = staticmethod(user_state_server.get_user_profile)
        get_user_history = staticmethod(user_state_server.get_user_history)
        get_city_venues = staticmethod(logistics_server.get_city_venues)
        score_venue_compatibility = staticmethod(
            profiler_server.score_venue_compatibility
        )
        build_feasible_itinerary = staticmethod(
            itinerary_server.build_feasible_itinerary
        )

    result = TravelOrchestrator(ConcreteTools()).plan(
        user_id="user_demo",
        city="Amsterdam",
        start_time="09:00",
        end_time="18:00",
    )

    assert result["status"] == "feasible"
    assert result["total_visited"] >= 1
    assert len(result["explanation"]["selected_venues"]) == result["total_visited"]
