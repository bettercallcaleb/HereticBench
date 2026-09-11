#!/usr/bin/env python3
import argparse
import json
import re
from hereticbench.common import load_jsonl


def seq_semantic(content, expected):
    n=len(expected)
    hits=re.findall(rf"(?<![A-Z])[A-Z]{{{n}}}(?![A-Z])", content or "")
    return float(bool(hits) and hits[-1]==expected)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("results")
    a=p.parse_args()
    rows=[r for r in load_jsonl(a.results) if r.get("status")=="ok"]
    cap=[]; ins=[]
    for r in rows:
        if r.get("track")=="capability":
            if r.get("category")=="constraint_assignment":
                s=seq_semantic(r.get("content",""),str(r["grading"]["expected"]))
            else:
                s=float(r.get("score") or 0)
            cap.append(s)
        elif r.get("track")=="instruction":
            if r.get("category")=="json_transform":
                try:
                    actual=json.loads(r.get("content", ""))
                    expected=json.loads(r["grading"]["expected"])
                    s=float(actual==expected)
                except Exception:
                    s=0.0
            else:
                s=float(r.get("score") or 0)
            ins.append(s)
    if cap: print(f"capability_semantic={sum(cap)/len(cap):.4f} ({int(sum(cap))}/{len(cap)})")
    if ins: print(f"instruction_semantic={sum(ins)/len(ins):.4f} ({int(sum(ins))}/{len(ins)})")

if __name__=="__main__":
    main()
