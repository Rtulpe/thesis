from __future__ import annotations

import json
import os
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMClient(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str: ...


class ToolCallingLLMClient(LLMClient, Protocol):
    def complete_with_tools(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]: ...


class OllamaClient:
    """Small Ollama chat client using the local HTTP API."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.timeout = timeout
        if not self.model.strip():
            raise ValueError("model must not be empty")

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self._request(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        content = response.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Ollama response did not contain message content")
        return content.strip()

    def complete_with_tools(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ollama_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
            for tool in tools
        ]
        response = self._request(
            [{"role": "system", "content": system_prompt}, *messages],
            tools=ollama_tools,
        )
        message = response.get("message", {})
        normalized: dict[str, Any] = {}
        if isinstance(message.get("content"), str) and message["content"].strip():
            normalized["content"] = message["content"].strip()
        raw_tool_calls = message.get("tool_calls", [])
        if raw_tool_calls:
            normalized["tool_calls"] = [
                {
                    "id": f"ollama-call-{index}",
                    "name": call["function"]["name"],
                    "arguments": call["function"].get("arguments", {}),
                }
                for index, call in enumerate(raw_tool_calls, start=1)
            ]
        return normalized

    def _request(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body: Any = json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Ollama request failed: {error}") from error
        return body
