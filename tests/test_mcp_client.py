import asyncio

import pytest

from agent.mcp_client import MCPToolBridge, server_parameters


class FakeTool:
    def __init__(self, name):
        self.name = name
        self.inputSchema = {"type": "object", "properties": {}}
        self.description = f"Call {name}"


class FakeToolResult:
    def __init__(self, value):
        self.structuredContent = value
        self.isError = False


class FakeSession:
    async def list_tools(self):
        class Result:
            tools = [FakeTool("get_city_venues")]

        return Result()

    async def call_tool(self, name, arguments):
        assert name == "get_city_venues"
        return FakeToolResult({"venues": arguments})


def test_mcp_tool_bridge_discovers_and_calls_tools():
    bridge = MCPToolBridge(FakeSession())

    async def exercise():
        schemas = await bridge.schemas()
        result = await bridge.call("get_city_venues", {"city": "Amsterdam"})
        return schemas, result

    schemas, result = asyncio.run(exercise())

    assert schemas[0]["name"] == "get_city_venues"
    assert result == {"venues": {"city": "Amsterdam"}}


def test_mcp_tool_bridge_rejects_unknown_tool():
    bridge = MCPToolBridge(FakeSession())

    async def exercise():
        with pytest.raises(ValueError, match="Unknown MCP tool"):
            await bridge.call("missing", {})

    asyncio.run(exercise())


def test_server_parameters_use_project_mcp_stdio_dispatcher():
    parameters = server_parameters("logistics")

    assert parameters.command.endswith("/.venv/bin/python")
    assert parameters.args[-3:] == ["-m", "mcp_servers.mcp_transport", "logistics"]
    assert parameters.cwd.name == "thesis"
