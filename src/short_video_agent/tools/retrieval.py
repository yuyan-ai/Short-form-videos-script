import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]

def search(query, product_id):
    records = json.loads((ROOT / "data/materials.json").read_text(encoding="utf-8-sig"))
    tokens = re.findall(r"[\w]+", query.casefold())
    if not tokens:
        return []
    ranked = []
    for material in records:
        if material["product_id"] != product_id:
            continue
        facts = " ".join(f["text"] for f in material["facts"]).casefold()
        name = material.get("product_name", "").casefold()
        score = sum(3 if token in facts else 1 if token in name else 0 for token in tokens)
        if score:
            ranked.append((score, material))
    return [m for _, m in sorted(ranked, key=lambda item: (-item[0], item[1]["id"]))]
