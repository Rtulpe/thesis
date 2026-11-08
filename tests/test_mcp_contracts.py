import inspect

from mcp_servers import (
    itinerary_server,
    logistics_server,
    profiler_server,
    user_state_server,
)


def test_each_server_registers_the_documented_tools():
    assert set(user_state_server.TOOL_REGISTRY.tools) == {
        "get_user_profile",
        "get_user_history",
        "record_interaction",
    }
    assert set(logistics_server.TOOL_REGISTRY.tools) == {
        "get_city_venues",
        "calculate_travel_matrix",
        "check_venue_open_status",
    }
    assert set(profiler_server.TOOL_REGISTRY.tools) == {
        "extract_text_vibe",
        "get_visitor_profile",
        "score_venue_compatibility",
    }
    assert set(itinerary_server.TOOL_REGISTRY.tools) == {
        "build_feasible_itinerary",
    }


def test_tool_signatures_match_plan_contracts():
    assert list(inspect.signature(user_state_server.get_user_profile).parameters) == [
        "user_id"
    ]
    assert list(inspect.signature(user_state_server.get_user_history).parameters) == [
        "user_id",
        "limit",
    ]
    assert list(inspect.signature(user_state_server.record_interaction).parameters) == [
        "user_id",
        "venue_id",
        "rating",
        "review_text",
    ]
    assert list(inspect.signature(logistics_server.get_city_venues).parameters) == [
        "city",
        "category_filter",
        "limit",
    ]
    assert list(
        inspect.signature(logistics_server.calculate_travel_matrix).parameters
    ) == ["venue_ids", "travel_mode"]
    assert list(
        inspect.signature(logistics_server.check_venue_open_status).parameters
    ) == ["venue_id", "day_of_week", "time_str"]
    assert list(inspect.signature(profiler_server.extract_text_vibe).parameters) == [
        "text"
    ]
    assert list(inspect.signature(profiler_server.get_visitor_profile).parameters) == [
        "venue_id"
    ]
    assert list(
        inspect.signature(profiler_server.score_venue_compatibility).parameters
    ) == ["user_text_or_id", "candidate_venue_ids"]
    assert list(
        inspect.signature(itinerary_server.build_feasible_itinerary).parameters
    ) == [
        "candidate_venue_ids",
        "start_time",
        "end_time",
        "dwell_time_minutes",
        "start_location",
    ]
