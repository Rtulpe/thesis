import json

from core.trace import ExecutionTrace


def test_execution_trace_sequences_events_and_writes_json(tmp_path):
    trace = ExecutionTrace()
    trace.record("tool_call", tool="logistics.calculate_travel_matrix")
    trace.record("tool_result", status="ok")

    output = tmp_path / "trace.json"
    trace.write_json(output)

    payload = json.loads(output.read_text())
    assert [event["sequence"] for event in payload["events"]] == [1, 2]
    assert payload["events"][0]["tool"] == "logistics.calculate_travel_matrix"
