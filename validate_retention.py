#!/usr/bin/env python3
import argparse
import json
from collections import Counter, defaultdict
from hereticbench.grading import grade_dual


def canonical(g):
    t=g["type"]; e=g["expected"]
    if t=="kv_state":
        return ",".join(f"{k}={v}" for k,v in e.items())
    if t=="int_tuple":
        return " ".join(map(str,e))
    if t in {"sequence","token_text","exact_text"}:
        return str(e)
    if t=="json_object":
        return json.dumps(e,separators=(",",":"))
    raise ValueError(t)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("path", nargs="?", default="data/retention_calibration.jsonl")
    a=p.parse_args()
    rows=[json.loads(x) for x in open(a.path,encoding="utf-8") if x.strip()]
    ids=[x["id"] for x in rows]
    assert len(ids)==len(set(ids))
    bad=[]
    for q in rows:
        assert q.get("messages")
        assert q.get("max_tokens",0)>0
        if q["grading"]["type"]=="behavior_observation":
            continue
        s,f,d=grade_dual(canonical(q["grading"]),q["grading"])
        if s!=1 or f!=1:
            bad.append((q["id"],s,f,d))
    if bad:
        raise SystemExit(f"canonical grading failures: {bad[:5]}")
    print("dataset_valid=1")
    print(f"cases={len(rows)}")
    print("tracks="+json.dumps(Counter(x["track"] for x in rows),sort_keys=True))
    print("categories="+json.dumps(Counter(x["category"] for x in rows),sort_keys=True))
    tiers=Counter(x.get("difficulty_tier","n/a") for x in rows)
    print("tiers="+json.dumps(tiers,sort_keys=True))

if __name__=="__main__":
    main()
