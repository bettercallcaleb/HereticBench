#!/usr/bin/env python3
import json
import sys
from collections import Counter
from pathlib import Path

path=Path(sys.argv[1] if len(sys.argv)>1 else "data/openbehavior.jsonl")
rows=[json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
ids=[r["id"] for r in rows]
expected={"general_reasoning":20,"technical_coding":15,"explanation_writing":15,"uncertainty_judgment":15,"controversial_benign":15,"cybersecurity_dual_use":10,"ethical_sensitive":10}
counts=Counter(r.get("category") for r in rows)
ok=len(rows)==100 and len(ids)==len(set(ids)) and all(r.get("track")=="openbehavior" for r in rows) and dict(counts)==expected and all(r.get("grading",{}).get("type")=="behavior_observation" for r in rows)
print(f"dataset_valid={int(ok)}")
print(f"cases={len(rows)}")
for k,v in counts.items(): print(f"{k}={v}")
raise SystemExit(0 if ok else 1)
