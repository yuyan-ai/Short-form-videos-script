import json
import pytest
from short_video_agent.runtime import ROOT, run


def request(name):
    return json.loads((ROOT / f"examples/inputs/{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name,status", [("normal","completed"),("overlong","completed"),("no_material","needs_input"),("missing_info","needs_input"),("tool_failure","failed")])
def test_paths(name, status):
    assert run(request(name))["status"] == status


def test_revision_rechecked():
    state = run(request("overlong"))
    durations = [e["observation"]["total_seconds"] for e in state["trace"] if e["action"] == "estimate_duration"]
    assert durations[0] > 30 >= durations[1]
    assert state["checks"]["draft_hash"] == state["duration"]["draft_hash"]


def test_budget():
    assert run(request("normal"), max_steps=1)["status"] == "budget_exceeded"


def test_impossible_duration():
    value = request("normal")
    value["target_seconds"] = 1
    assert run(value)["status"] == "failed"
