"""离线原型：真实工具配合确定性 Mock 决策，不代表 LLM 能力。"""
import hashlib
import json
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field, ValidationError

ROOT = Path(__file__).resolve().parents[2]


class Request(BaseModel):
    topic: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    target_seconds: float = Field(gt=0, le=300)
    style: str = "清晰自然"
    product_id: str = "qingjian"
    query: str = "字幕"
    demo_scenario: str = "normal"


class State(TypedDict, total=False):
    request: dict
    materials: list
    rules: dict
    draft: dict
    duration: dict
    checks: dict
    trace: list
    action: dict
    status: str
    reason: str
    steps: int
    max_steps: int
    searched: bool
    revision: int


def fingerprint(draft):
    return hashlib.sha256(json.dumps(draft, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def search(query, product_id):
    records = json.loads((ROOT / "data/materials.json").read_text(encoding="utf-8-sig"))
    return [m for m in records if m["product_id"] == product_id
            and query in json.dumps(m, ensure_ascii=False)]


def estimate(draft):
    scenes = []
    for scene in draft["scenes"]:
        text = scene["voiceover"] or scene["subtitle"]
        count = sum(c.isalnum() for c in text)
        seconds = round(max(count / 4, scene["min_visual_seconds"]) + 0.5, 2)
        scenes.append({"scene_id": scene["scene_id"], "seconds": seconds})
    return {"draft_hash": fingerprint(draft), "scenes": scenes,
            "total_seconds": round(sum(s["seconds"] for s in scenes), 2),
            "method": "每秒4个字/字符，逐镜取最低画面时长与朗读时长较大值，加0.5秒停顿；仅为估算"}


def check(draft, materials, rules):
    allowed = {f["id"]: f["text"] for m in materials for f in m["facts"]}
    issues = []
    # 原型严格限制所有用户可见文本为审核过的素材表达或中性模板。
    neutral = rules["neutral_texts"]
    for field, text in [("title", draft["title"])]:
        if text not in neutral:
            issues.append({"field": field, "code": "UNAPPROVED_TEXT"})
    for scene in draft["scenes"]:
        for field in ("visual", "voiceover", "subtitle"):
            text = scene[field]
            if text and text not in neutral and text not in allowed.values():
                issues.append({"scene_id": scene["scene_id"], "field": field, "code": "UNAPPROVED_TEXT"})
        claims = scene["claims"]
        for claim in claims:
            if allowed.get(claim["fact_id"]) != claim["text"] or not any(
                m["id"] == claim["material_id"] and any(f["id"] == claim["fact_id"] for f in m["facts"])
                for m in materials
            ):
                issues.append({"scene_id": scene["scene_id"], "code": "UNSUPPORTED_CLAIM"})
        for field in ("visual", "voiceover", "subtitle"):
            if scene[field] in allowed.values() and not any(c["text"] == scene[field] for c in claims):
                issues.append({"scene_id": scene["scene_id"], "code": "MISSING_CITATION"})
    text = json.dumps(draft, ensure_ascii=False)
    for word in rules["forbidden_terms"]:
        if word in text:
            issues.append({"code": "FORBIDDEN_TERM", "term": word})
    return {"draft_hash": fingerprint(draft), "passed": not issues, "issues": issues}


def can_finish(state):
    draft = state.get("draft")
    if not draft:
        return False
    h = fingerprint(draft)
    return (state.get("duration", {}).get("draft_hash") == h
            and state.get("checks", {}).get("draft_hash") == h
            and state["checks"]["passed"]
            and state["duration"]["total_seconds"] <= state["request"]["target_seconds"])


def make_draft(material, revision, long=False):
    fact = material["facts"][0]
    def scene(i, text, seconds, claim=False):
        return {"scene_id": f"S{i:02}", "visual": "产品演示画面" if claim else "创作者工作画面",
                "voiceover": text, "subtitle": text, "min_visual_seconds": seconds,
                "claims": [{"text": fact["text"], "material_id": material["id"], "fact_id": fact["id"]}] if claim else []}
    return {"revision": revision, "title": "给创作加上字幕",
            "scenes": [scene(1, "准备好这次的创作内容。", 8 if long else 2),
                       scene(2, fact["text"], 22 if long else 3, True),
                       scene(3, "检查文字，再发布你的作品。", 8 if long else 2)]}


def validate(state):
    try:
        request = Request(**state["request"]).model_dump()
        rules = json.loads((ROOT / "data/brand_rules.json").read_text(encoding="utf-8-sig"))
        return {"request": request, "rules": rules, "status": "running"}
    except ValidationError as exc:
        return {"status": "needs_input", "reason": str(exc)}


def decide(state):
    if state["steps"] >= state["max_steps"]:
        return {"status": "budget_exceeded", "reason": "达到动作次数上限"}
    if not state.get("searched"):
        action = {"name": "search_materials", "args": {"query": state["request"]["query"]}, "reason": "先取得可引用事实"}
    elif not state.get("materials"):
        action = {"name": "request_info", "args": {}, "reason": "未检索到素材，请补充产品资料或调整查询"}
    elif not state.get("draft"):
        action = {"name": "save_draft", "args": {"long": state["request"]["demo_scenario"] == "overlong"}, "reason": "依据已命中素材构建演示草稿"}
    elif not state.get("duration"):
        action = {"name": "estimate_duration", "args": {}, "reason": "检查当前版本时长"}
    elif state["duration"]["total_seconds"] > state["request"]["target_seconds"]:
        action = {"name": "save_draft" if state["revision"] < 2 else "fail", "args": {"long": False}, "reason": "超出目标时长，压缩画面停留；仍不满足则明确失败"}
    elif not state.get("checks"):
        action = {"name": "check_rules", "args": {}, "reason": "核对事实来源与品牌规则"}
    else:
        action = {"name": "finish" if can_finish(state) else "fail", "args": {}, "reason": "根据当前版本检查报告结束"}
    return {"action": action}


def dispatch(state):
    action = state["action"]
    name = action["name"]
    update = {}
    try:
        if name == "search_materials":
            if state["request"]["demo_scenario"] == "tool_failure":
                raise OSError("演示注入：素材工具不可用")
            matches = search(action["args"]["query"], state["request"]["product_id"])
            update = {"materials": matches, "searched": True}
            observation = {"count": len(matches), "ids": [m["id"] for m in matches]}
        elif name == "save_draft":
            revision = state.get("revision", 0) + 1
            draft = make_draft(state["materials"][0], revision, action["args"]["long"])
            update = {"draft": draft, "revision": revision, "duration": {}, "checks": {}}
            observation = {"revision": revision, "draft_hash": fingerprint(draft)}
        elif name == "estimate_duration":
            observation = estimate(state["draft"])
            update = {"duration": observation}
        elif name == "check_rules":
            observation = check(state["draft"], state["materials"], state["rules"])
            update = {"checks": observation}
        else:
            status = "needs_input" if name == "request_info" else "completed" if name == "finish" and can_finish(state) else "failed"
            update = {"status": status, "reason": action["reason"]}
            observation = {"status": status}
    except (OSError, ValueError, KeyError) as exc:
        update = {"status": "failed", "reason": str(exc)}
        observation = {"error": str(exc)}
    event = {"step": state["steps"] + 1, "actor": "deterministic_mock", "action": name,
             "arguments": action["args"], "reason": action["reason"], "observation": observation}
    return {**update, "steps": state["steps"] + 1, "trace": state["trace"] + [event]}


def build_graph():
    graph = StateGraph(State)
    graph.add_node("validate", validate)
    graph.add_node("decide", decide)
    graph.add_node("dispatch", dispatch)
    graph.add_edge(START, "validate")
    graph.add_conditional_edges("validate", lambda s: "decide" if s["status"] == "running" else END)
    graph.add_conditional_edges("decide", lambda s: "dispatch" if s["status"] == "running" else END)
    graph.add_conditional_edges("dispatch", lambda s: "decide" if s["status"] == "running" else END)
    return graph.compile()


def run(request, max_steps=10):
    if not 1 <= max_steps <= 100:
        raise ValueError("max_steps 必须为 1 到 100")
    return build_graph().invoke({"request": request, "steps": 0, "max_steps": max_steps, "trace": []},
                                {"recursion_limit": 2 * max_steps + 5})
