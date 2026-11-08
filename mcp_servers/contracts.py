from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolContract:
    name: str
    function: Callable[..., Any]


class ToolRegistry:
    """Small dependency-free registry used by the server adapters."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolContract] = {}

    def register(self, function: Callable[..., Any]) -> Callable[..., Any]:
        contract = ToolContract(function.__name__, function)
        if contract.name in self._tools:
            raise ValueError(f"Tool already registered: {contract.name}")
        self._tools[contract.name] = contract
        return function

    @property
    def tools(self) -> dict[str, ToolContract]:
        return dict(self._tools)


def create_registry(*functions: Callable[..., Any]) -> ToolRegistry:
    registry = ToolRegistry()
    for function in functions:
        registry.register(function)
    return registry
