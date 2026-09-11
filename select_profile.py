#!/usr/bin/env python3
import argparse
import json
from collections import defaultdict
from pathlib import Path

TIERS = ["easy", "medium", "hard", "very_hard"]


def load_jsonl(path):
    rows=[]
    with open(path, encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def metric(r):
    v=r.get("semantic_score")
    if v is None:
        v=r.get("score")
    return v


def main():
    p=argparse.ArgumentParser()
    p.add_argument("base_results")
    p.add_argument("--out", default="profiles/retention_profile.json")
    p.add_argument("--target", type=float, default=0.75)
    p.add_argument("--low", type=float, default=0.55)
    p.add_argument("--high", type=float, default=0.90)
    a=p.parse_args()
    rows=[r for r in load_jsonl(a.base_results) if r.get("status")=="ok" and r.get("track")=="retention"]
    by=defaultdict(lambda: defaultdict(list))
    for r in rows:
        s=metric(r)
        if s is not None:
            by[r["category"]][r.get("difficulty_tier") or r.get("difficulty")].append(float(s))
    profile={"target":a.target,"acceptable_range":[a.low,a.high],"categories":{}}
    print("category                     easy   medium   hard   very_hard   selected")
    print("---------------------------  -----  -------  -----  ----------  --------")
    for cat in sorted(by):
        rates={t:(sum(by[cat][t])/len(by[cat][t]) if by[cat][t] else None) for t in TIERS}
        candidates=[t for t in TIERS if rates[t] is not None and a.low <= rates[t] <= a.high]
        pool=candidates or [t for t in TIERS if rates[t] is not None]
        chosen=min(pool, key=lambda t:(abs(rates[t]-a.target), TIERS.index(t)))
        status="in_range" if chosen in candidates else ("ceiling" if all((rates[t] or 0)>a.high for t in pool) else "floor_or_mixed")
        profile["categories"][cat]={"selected_tier":chosen,"calibration_accuracy":rates[chosen],"status":status,"all_tiers":rates}
        vals=["n/a" if rates[t] is None else f"{rates[t]:.3f}" for t in TIERS]
        print(f"{cat:27s}  {vals[0]:>5s}  {vals[1]:>7s}  {vals[2]:>5s}  {vals[3]:>10s}  {chosen}")
    if not profile["categories"]:
        raise SystemExit("No usable retention calibration results")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(f"profile={a.out}")

if __name__=="__main__":
    main()
