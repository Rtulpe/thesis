import json
from urllib.request import Request

from agent.llm_client import OllamaClient


def test_ollama_client_builds_chat_request(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return json.dumps({"message": {"content": "A useful itinerary."}}).encode()

        return Response()

    monkeypatch.setattr("agent.llm_client.urlopen", fake_urlopen)
    client = OllamaClient(base_url="http://localhost:11434", model="llama3.2")

    response = client.complete("system prompt", "plan my trip")

    assert response == "A useful itinerary."
    request = captured["request"]
    assert isinstance(request, Request)
    assert request.full_url == "http://localhost:11434/api/chat"
    assert json.loads(request.data) == {
        "model": "llama3.2",
        "messages": [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "plan my trip"},
        ],
        "stream": False,
    }


def test_ollama_client_rejects_malformed_response(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b"{}"

    monkeypatch.setattr("agent.llm_client.urlopen", lambda request, timeout: Response())

    try:
        OllamaClient().complete("system", "user")
    except RuntimeError as error:
        assert "response" in str(error)
    else:
        raise AssertionError("Expected malformed Ollama response to fail")


def test_ollama_client_normalizes_tool_calls(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "get_city_venues",
                                    "arguments": {"city": "Amsterdam"},
                                }
                            }
                        ]
                    }
                }
            ).encode()

    monkeypatch.setattr("agent.llm_client.urlopen", lambda request, timeout: Response())
    response = OllamaClient().complete_with_tools(
        "system",
        [{"role": "user", "content": "Find Amsterdam venues"}],
        [
            {
                "name": "get_city_venues",
                "description": "Find venues",
                "input_schema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            }
        ],
    )

    assert response["tool_calls"][0]["name"] == "get_city_venues"
    assert response["tool_calls"][0]["arguments"] == {"city": "Amsterdam"}
