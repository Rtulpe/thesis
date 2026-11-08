from __future__ import annotations

import asyncio
import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def server_parameters(server_name: str) -> StdioServerParameters:
    valid_servers = {"user-state", "logistics", "profiler", "itinerary"}
    if server_name not in valid_servers:
        raise ValueError(f"Unknown MCP server: {server_name}")
    python_path = PROJECT_ROOT / ".venv" / "bin" / "python"
    if not python_path.exists():
        python_path = Path(sys.executable)
    return StdioServerParameters(
        command=str(python_path),
        args=["-m", "mcp_servers.mcp_transport", server_name],
        cwd=PROJECT_ROOT,
    )


class MCPToolBridge:
    def __init__(self, session: ClientSession) -> None:
        self._session = session
        self._tool_names: set[str] | None = None

    async def schemas(self) -> list[dict[str, Any]]:
        result = await self._session.list_tools()
        schemas = []
        self._tool_names = set()
        for tool in result.tools:
            self._tool_names.add(tool.name)
            schemas.append(
                {
                    "name": tool.name,
                    "description": tool.description or f"Call {tool.name}",
                    "input_schema": tool.inputSchema,
                }
            )
        return schemas

    async def call(self, name: str, arguments: dict[str, Any]) -> Any:
        if self._tool_names is None:
            await self.schemas()
        if name not in self._tool_names:
            raise ValueError(f"Unknown MCP tool: {name}")
        result = await self._session.call_tool(name, arguments)
        if result.isError:
            raise RuntimeError(f"MCP tool failed: {name}")
        if result.structuredContent is not None:
            return result.structuredContent
        text_content = [
            item.text
            for item in result.content
            if getattr(item, "type", None) == "text"
        ]
        if len(text_content) == 1:
            try:
                return json.loads(text_content[0])
            except json.JSONDecodeError:
                return text_content[0]
        return text_content


class MCPClientSession:
    def __init__(self, server_name: str) -> None:
        self._parameters = server_parameters(server_name)
        self._exit_stack = None
        self.bridge: MCPToolBridge | None = None

    async def __aenter__(self) -> MCPToolBridge:
        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(self._parameters)
        )
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()
        self.bridge = MCPToolBridge(session)
        await self.bridge.schemas()
        return self.bridge

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self._exit_stack is not None:
            await self._exit_stack.__aexit__(exc_type, exc_value, traceback)


class MultiServerMCPClient:
    SERVER_NAMES = ("user-state", "logistics", "profiler", "itinerary")

    def __init__(self, server_names: tuple[str, ...] | None = None) -> None:
        self._server_names = server_names or self.SERVER_NAMES
        invalid = set(self._server_names) - set(self.SERVER_NAMES)
        if invalid:
            raise ValueError(f"Unknown MCP servers: {', '.join(sorted(invalid))}")
        self._exit_stack: AsyncExitStack | None = None
        self._bridges: dict[str, MCPToolBridge] = {}
        self._tools: dict[str, tuple[str, str]] = {}

    async def __aenter__(self) -> "MultiServerMCPClient":
        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()
        try:
            for name in self._server_names:
                self._bridges[name] = await self._exit_stack.enter_async_context(
                    MCPClientSession(name)
                )
            await self.schemas()
            return self
        except BaseException:
            await self._exit_stack.__aexit__(*sys.exc_info())
            self._exit_stack = None
            raise

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self._exit_stack is not None:
            await self._exit_stack.__aexit__(exc_type, exc_value, traceback)
            self._exit_stack = None
            self._bridges.clear()
            self._tools.clear()

    async def schemas(self) -> list[dict[str, Any]]:
        discovered = await asyncio.gather(
            *(self._bridges[name].schemas() for name in self._server_names)
        )
        schemas: list[dict[str, Any]] = []
        self._tools.clear()
        for server_name, server_schemas in zip(self._server_names, discovered):
            for schema in server_schemas:
                namespaced_name = f"{server_name}.{schema['name']}"
                self._tools[namespaced_name] = (server_name, schema["name"])
                schemas.append({**schema, "name": namespaced_name})
        return schemas

    async def call(self, name: str, arguments: dict[str, Any]) -> Any:
        try:
            server_name, tool_name = self._tools[name]
        except KeyError:
            raise ValueError(f"Unknown MCP tool: {name}") from None
        return await self._bridges[server_name].call(tool_name, arguments)
