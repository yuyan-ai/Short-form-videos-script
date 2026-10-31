"""离线原型：真实工具配合确定性 Mock 决策，不代表 LLM 能力。"""
import json
from pathlib import Path
from .tools.retrieval import search
from .tools.duration import estimate
from .tools.rules import check
from .policy import fingerprint, can_finish
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, ConfigDict, Field, ValidationError

ROOT = Path(__file__).resolve().parents[2]


class Request(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    topic: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    target_seconds: float = Field(gt=0, le=300, allow_inf_nan=False)
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
    mode: str
    model: str
    deadline: float












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
    except (OSError, ValueError, TypeError) as exc:
        return {"status": "failed", "reason": "规则文件加载失败：" + type(exc).__name__}


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
            if state.get("mode") != "live" and state["request"]["demo_scenario"] == "tool_failure":
                raise OSError("演示注入：素材工具不可用")
            matches = search(action["args"]["query"], state["request"]["product_id"])
            merged = {m["id"]: m for m in state.get("materials", [])}
            merged.update({m["id"]: m for m in matches})
            update = {"materials": list(merged.values()), "searched": True, "checks": {}}
            observation = {"count": len(matches), "ids": [m["id"] for m in matches]}
        elif name == "save_draft":
            revision = state.get("revision", 0) + 1
            if state.get("mode") == "live":
                from .schemas import Draft
                draft = Draft(**action["args"]["draft"]).model_dump()
                draft["revision"] = revision
            else:
                draft = make_draft(state["materials"][0], revision, action["args"]["long"])
            update = {"draft": draft, "revision": revision, "duration": {}, "checks": {}}
            observation = {"revision": revision, "draft_hash": fingerprint(draft)}
        elif name == "estimate_duration":
            observation = estimate(state["draft"])
            update = {"duration": observation}
        elif name == "check_rules":
            observation = check(state["draft"], state["materials"], state["rules"])
            update = {"checks": observation}
        elif name == "invalid_output":
            return {}
        elif name == "finish" and not can_finish(state):
            observation = {"error": "当前草稿缺少通过的时长/规则报告，请补检或修改"}
        else:
            status = "needs_input" if name == "request_info" else "completed" if name == "finish" and can_finish(state) else "failed"
            update = {"status": status, "reason": action["reason"]}
            observation = {"status": status}
    except (OSError, ValueError, KeyError, IndexError) as exc:
        message = "工具执行或参数校验失败，请核对动作参数及前置草稿" if isinstance(exc, ValidationError) else str(exc)
        update = {} if state.get("mode") == "live" else {"status": "failed", "reason": message}
        observation = {"error": message}
    event = {"step": state["steps"] + 1, "actor": "live_model" if state.get("mode") == "live" else "deterministic_mock", "action": name,
             "arguments": action["args"], "reason": action["reason"], "observation": observation}
    return {**update, "steps": state["steps"] + 1, "trace": state["trace"] + [event]}


def build_graph(model=None):
    import time
    from .models.live import ModelError

    def checked_dispatch(state):
        # 仅原创文案需要额外模型审核；原文白名单仍走确定性检查。
        if state["action"]["name"] != "check_rules" or not model or not state.get("draft"):
            return dispatch(state)
        report = check(state["draft"], state.get("materials", []), state["rules"])
        if not any(i["code"] == "UNAPPROVED_TEXT" for i in report["issues"]):
            return dispatch(state)
        if state["steps"] + 2 > state["max_steps"] or time.monotonic() >= state["deadline"]:
            return {"status": "budget_exceeded", "reason": "剩余预算不足以审核原创文案"}
        try:
            review = model.review(state)
            if time.monotonic() >= state["deadline"]:
                return {"status": "budget_exceeded", "reason": "文案审核后总时间已耗尽"}
            if review["passed"]:
                report["issues"] = [i for i in report["issues"] if i["code"] != "UNAPPROVED_TEXT"]
            else:
                report["issues"].append({"code": "COPY_REVIEW_FAILED", "details": review["issues"]})
            report["copy_review"] = review
        except (ModelError, ValidationError) as exc:
            report["issues"].append({"code": "COPY_REVIEW_ERROR", "message": "文案审核失败，未获批准"})
        report["passed"] = not report["issues"]
        events = [{"step": state["steps"] + 1, "actor": "live_model", "action": "check_rules",
                   "arguments": {}, "reason": state["action"]["reason"], "observation": report},
                  {"step": state["steps"] + 2, "actor": "live_model", "action": "review_copy",
                   "arguments": {"draft_hash": fingerprint(state["draft"])},
                   "reason": "审核原创文案的事实依据和用户要求适配", "observation": report.get("copy_review", {"error": "审核失败"})}]
        return {"checks": report, "steps": state["steps"] + 2, "trace": state["trace"] + events}

    def live_decide(state):
        if state["steps"] >= state["max_steps"] or time.monotonic() >= state["deadline"]:
            return {"status": "budget_exceeded", "reason": "达到模型调用或总运行时间上限"}
        try:
            action = model.decide(state)
            if time.monotonic() >= state["deadline"]:
                return {"status": "budget_exceeded", "reason": "总运行时间已耗尽"}
            return {"action": action}
        except ValidationError:
            event = {"step": state["steps"] + 1, "actor": "live_model", "action": "invalid_output",
                     "observation": {"error": "输出结构不合法，请按schema重试"}}
            return {"steps": state["steps"] + 1, "action": {"name": "invalid_output", "args": {}, "reason": "输出结构不合法"},
                    "trace": state["trace"] + [event]}
        except ModelError as exc:
            event = {"step": state["steps"] + 1, "actor": "live_model", "action": "model_error", "observation": {"error": str(exc)}}
            return {"status": "failed", "reason": str(exc), "steps": state["steps"] + 1, "trace": state["trace"] + [event]}

    graph = StateGraph(State)
    graph.add_node("validate", validate)
    graph.add_node("decide", live_decide if model else decide)
    graph.add_node("dispatch", checked_dispatch)
    graph.add_edge(START, "validate")
    graph.add_conditional_edges("validate", lambda s: "decide" if s["status"] == "running" else END)
    graph.add_conditional_edges("decide", lambda s: "dispatch" if s["status"] == "running" else END)
    graph.add_conditional_edges("dispatch", lambda s: "decide" if s["status"] == "running" else END)
    return graph.compile()


def run(request, max_steps=10, model=None, total_seconds=180, initial_draft=None):
    import time
    if not 1 <= max_steps <= 100:
        raise ValueError("max_steps 必须为 1 到 100")
    seed = {}
    trace = []
    if initial_draft is not None:
        from .schemas import Draft
        draft = Draft.model_validate(initial_draft).model_dump()
        draft["revision"] = 1
        initial_duration = estimate(draft)
        seed = {"draft": draft, "revision": 1, "duration": initial_duration}
        trace = [{"step": 0, "actor": "user", "action": "import_draft", "arguments": {"draft": draft},
                  "reason": "导入待检查或改写的用户脚本，尚未获得检查批准", "observation": {"draft_hash": fingerprint(draft), "initial_duration": initial_duration}}]
    return build_graph(model).invoke({**seed, "request": request, "steps": 0, "max_steps": max_steps, "trace": trace,
                                     "mode": "live" if model else "mock", "model": getattr(getattr(model, "config", None), "model", None),
                                     "deadline": time.monotonic() + total_seconds},
                                {"recursion_limit": 2 * max_steps + 5})
