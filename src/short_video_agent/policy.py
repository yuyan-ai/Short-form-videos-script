import hashlib
import json

def fingerprint(draft):
    return hashlib.sha256(json.dumps(draft, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def can_finish(state):
    draft = state.get("draft")
    if not draft:
        return False
    h = fingerprint(draft)
    return (state.get("duration", {}).get("draft_hash") == h
            and state.get("checks", {}).get("draft_hash") == h
            and state["checks"].get("context_hash") == fingerprint({"materials": state.get("materials", []), "rules": state.get("rules", {})})
            and state["checks"]["passed"]
            and state["duration"]["total_seconds"] <= state["request"]["target_seconds"])
