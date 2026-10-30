import copy
import json
import pytest
from short_video_agent.runtime import ROOT, run, search, make_draft, check, estimate, can_finish
from test_graph_mock import request


def fixtures():
    materials = search("字幕", "qingjian")
    draft = make_draft(materials[0], 1)
    rules = json.loads((ROOT / "data/brand_rules.json").read_text(encoding="utf-8"))
    return draft, materials, rules


def test_unrelated_citation():
    draft, materials, rules = fixtures()
    draft["scenes"][2]["claims"] = copy.deepcopy(draft["scenes"][1]["claims"])
    assert "IRRELEVANT_CITATION" in {i["code"] for i in check(draft, materials, rules)["issues"]}


def test_padding_rejected_even_within_target():
    draft, materials, rules = fixtures()
    draft["scenes"][1]["min_visual_seconds"] = 15
    assert estimate(draft)["total_seconds"] < 30
    assert "EXCESSIVE_PADDING" in {i["code"] for i in check(draft, materials, rules)["issues"]}


def test_repeated_copy():
    draft, materials, rules = fixtures()
    draft["scenes"][2]["voiceover"] = draft["scenes"][0]["voiceover"]
    assert "REPEATED_COPY" in {i["code"] for i in check(draft, materials, rules)["issues"]}


def test_subtitle_not_hidden_by_short_voiceover():
    draft, _, _ = fixtures()
    draft["scenes"][0]["subtitle"] = "字幕" * 60
    assert estimate(draft)["scenes"][0]["seconds"] >= 30


def test_rule_mutation_invalidates_report():
    state = run(request("normal"))
    assert can_finish(state)
    state["rules"]["version"] = "changed"
    assert not can_finish(state)


def test_material_mutation_invalidates_report():
    state = run(request("normal"))
    state["materials"][0]["facts"][0]["text"] = "changed"
    assert not can_finish(state)


def test_multi_keyword_search_and_no_metadata_matches():
    assert search("轻剪 字幕 功能 创作者", "qingjian")[0]["id"] == "P01"
    assert search("synthetic", "qingjian") == []
    assert search(" ", "qingjian") == []


@pytest.mark.parametrize("value", ["  ", None])
def test_invalid_topic(value):
    data = request("normal")
    data["topic"] = value
    assert run(data)["status"] == "needs_input"


def test_historical_bad_output_is_rejected():
    path = ROOT / "examples/runs/20261029-192730-6ac7b49b/result.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    _, materials, rules = fixtures()
    report = check(result["script"], materials, rules)
    assert not report["passed"]
    assert {"IRRELEVANT_CITATION", "REPEATED_COPY", "EXCESSIVE_PADDING"} <= {i["code"] for i in report["issues"]}


def test_export_displays_subtitles_and_rule_snapshot(tmp_path):
    from short_video_agent.export import export_run
    state = run(request("normal"))
    state["materials"] += search("竖屏", "qingjian")
    directory = tmp_path / "run"
    export_run(directory, state["request"], state)
    result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    assert result["sources"] == ["P01"]
    assert "字幕：" in (directory / "script.md").read_text(encoding="utf-8")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["rules"]["version"] == "2"
