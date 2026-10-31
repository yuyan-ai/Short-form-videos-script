import json
import httpx
import pytest
from short_video_agent.config import ModelConfig
from short_video_agent.models.live import LiveModel
from short_video_agent.runtime import run, make_draft, search
from test_graph_mock import request


def execute(review, max_steps=10):
    draft = make_draft(search("字幕", "qingjian")[0], 1)
    draft.pop("revision")
    draft["title"] = "新手也来检查字幕吧"
    actions = iter([
        {"name": "search_materials", "query": "字幕", "reason": "取得事实"},
        {"name": "save_draft", "draft": draft, "reason": "面向新手创作标题"},
        {"name": "estimate_duration", "reason": "估时"},
        {"name": "check_rules", "reason": "审核"},
        {"name": "finish", "reason": "提交"},
        {"name": "fail", "reason": "审核未通过"},
    ])
    calls = []
    def handler(req):
        payload = json.loads(req.content)
        calls.append(payload)
        result = review if "审核员" in payload["messages"][0]["content"] else next(actions)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(result)}}]})
    model = LiveModel(ModelConfig("test", "https://example.test/v1", "test"), httpx.MockTransport(handler))
    return run(request("normal"), model=model, max_steps=max_steps), calls


def test_original_copy_review_and_budget_count():
    state, calls = execute({"passed": True, "issues": []})
    assert state["status"] == "completed"
    assert len(calls) == state["steps"] == 6
    assert state["checks"]["copy_review"]["passed"]
    assert any(e["action"] == "review_copy" for e in state["trace"])


@pytest.mark.parametrize("review", [
    {"passed": False, "issues": ["标题未响应受众要求"]},
    {"passed": True, "issues": ["自相矛盾"]},
    {"unexpected": True},
])
def test_review_rejection_and_invalid_output_block_finish(review):
    state, _ = execute(review)
    assert state["status"] == "failed"
    assert not state["checks"]["passed"]
    assert any("error" in e["observation"] for e in state["trace"] if e["action"] == "finish")


def test_review_cannot_overrun_budget():
    state, calls = execute({"passed": True, "issues": []}, max_steps=4)
    assert state["status"] == "budget_exceeded"
    assert len(calls) == 4


def test_imported_draft_is_reestimated_and_revised():
    draft = make_draft(search("字幕", "qingjian")[0], 1, True)
    draft.pop("revision")
    state = run(request("normal"), initial_draft=draft)
    assert state["status"] == "completed"
    assert state["trace"][0]["actor"] == "user"
    durations = [e["observation"]["total_seconds"] for e in state["trace"] if e["action"] == "estimate_duration"]
    assert state["trace"][0]["observation"]["initial_duration"]["total_seconds"] > 30 >= durations[-1]
    assert state["revision"] == 2
