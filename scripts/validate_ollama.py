from __future__ import annotations

import argparse
import asyncio
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any

from agent.llm_client import OllamaClient
from agent.mcp_client import MultiServerMCPClient
from agent.orchestrator import DynamicToolOrchestrator


@dataclass(frozen=True)
class LiveValidationReport:
    status: str
    model: str
    reason: str
    tool_calls: int
    response: str


def model_is_available(models: list[dict[str, Any]], model: str) -> bool:
    return any(item.get("name") == model for item in models)


def _list_models(base_url: str) -> list[dict[str, Any]]:
    request = urllib.request.Request(f"{base_url.rstrip('/')}/api/tags")
    with urllib.request.urlopen(request, timeout=5) as response:
        body = json.loads(response.read())
    models = body.get("models")
    if not isinstance(models, list):
        raise RuntimeError("Ollama model listing is malformed")
    return models


def report_to_json(report: LiveValidationReport) -> str:
    return json.dumps(asdict(report), indent=2)


async def validate_live(
    *,
    base_url: str,
    model: str,
    prompt: str,
    timeout_seconds: float = 180.0,
) -> LiveValidationReport:
    try:
        models = _list_models(base_url)
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return LiveValidationReport(
            "skipped",
            model,
            f"Ollama unavailable: {error}",
            0,
            "",
        )
    if not model_is_available(models, model):
        return LiveValidationReport(
            "skipped",
            model,
            f"Model is not installed: {model}",
            0,
            "",
        )

    try:
        async with MultiServerMCPClient() as tools:
            result = await asyncio.wait_for(
                DynamicToolOrchestrator(
                    tools,
                    OllamaClient(base_url=base_url, model=model),
                    max_rounds=4,
                ).run_async(prompt),
                timeout=timeout_seconds,
            )
        return LiveValidationReport(
            "passed",
            model,
            "Live MCP tool-calling validation completed",
            len(result["tool_results"]),
            result["response"],
        )
    except Exception as error:
        return LiveValidationReport(
            "failed",
            model,
            f"Live validation failed: {error}",
            0,
            "",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate live Ollama MCP tool calling")
    parser.add_argument("--base-url", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen3.5:4b"))
    parser.add_argument(
        "--prompt",
        default="Use one appropriate MCP tool to find museums in Amsterdam, then give a concise answer.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    args = parser.parse_args()

    report = asyncio.run(
        validate_live(
            base_url=args.base_url,
            model=args.model,
            prompt=args.prompt,
            timeout_seconds=args.timeout_seconds,
        )
    )
    print(report_to_json(report))
    if report.status == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
