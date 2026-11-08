from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from typing import Any

from agent.llm_client import OllamaClient
from agent.mcp_client import MultiServerMCPClient
from agent.orchestrator import DynamicToolOrchestrator, TravelOrchestrator
from mcp_servers import itinerary_server, logistics_server, profiler_server, user_state_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agentic tourism recommender")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--city", required=True)
    parser.add_argument("--start-time", required=True, type=_time_value)
    parser.add_argument("--end-time", required=True, type=_time_value)
    parser.add_argument("--preference", default=None)
    parser.add_argument("--category", default=None)
    parser.add_argument("--candidate-limit", type=int, default=50)
    parser.add_argument("--dwell-minutes", type=int, default=90)
    parser.add_argument("--llm", choices=("offline", "ollama"), default="offline")
    parser.add_argument("--ollama-model", default="qwen3.5:4b")
    parser.add_argument("--ollama-base-url", default="http://localhost:11434")
    return parser


def _time_value(value: str) -> str:
    try:
        hour, minute = value.split(":")
        if len(hour) != 2 or len(minute) != 2:
            raise ValueError
        if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
            raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError("time must use HH:MM in 24-hour format") from None
    return value


class _OfflineTools:
    @staticmethod
    def get_user_profile(user_id: str) -> dict[str, Any]:
        try:
            return user_state_server.get_user_profile(user_id)
        except ValueError as error:
            if str(error) != f"Unknown user: {user_id}":
                raise
            return {"user_id": user_id, "review_count": 0}

    @staticmethod
    def get_user_history(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        try:
            return user_state_server.get_user_history(user_id, limit)
        except ValueError as error:
            if str(error) != f"Unknown user: {user_id}":
                raise
            return []

    get_city_venues = staticmethod(logistics_server.get_city_venues)
    score_venue_compatibility = staticmethod(
        profiler_server.score_venue_compatibility
    )
    build_feasible_itinerary = staticmethod(
        itinerary_server.build_feasible_itinerary
    )


def ollama_available(base_url: str, model: str) -> bool:
    try:
        request = urllib.request.Request(f"{base_url.rstrip('/')}/api/tags")
        with urllib.request.urlopen(request, timeout=3) as response:
            models = json.loads(response.read()).get("models", [])
        return any(item.get("name") == model for item in models)
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


def run_cli(args: argparse.Namespace) -> dict[str, Any]:
    request = {
        "user_id": args.user_id,
        "city": args.city,
        "start_time": args.start_time,
        "end_time": args.end_time,
        "preference_text": args.preference,
        "category_filter": args.category,
        "candidate_limit": args.candidate_limit,
        "dwell_time_minutes": args.dwell_minutes,
    }
    if args.llm == "offline":
        result = TravelOrchestrator(_OfflineTools()).plan(**request)
        return {"mode": "offline", "fallback": False, "result": result}
    if not ollama_available(args.ollama_base_url, args.ollama_model):
        result = TravelOrchestrator(_OfflineTools()).plan(**request)
        return {
            "mode": "ollama",
            "fallback": True,
            "fallback_reason": "Ollama model unavailable",
            "result": result,
        }

    async def execute() -> dict[str, Any]:
        async with MultiServerMCPClient() as tools:
            result = await DynamicToolOrchestrator(
                tools,
                OllamaClient(
                    base_url=args.ollama_base_url,
                    model=args.ollama_model,
                ),
            ).run_async(args.preference or f"Plan a trip to {args.city}")
        return {"mode": "ollama", "fallback": False, "result": result}

    import asyncio

    return asyncio.run(execute())


def main() -> None:
    args = build_parser().parse_args()
    print(json.dumps(run_cli(args), indent=2, default=str))


if __name__ == "__main__":
    main()
