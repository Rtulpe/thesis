from __future__ import annotations

import asyncio
import json
import sys
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
        from contextlib import AsyncExitStack

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
