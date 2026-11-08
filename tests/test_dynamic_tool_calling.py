import pytest

from agent.orchestrator import DynamicToolOrchestrator


class FakeToolLLM:
    def __init__(self):
        self.calls = []

    def complete_with_tools(self, system_prompt, messages, tools):
        self.calls.append((system_prompt, messages, tools))
        if len(self.calls) == 1:
            return {
                "tool_calls": [
                    {
                        "id": "call-1",
                        "name": "get_city_venues",
                        "arguments": {"city": "Amsterdam", "limit": 5},
                    }
                ]
            }
        return {"content": "I found suitable venues in Amsterdam."}


class FakeTools:
    def get_city_venues(self, city, category_filter=None, limit=50):
        return [{"venue_id": "venue_museum", "city": city}]


def test_dynamic_orchestrator_executes_tool_and_returns_final_answer():
    llm = FakeToolLLM()
    result = DynamicToolOrchestrator(FakeTools(), llm).run(
        "Find venues in Amsterdam"
    )

    assert result["response"] == "I found suitable venues in Amsterdam."
    assert result["tool_results"][0]["name"] == "get_city_venues"
    assert result["tool_results"][0]["result"][0]["city"] == "Amsterdam"
    assert len(llm.calls[0][2]) == 1
    assert llm.calls[0][2][0]["name"] == "get_city_venues"


def test_dynamic_orchestrator_rejects_unknown_tools():
    class UnknownToolLLM:
        def complete_with_tools(self, system_prompt, messages, tools):
            return {
                "tool_calls": [
                    {"id": "call-1", "name": "unknown", "arguments": {}}
                ]
            }

    with pytest.raises(ValueError, match="Unknown tool"):
        DynamicToolOrchestrator(FakeTools(), UnknownToolLLM()).run("Do something")


def test_dynamic_orchestrator_has_a_call_limit():
    class EndlessLLM:
        def complete_with_tools(self, system_prompt, messages, tools):
            return {
                "tool_calls": [
                    {
                        "id": "call",
                        "name": "get_city_venues",
                        "arguments": {"city": "Amsterdam"},
                    }
                ]
            }

    with pytest.raises(RuntimeError, match="maximum"):
        DynamicToolOrchestrator(
            FakeTools(),
            EndlessLLM(),
            max_rounds=2,
        ).run("Loop forever")


def test_dynamic_orchestrator_can_run_against_async_mcp_bridge():
    class AsyncLLM:
        def complete_with_tools(self, system_prompt, messages, tools):
            if len(messages) == 1:
                return {
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "name": "get_city_venues",
                            "arguments": {"city": "Amsterdam"},
                        }
                    ]
                }
            return {"content": "MCP-backed answer"}

    class AsyncBridge:
        async def schemas(self):
            return [
                {
                    "name": "get_city_venues",
                    "description": "Find venues",
                    "input_schema": {"type": "object"},
                }
            ]

        async def call(self, name, arguments):
            return [{"venue_id": "venue_museum", "city": arguments["city"]}]

    async def exercise():
        return await DynamicToolOrchestrator(
            AsyncBridge(),
            AsyncLLM(),
        ).run_async("Find Amsterdam venues")

    import asyncio

    result = asyncio.run(exercise())
    assert result["response"] == "MCP-backed answer"
    assert result["tool_results"][0]["name"] == "get_city_venues"
