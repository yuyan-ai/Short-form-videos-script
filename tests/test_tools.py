from short_video_agent.runtime import search, make_draft, check, ROOT
import json


def test_fabricated_claim_rejected():
    materials = search("字幕", "qingjian")
    draft = make_draft(materials[0], 1)
    draft["scenes"][1]["voiceover"] = "效率提升80%"
    rules = json.loads((ROOT / "data/brand_rules.json").read_text(encoding="utf-8"))
    assert not check(draft, materials, rules)["passed"]


def test_unknown_citation_rejected():
    materials = search("字幕", "qingjian")
    draft = make_draft(materials[0], 1)
    draft["scenes"][1]["claims"][0]["material_id"] = "FAKE"
    rules = json.loads((ROOT / "data/brand_rules.json").read_text(encoding="utf-8"))
    assert not check(draft, materials, rules)["passed"]
