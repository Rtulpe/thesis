import asyncio

import pytest

from agent.mcp_client import MultiServerMCPClient


class FakeBridge:
    def __init__(self, server_name, tools, events):
        self.server_name = server_name
        self.tools = tools
        self.events = events

    async def schemas(self):
        self.events.append(("schemas", self.server_name))
        return [
            {
                "name": name,
                "description": f"{self.server_name} {name}",
                "input_schema": {"type": "object"},
            }
            for name in self.tools
        ]

    async def call(self, name, arguments):
        self.events.append(("call", self.server_name, name, arguments))
        return {"server": self.server_name, "arguments": arguments}


class FakeSession:
    def __init__(self, bridge, events):
        self.bridge = bridge
        self.events = events

    async def __aenter__(self):
        self.events.append(("enter", self.bridge.server_name))
        return self.bridge

    async def __aexit__(self, *args):
        self.events.append(("exit", self.bridge.server_name))


def test_multi_server_client_discovers_namespaced_tools_and_calls_them(monkeypatch):
    events = []
    bridges = {
        "user-state": FakeBridge("user-state", ["get_user_profile"], events),
        "logistics": FakeBridge("logistics", ["get_city_venues"], events),
        "profiler": FakeBridge("profiler", ["score_venue_compatibility"], events),
        "itinerary": FakeBridge(
            "itinerary",
            ["build_feasible_itinerary"],
            events,
        ),
    }

    def fake_factory(name):
        return FakeSession(bridges[name], events)

    monkeypatch.setattr("agent.mcp_client.MCPClientSession", fake_factory)

    async def exercise():
        async with MultiServerMCPClient() as client:
            schemas = await client.schemas()
            result = await client.call(
                "logistics.get_city_venues",
                {"city": "Amsterdam"},
            )
            return schemas, result

    schemas, result = asyncio.run(exercise())

    assert {schema["name"] for schema in schemas} == {
        "user-state.get_user_profile",
        "logistics.get_city_venues",
        "profiler.score_venue_compatibility",
        "itinerary.build_feasible_itinerary",
    }
    assert result["server"] == "logistics"
    assert all(("exit", name) in events for name in bridges)


def test_multi_server_client_rejects_unknown_namespaced_tool():
    async def exercise():
        client = MultiServerMCPClient()
        with pytest.raises(ValueError, match="Unknown MCP tool"):
            await client.call("missing.tool", {})

    asyncio.run(exercise())
