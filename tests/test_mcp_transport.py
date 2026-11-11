import inspect

import pytest

from mcp_servers.mcp_transport import (
    create_itinerary_server,
    create_logistics_server,
    create_profiler_server,
    create_user_state_server,
    create_server,
)


@pytest.mark.parametrize(
    ("factory", "expected_tools"),
    [
        (
            create_user_state_server,
            {"get_user_profile", "get_user_history", "record_interaction"},
        ),
        (
            create_logistics_server,
            {
                "get_city_venues",
                "calculate_travel_matrix",
                "check_venue_open_status",
                "validate_travel_budget",
            },
        ),
        (
            create_profiler_server,
            {
                "extract_text_vibe",
                "get_visitor_profile",
                "score_venue_compatibility",
            },
        ),
        (
            create_itinerary_server,
            {"build_feasible_itinerary", "optimize_itinerary"},
        ),
    ],
)
def test_server_factories_expose_contract_tools(factory, expected_tools):
    server = factory()

    assert set(server._tool_manager._tools) == expected_tools


def test_server_factories_return_mcp_server_instances():
    servers = (
        create_user_state_server(),
        create_logistics_server(),
        create_profiler_server(),
        create_itinerary_server(),
    )

    assert all(server.name for server in servers)
    assert inspect.iscoroutinefunction(servers[0].list_tools)


def test_create_server_selects_named_transport():
    assert create_server("user-state").name == "tourism-user-state"
    assert create_server("logistics").name == "tourism-logistics"

    with pytest.raises(ValueError, match="Unknown server"):
        create_server("unknown")
