import json

from scripts.validate_ollama import (
    LiveValidationReport,
    model_is_available,
    report_to_json,
)


def test_model_is_available_matches_ollama_model_listing():
    assert model_is_available(
        [{"name": "qwen3.5:4b"}],
        "qwen3.5:4b",
    )
    assert not model_is_available(
        [{"name": "qwen3.5:2b"}],
        "qwen3.5:4b",
    )


def test_validation_report_is_machine_readable():
    report = LiveValidationReport(
        status="skipped",
        model="qwen3.5:4b",
        reason="Ollama unavailable",
        tool_calls=0,
        response="",
    )

    encoded = report_to_json(report)

    assert json.loads(encoded)["status"] == "skipped"
    assert json.loads(encoded)["model"] == "qwen3.5:4b"
