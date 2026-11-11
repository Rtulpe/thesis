from evaluation.thesis_fixtures import build_thesis_scenarios


def test_thesis_scenarios_are_reproducible_and_cover_failure_case():
    first = build_thesis_scenarios(seed=7, repetitions=2)
    second = build_thesis_scenarios(seed=7, repetitions=2)

    assert first == second
    assert len(first) == 8
    assert any(
        "NO_FEASIBLE_ITINERARY" in scenario["expected_violation_codes"]
        for scenario in first
    )


def test_thesis_scenarios_reject_invalid_repetitions():
    try:
        build_thesis_scenarios(repetitions=0)
    except ValueError as error:
        assert "repetitions" in str(error)
    else:
        raise AssertionError("Expected repetitions validation")
