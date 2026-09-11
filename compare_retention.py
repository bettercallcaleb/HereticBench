#!/usr/bin/env python3
import argparse
from collections import Counter, defaultdict
from statistics import mean, median
from hereticbench.common import load_jsonl
from hereticbench.grading import grade_dual


def index(path):
    return {r["id"]:r for r in load_jsonl(path) if r.get("status")=="ok"}


def metrics(r):
    sem=r.get("semantic_score")
    fmt=r.get("format_score")
    if sem is None or fmt is None:
        sem,fmt,_=grade_dual(r.get("content", ""), r["grading"])
    return sem,fmt


def main():
    p=argparse.ArgumentParser()
    p.add_argument("base")
    p.add_argument("variant")
    a=p.parse_args()
    A=index(a.base); B=index(a.variant)
    ids=sorted(set(A)&set(B))
    if not ids:
        raise SystemExit("No paired successful cases")
    if any(A[i].get("messages")!=B[i].get("messages") for i in ids):
        raise SystemExit("MESSAGE_MISMATCH")
    if any(A[i].get("grading")!=B[i].get("grading") for i in ids):
        raise SystemExit("GRADING_MISMATCH")
    print(f"paired={len(ids)}")
    print("track/category                 n   base_sem  var_sem   delta   base_fmt  var_fmt")
    print("----------------------------- ---  --------  -------  -------  --------  -------")
    groups=defaultdict(list)
    for i in ids:
        groups[(A[i].get("track"),A[i].get("category"))].append(i)
    all_reg=[]; all_imp=[]
    for (track,cat),qids in sorted(groups.items()):
        vals=[]
        for i in qids:
            bs,bf=metrics(A[i]); vs,vf=metrics(B[i])
            if bs is None or vs is None:
                continue
            vals.append((i,bs,bf,vs,vf))
            if bs>vs: all_reg.append(i)
            if vs>bs: all_imp.append(i)
        if not vals:
            continue
        bsem=mean(x[1] for x in vals); vsem=mean(x[3] for x in vals)
        bfmt=mean(x[2] for x in vals); vfmt=mean(x[4] for x in vals)
        print(f"{track+'/'+cat:29s} {len(vals):3d}  {bsem:8.3f}  {vsem:7.3f}  {vsem-bsem:+7.3f}  {bfmt:8.3f}  {vfmt:7.3f}")
    for track in sorted({A[i].get("track") for i in ids}):
        qids=[i for i in ids if A[i].get("track")==track]
        vals=[(i,*metrics(A[i]),*metrics(B[i])) for i in qids]
        vals=[x for x in vals if x[1] is not None and x[3] is not None]
        if not vals: continue
        print(f"\n{track}: semantic base={mean(x[1] for x in vals):.4f} variant={mean(x[3] for x in vals):.4f} delta={mean(x[3]-x[1] for x in vals):+.4f}")
        print(f"{track}: format   base={mean(x[2] for x in vals):.4f} variant={mean(x[4] for x in vals):.4f} delta={mean(x[4]-x[2] for x in vals):+.4f}")
        bct=[(A[i].get("usage") or {}).get("completion_tokens",0) or 0 for i in qids]
        vct=[(B[i].get("usage") or {}).get("completion_tokens",0) or 0 for i in qids]
        print(f"{track}: avg_completion_tokens base={mean(bct):.1f} variant={mean(vct):.1f} delta={mean(vct)-mean(bct):+.1f}")
    print(f"\nsemantic_regressions={len(all_reg)} semantic_improvements={len(all_imp)}")
    if all_reg: print("regressions="+" ".join(all_reg))
    if all_imp: print("improvements="+" ".join(all_imp))

if __name__=="__main__":
    main()
