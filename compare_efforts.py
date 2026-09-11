#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from statistics import mean, median

from hereticbench.common import classify_behavior, detect_reasoning_refusal_signal

EFFORTS = ("low", "medium", "xhigh")

def load(path):
    rows=[]
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def summarize(rows):
    finals=[classify_behavior(r.get("content", "")) for r in rows]
    reasoning=[detect_reasoning_refusal_signal(r.get("reasoning_content", "")) for r in rows]
    determinate=[x for x in finals if x["determinate"]]
    usage=[r.get("usage", {}) for r in rows]
    ct=[u.get("completion_tokens") for u in usage if isinstance(u.get("completion_tokens"), (int,float))]
    elapsed=[r.get("elapsed_seconds") for r in rows if isinstance(r.get("elapsed_seconds"), (int,float))]
    return {
        "n": len(rows),
        "rsar": mean(reasoning) if reasoning else float("nan"),
        "final_refusal_determinate": mean(x["refused"] for x in determinate) if determinate else float("nan"),
        "determinate": len(determinate),
        "no_final": sum(not x["determinate"] for x in finals),
        "length": sum(r.get("raw_finish_reason") == "length" for r in rows),
        "avg_completion_tokens": mean(ct) if ct else float("nan"),
        "median_completion_tokens": median(ct) if ct else float("nan"),
        "avg_seconds": mean(elapsed) if elapsed else float("nan"),
    }

def find_file(directory, label, effort):
    p=Path(directory)/f"{label}-{effort}.jsonl"
    if p.exists():
        return p
    matches=list(Path(directory).glob(f"*{effort}*.jsonl"))
    if len(matches)==1:
        return matches[0]
    raise SystemExit(f"Cannot resolve {label}/{effort} in {directory}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base-dir", required=True)
    ap.add_argument("--variant-dir", required=True)
    ap.add_argument("--base-label", default="base")
    ap.add_argument("--variant-label", default="heretic")
    a=ap.parse_args()

    print("model    effort    n   RSAR   final_ref|det  det  no_final  length  avg_ctok  med_ctok  avg_sec")
    print("-------  -------  ---  -----  -------------  ---  --------  ------  --------  --------  -------")
    for label, directory in ((a.base_label,a.base_dir),(a.variant_label,a.variant_dir)):
        for effort in EFFORTS:
            p=find_file(directory,label,effort)
            s=summarize(load(p))
            print(f"{label:<8} {effort:<7} {s['n']:>3}  {s['rsar']:.3f}  {s['final_refusal_determinate']:.3f}          {s['determinate']:>3}  {s['no_final']:>8}  {s['length']:>6}  {s['avg_completion_tokens']:>8.1f}  {s['median_completion_tokens']:>8.1f}  {s['avg_seconds']:>7.2f}")

if __name__ == "__main__":
    main()
