import json
import httpx
import pytest
from pydantic import ValidationError
from short_video_agent.config import ModelConfig
from short_video_agent.models.live import LiveModel
from short_video_agent.runtime import run, make_draft, search
from short_video_agent.schemas import Action
from test_graph_mock import request


def adapter(actions):
    items = iter(actions)
    def handler(req):
        payload = json.loads(req.content)
        assert payload["model"] == "test-model"
        assert req.headers["Authorization"] == "Bearer secret-test"
        return httpx.Response(200, json={"choices":[{"message":{"content":json.dumps(next(items), ensure_ascii=False)}}]})
    return LiveModel(ModelConfig("secret-test", "https://example.test/v1", "test-model"), httpx.MockTransport(handler))


def action(name, **kwargs):
    return {"name":name, "reason":"测试公开依据", **kwargs}


def test_live_protocol_and_revision_loop():
    material = search("字幕", "qingjian")[0]
    long = make_draft(material, 1, True)
    short = make_draft(material, 2)
    long.pop("revision")
    short.pop("revision")
    model = adapter([action("search_materials", query="字幕"), action("save_draft", draft=long),
        action("estimate_duration"), action("save_draft", draft=short), action("estimate_duration"),
        action("finish"), action("check_rules"), action("finish")])
    state = run(request("normal"), model=model)
    assert state["status"] == "completed"
    assert state["revision"] == 2
    assert any("error" in e["observation"] for e in state["trace"])
    assert "secret-test" not in json.dumps(state)


def test_query_rewrite_after_empty_result():
    state = run(request("normal"), model=adapter([action("search_materials", query="不存在关键词"),
        action("search_materials", query="字幕"), action("request_info")]))
    assert state["trace"][0]["observation"]["count"] == 0
    assert state["trace"][1]["observation"]["count"] == 1


def test_invalid_model_output_consumes_budget():
    state = run(request("normal"), max_steps=2, model=adapter([{"name":"unknown"}, {"name":"unknown"}]))
    assert state["status"] == "budget_exceeded"
    assert len(state["trace"]) == 2


def test_http_error_body_not_exported():
    model = LiveModel(ModelConfig("secret-test", "https://example.test/v1", "test"),
        httpx.MockTransport(lambda req: httpx.Response(401, text="secret-test")))
    state = run(request("normal"), model=model)
    assert state["status"] == "failed"
    assert "secret-test" not in json.dumps(state)


def test_configuration_missing(monkeypatch, tmp_path):
    for key in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        ModelConfig.from_env(tmp_path / "missing.env")


def test_env_priority(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_API_KEY", "process-value")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    path = tmp_path / ".env"
    path.write_text("LLM_API_KEY=file-value\nLLM_BASE_URL=https://example.test/v1\nLLM_MODEL=test", encoding="utf-8")
    config = ModelConfig.from_env(path)
    assert config.api_key == "process-value"
    assert "process-value" not in repr(config)


def test_model_timeout():
    def handler(req):
        raise httpx.ReadTimeout("sensitive detail")
    state = run(request("normal"), model=LiveModel(ModelConfig("key", "https://example.test/v1", "test"), httpx.MockTransport(handler)))
    assert state["status"] == "failed"
    assert "sensitive detail" not in json.dumps(state)


def test_total_budget():
    state = run(request("normal"), model=adapter([]), total_seconds=0)
    assert state["status"] == "budget_exceeded"
