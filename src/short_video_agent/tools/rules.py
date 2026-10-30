import json
from ..policy import fingerprint
from .duration import estimate

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
            if claim["text"] not in [scene[f] for f in ("visual", "voiceover", "subtitle")]:
                issues.append({"scene_id": scene["scene_id"], "code": "IRRELEVANT_CITATION",
                               "suggestion": "删除无关引用，或在本镜头中展示对应事实原文"})
            if allowed.get(claim["fact_id"]) != claim["text"] or not any(
                m["id"] == claim["material_id"] and any(f["id"] == claim["fact_id"] for f in m["facts"])
                for m in materials
            ):
                issues.append({"scene_id": scene["scene_id"], "code": "UNSUPPORTED_CLAIM"})
        for field in ("visual", "voiceover", "subtitle"):
            if scene[field] in allowed.values() and not any(c["text"] == scene[field] for c in claims):
                issues.append({"scene_id": scene["scene_id"], "code": "MISSING_CITATION"})
    if not any(scene["claims"] for scene in draft["scenes"]):
        issues.append({"code": "NO_PRODUCT_FACT", "suggestion": "至少一个镜头应展示并引用产品事实"})
    spoken = [s["voiceover"] or s["subtitle"] for s in draft["scenes"]]
    for text in set(spoken):
        if text and spoken.count(text) > 1:
            issues.append({"code": "REPEATED_COPY", "text": text,
                           "suggestion": "合并重复镜头或使用不同的已审核表达"})
    for timing in estimate(draft)["scenes"]:
        if timing["padding_seconds"] > rules.get("max_scene_padding_seconds", 3):
            issues.append({"scene_id": timing["scene_id"], "code": "EXCESSIVE_PADDING",
                           "padding_seconds": timing["padding_seconds"],
                           "suggestion": "缩短画面停留或补充审核过的有效内容，不必凑满目标时长"})
    text = json.dumps(draft, ensure_ascii=False)
    for word in rules["forbidden_terms"]:
        if word in text:
            issues.append({"code": "FORBIDDEN_TERM", "term": word})
    return {"draft_hash": fingerprint(draft), "context_hash": fingerprint({"materials": materials, "rules": rules}),
            "passed": not issues, "issues": issues}
