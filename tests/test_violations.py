from core.violations import Violation


def test_violation_serialization_preserves_machine_readable_fields():
    assert Violation(
        "TRAVEL_BUDGET_EXCEEDED",
        "Too far",
        venue_id="v1",
        details={"actual": 12},
    ).as_dict() == {
        "code": "TRAVEL_BUDGET_EXCEEDED",
        "message": "Too far",
        "venue_id": "v1",
        "details": {"actual": 12},
    }
