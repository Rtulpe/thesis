import json

from agent.cli import build_parser, run_cli


def test_cli_defaults_to_offline_and_returns_json():
    parser = build_parser()
    args = parser.parse_args(
        [
            "--user-id",
            "new_user",
            "--city",
            "Amsterdam",
            "--start-time",
            "09:00",
            "--end-time",
            "18:00",
            "--preference",
            "history and culture",
        ]
    )

    output = run_cli(args)

    assert output["mode"] == "offline"
    assert output["result"]["status"] in {"feasible", "infeasible"}
    assert output["fallback"] is False


def test_cli_rejects_invalid_time_format():
    parser = build_parser()

    try:
        parser.parse_args(
            [
                "--user-id",
                "new_user",
                "--city",
                "Amsterdam",
                "--start-time",
                "bad",
                "--end-time",
                "18:00",
            ]
        )
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("Expected argparse to reject invalid time")


def test_cli_ollama_mode_reports_fallback_when_unavailable(monkeypatch):
    parser = build_parser()
    args = parser.parse_args(
        [
            "--user-id",
            "new_user",
            "--city",
            "Amsterdam",
            "--start-time",
            "09:00",
            "--end-time",
            "18:00",
            "--preference",
            "history",
            "--llm",
            "ollama",
        ]
    )
    monkeypatch.setattr("agent.cli.ollama_available", lambda *args: False)

    output = run_cli(args)

    assert output["mode"] == "ollama"
    assert output["fallback"] is True
    assert output["result"]["status"] in {"feasible", "infeasible"}
