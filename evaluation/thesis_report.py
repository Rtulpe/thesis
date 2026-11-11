"""Reproducible thesis validation and reporting helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ablation import ConfigurationRunner, run_ablation
from .thesis_fixtures import build_thesis_scenarios


def run_thesis_validation(
    runners: dict[str, ConfigurationRunner],
    *,
    seed: int = 42,
    repetitions: int = 1,
) -> dict[str, Any]:
    scenarios = build_thesis_scenarios(seed=seed, repetitions=repetitions)
    report = run_ablation(scenarios, runners)
    return {
        "experiment": "neuro-symbolic-tourism-ablation",
        "seed": seed,
        "repetitions": repetitions,
        "report": report,
    }


def write_thesis_report(
    validation: dict[str, Any],
    json_path: str | Path,
    summary_path: str | Path,
) -> None:
    json_target = Path(json_path)
    summary_target = Path(summary_path)
    json_target.parent.mkdir(parents=True, exist_ok=True)
    summary_target.parent.mkdir(parents=True, exist_ok=True)
    json_target.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n")
    configurations = validation["report"]["configurations"]
    lines = [
        "Neuro-symbolic tourism ablation",
        f"Scenarios: {validation['report']['scenario_count']}",
    ]
    for name, result in configurations.items():
        lines.append(
            (
                f"{name}: validity={result['itinerary_validity_rate']:.3f}, "
                f"preference={result['cumulative_preference_score']:.3f}, "
                f"travel_time={result['mean_travel_time']:.3f}, "
                f"travel_distance={result['mean_travel_distance']:.3f}"
            )
        )
    summary_target.write_text("\n".join(lines) + "\n")
