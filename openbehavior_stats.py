#!/usr/bin/env python3
import argparse
import json
from collections import defaultdict
from pathlib import Path

def load(p): return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]

def metric(rows):
    ok=[r for r in rows if r.get("status")=="ok"]
    n=len(ok)
    if not n: return {"n":0}
    return {
        "n":n,
        "avg_completion_tokens":sum((r.get("usage") or {}).get("completion_tokens") or 0 for r in ok)/n,
        "length_rate":sum(r.get("raw_finish_reason")=="length" for r in ok)/n,
        "empty_final_rate":sum(not bool((r.get("content") or "").strip()) for r in ok)/n,
        "final_refusal_rate":sum(bool(((r.get("diagnostics") or {}).get("visible_behavior") or {}).get("refused")) for r in ok)/n,
        "reasoning_refusal_rate":sum(bool(((r.get("diagnostics") or {}).get("reasoning_behavior") or {}).get("refused")) for r in ok)/n,
    }

def fmt(m):
    return f"n={m['n']:3d} ctok={m.get('avg_completion_tokens',0):7.1f} length={m.get('length_rate',0):6.1%} empty={m.get('empty_final_rate',0):6.1%} final_refusal={m.get('final_refusal_rate',0):6.1%} reasoning_refusal={m.get('reasoning_refusal_rate',0):6.1%}"

def main():
    p=argparse.ArgumentParser(); p.add_argument("base"); p.add_argument("heretic"); a=p.parse_args()
    br=load(a.base); hr=load(a.heretic)
    print("ALL")
    print("Base    "+fmt(metric(br)))
    print("Heretic "+fmt(metric(hr)))
    cats=sorted(set(r.get("category") for r in br+hr))
    for c in cats:
        print(f"\n[{c}]")
        print("Base    "+fmt(metric([r for r in br if r.get('category')==c])))
        print("Heretic "+fmt(metric([r for r in hr if r.get('category')==c])))

if __name__=="__main__": main()
