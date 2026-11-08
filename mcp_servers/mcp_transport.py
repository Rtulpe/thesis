"""MCP transport adapters for the domain tool modules."""

from __future__ import annotations

import argparse
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from . import itinerary_server, logistics_server, profiler_server, user_state_server


def create_user_state_server() -> FastMCP:
    server = FastMCP("tourism-user-state")
    server.tool()(user_state_server.get_user_profile)
    server.tool()(user_state_server.get_user_history)
    server.tool()(user_state_server.record_interaction)
    return server


def create_logistics_server() -> FastMCP:
    server = FastMCP("tourism-logistics")
    server.tool()(logistics_server.get_city_venues)
    server.tool()(logistics_server.calculate_travel_matrix)
    server.tool()(logistics_server.check_venue_open_status)
    return server


def create_profiler_server() -> FastMCP:
    server = FastMCP("tourism-profiler")
    server.tool()(profiler_server.extract_text_vibe)
    server.tool()(profiler_server.get_visitor_profile)
    server.tool()(profiler_server.score_venue_compatibility)
    return server


def create_itinerary_server() -> FastMCP:
    server = FastMCP("tourism-itinerary")
    server.tool()(itinerary_server.build_feasible_itinerary)
    return server


SERVER_FACTORIES: dict[str, Callable[[], FastMCP]] = {
    "user-state": create_user_state_server,
    "logistics": create_logistics_server,
    "profiler": create_profiler_server,
    "itinerary": create_itinerary_server,
}


def create_server(server_name: str) -> FastMCP:
    try:
        factory = SERVER_FACTORIES[server_name]
    except KeyError:
        available = ", ".join(sorted(SERVER_FACTORIES))
        raise ValueError(
            f"Unknown server: {server_name}. Available servers: {available}"
        ) from None
    return factory()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a tourism MCP server over stdio")
    parser.add_argument("server", choices=sorted(SERVER_FACTORIES))
    args = parser.parse_args()
    create_server(args.server).run(transport="stdio")


if __name__ == "__main__":
    main()
