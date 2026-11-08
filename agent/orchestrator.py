from __future__ import annotations

from typing import Any, Protocol

import json
import inspect
from dataclasses import dataclass

from .llm_client import LLMClient, ToolCallingLLMClient
from .prompts import ANSWER_PROMPT_TEMPLATE, SYSTEM_PROMPT

class TravelTools(Protocol):
    def get_user_profile(self, user_id: str) -> dict[str, Any]: ...

    def get_user_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]: ...

    def get_city_venues(
        self,
        city: str,
        category_filter: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...

    def score_venue_compatibility(
        self,
        user_text_or_id: str,
        candidate_venue_ids: list[str],
    ) -> list[dict[str, Any]]: ...

    def build_feasible_itinerary(
        self,
        candidate_venue_ids: list[str],
        start_time: str,
        end_time: str,
        dwell_time_minutes: int = 90,
        start_location: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


class TravelOrchestrator:
    def __init__(
        self,
        tools: TravelTools,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._tools = tools
        self._llm_client = llm_client

    def answer(self, **kwargs: Any) -> dict[str, Any]:
        if self._llm_client is None:
            raise RuntimeError("An LLM client is required to generate an answer")
        plan = self.plan(**kwargs)
        prompt = ANSWER_PROMPT_TEMPLATE.format(
            city=plan["explanation"]["city"],
            user_state=plan["explanation"]["user_state"],
            itinerary=plan,
        )
        return {**plan, "response": self._llm_client.complete(SYSTEM_PROMPT, prompt)}

    def plan(
        self,
        user_id: str,
        city: str,
        start_time: str,
        end_time: str,
        *,
        preference_text: str | None = None,
        category_filter: str | None = None,
        candidate_limit: int = 50,
        dwell_time_minutes: int = 90,
        start_location: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not user_id or not user_id.strip():
            raise ValueError("user_id must not be empty")
        if not city or not city.strip():
            raise ValueError("city must not be empty")
        if candidate_limit <= 0:
            raise ValueError("candidate_limit must be greater than zero")

        profile = self._tools.get_user_profile(user_id)
        history = self._tools.get_user_history(user_id)
        has_history = bool(history) and profile.get("review_count", 0) > 0
        user_state = "history" if has_history else "cold_start"
        preference_source = user_id if has_history else preference_text
        if not preference_source:
            raise ValueError(
                "preference_text is required for users without interaction history"
            )

        venues = self._tools.get_city_venues(
            city,
            category_filter=category_filter,
            limit=candidate_limit,
        )
        candidate_ids = [venue["venue_id"] for venue in venues]
        if not candidate_ids:
            raise ValueError(f"No venues found in city: {city}")

        ranked = self._tools.score_venue_compatibility(
            preference_source,
            candidate_ids,
        )
        ranked_ids = [candidate["venue_id"] for candidate in ranked]
        itinerary = self._tools.build_feasible_itinerary(
            ranked_ids,
            start_time=start_time,
            end_time=end_time,
            dwell_time_minutes=dwell_time_minutes,
            start_location=start_location,
        )
        scores = {item["venue_id"]: item["score"] for item in ranked}
        return {
            **itinerary,
            "explanation": {
                "user_state": user_state,
                "city": city,
                "candidate_count": len(candidate_ids),
                "compatibility_scores": scores,
                "selected_venues": [
                    {
                        "venue_id": stop["venue_id"],
                        "compatibility_score": scores.get(stop["venue_id"]),
                        "constraint_evidence": {
                            "arrival_time": stop.get("arrival_time"),
                            "departure_time": stop.get("departure_time"),
                            "binding_reason": stop.get("binding_reason"),
                        },
                    }
                    for stop in itinerary.get("schedule", [])
                ],
            },
        }


@dataclass(frozen=True)
class DynamicToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


class DynamicToolOrchestrator:
    def __init__(
        self,
        tools: Any,
        llm_client: ToolCallingLLMClient,
        *,
        max_rounds: int = 8,
    ) -> None:
        if max_rounds <= 0:
            raise ValueError("max_rounds must be greater than zero")
        self._tools = tools
        self._llm_client = llm_client
        self._max_rounds = max_rounds

    def _tool_schemas(self) -> list[dict[str, Any]]:
        schemas = []
        for name, function in inspect.getmembers(self._tools, predicate=callable):
            if name.startswith("_"):
                continue
            signature = inspect.signature(function)
            properties = {}
            required = []
            for parameter_name, parameter in signature.parameters.items():
                if parameter.kind in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                ):
                    continue
                annotation = parameter.annotation
                properties[parameter_name] = {
                    "type": "string" if annotation is str else "object"
                }
                if parameter.default is inspect.Parameter.empty:
                    required.append(parameter_name)
            schemas.append(
                {
                    "name": name,
                    "description": inspect.getdoc(function) or f"Call {name}",
                    "input_schema": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                }
            )
        return schemas

    def run(self, user_prompt: str) -> dict[str, Any]:
        if not user_prompt or not user_prompt.strip():
            raise ValueError("user_prompt must not be empty")
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_prompt.strip()}
        ]
        schemas = self._tool_schemas()
        available = {schema["name"] for schema in schemas}
        tool_results = []
        for _ in range(self._max_rounds):
            response = self._llm_client.complete_with_tools(
                SYSTEM_PROMPT,
                messages,
                schemas,
            )
            tool_calls = response.get("tool_calls", [])
            if not tool_calls:
                content = response.get("content")
                if not isinstance(content, str) or not content.strip():
                    raise RuntimeError("LLM response did not contain a final answer")
                return {"response": content.strip(), "tool_results": tool_results}
            messages.append({"role": "assistant", "tool_calls": tool_calls})
            for raw_call in tool_calls:
                call = DynamicToolCall(
                    id=raw_call["id"],
                    name=raw_call["name"],
                    arguments=raw_call.get("arguments", {}),
                )
                if call.name not in available:
                    raise ValueError(f"Unknown tool: {call.name}")
                function = getattr(self._tools, call.name)
                try:
                    result = function(**call.arguments)
                except TypeError as error:
                    raise ValueError(
                        f"Invalid arguments for tool {call.name}: {error}"
                    ) from error
                tool_results.append(
                    {"id": call.id, "name": call.name, "result": result}
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, default=str),
                    }
                )
        raise RuntimeError("Reached maximum dynamic tool-calling rounds")

    async def run_async(self, user_prompt: str) -> dict[str, Any]:
        if not user_prompt or not user_prompt.strip():
            raise ValueError("user_prompt must not be empty")
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_prompt.strip()}
        ]
        schemas = await self._tools.schemas()
        available = {schema["name"] for schema in schemas}
        tool_results = []
        for _ in range(self._max_rounds):
            response = self._llm_client.complete_with_tools(
                SYSTEM_PROMPT,
                messages,
                schemas,
            )
            tool_calls = response.get("tool_calls", [])
            if not tool_calls:
                content = response.get("content")
                if not isinstance(content, str) or not content.strip():
                    raise RuntimeError("LLM response did not contain a final answer")
                return {"response": content.strip(), "tool_results": tool_results}
            messages.append({"role": "assistant", "tool_calls": tool_calls})
            for raw_call in tool_calls:
                call = DynamicToolCall(
                    id=raw_call["id"],
                    name=raw_call["name"],
                    arguments=raw_call.get("arguments", {}),
                )
                if call.name not in available:
                    raise ValueError(f"Unknown MCP tool: {call.name}")
                result = await self._tools.call(call.name, call.arguments)
                tool_results.append(
                    {"id": call.id, "name": call.name, "result": result}
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, default=str),
                    }
                )
        raise RuntimeError("Reached maximum dynamic tool-calling rounds")
