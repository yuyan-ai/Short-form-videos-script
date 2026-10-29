"""导出实际执行的离线流程结果。"""
import json
from pathlib import Path


def export_run(directory: Path, request, state):
    directory.mkdir(parents=True, exist_ok=False)
    def save(name, obj):
        (directory / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    save("input.json", request)
    result = {"mode": state.get("mode", "mock"), "status": state["status"], "reason": state.get("reason"),
              "script": state.get("draft"), "duration": state.get("duration"),
              "sources": [m["id"] for m in state.get("materials", [])],
              "risks": ["合成素材；时长仅为估算；模型效果须单独评估"], "steps": state["steps"]}
    save("result.json", result)
    save("checks.json", state.get("checks", {}))
    save("manifest.json", {"mode": state.get("mode", "mock"), "model": state.get("model"), "rules_version": state.get("rules", {}).get("version"), "materials": state.get("materials", [])})
    (directory / "trace.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False)+"\n" for e in state["trace"]), encoding="utf-8")
    lines = ["# 脚本结果（" + state.get("mode", "mock") + "）", "", "状态："+state["status"], "", "合成素材 / 估算时长", ""]
    draft = state.get("draft")
    if draft:
        lines.append("## "+draft["title"])
        timings = {s["scene_id"]: s["seconds"] for s in state.get("duration", {}).get("scenes", [])}
        for s in draft["scenes"]:
            lines.extend(["", "### "+s["scene_id"], "画面："+s["visual"], "旁白/字幕："+s["voiceover"],
                          "预计秒数："+str(timings.get(s["scene_id"], "尚未检查")), "引用："+str([c["fact_id"] for c in s["claims"]])])
        lines.extend(["", "预计总时长："+str(state.get("duration", {}).get("total_seconds", "尚未检查"))])
    (directory / "script.md").write_text("\n".join(lines), encoding="utf-8")
