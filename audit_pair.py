#!/usr/bin/env python3
import argparse
import re
from collections import Counter, defaultdict
from hereticbench.common import classify_behavior, load_jsonl

def idx(path):
    return {r["id"]: r for r in load_jsonl(path) if r.get("status") == "ok"}

def usage(r, key):
    return (r.get("usage") or {}).get(key)

def guess_quant(r):
    q = str(r.get("quantization") or "")
    if q and q != "unknown":
        return q
    text = str(r.get("server_model_path") or r.get("model") or "")
    m = re.search(r"(?i)(?:UD-)?(?:IQ|Q)\d(?:_[A-Z0-9]+)+", text)
    return m.group(0) if m else "unknown"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("base")
    p.add_argument("variant")
    a = p.parse_args()
    A = idx(a.base)
    B = idx(a.variant)
    ids = sorted(set(A) & set(B))
    print(f"paired={len(ids)}")
    print(f"same_messages={sum(A[i].get('messages')==B[i].get('messages') for i in ids)}/{len(ids)}")
    print(f"same_grading={sum(A[i].get('grading')==B[i].get('grading') for i in ids)}/{len(ids)}")
    print(f"dataset_hash_base={sorted({A[i].get('dataset_sha256') for i in ids})}")
    print(f"dataset_hash_variant={sorted({B[i].get('dataset_sha256') for i in ids})}")
    deltas = []
    for i in ids:
        x, y = usage(A[i], "prompt_tokens"), usage(B[i], "prompt_tokens")
        if x is not None and y is not None:
            deltas.append(y - x)
    print(f"prompt_token_delta_histogram={dict(sorted(Counter(deltas).items()))}")
    print(f"quant_base={sorted({guess_quant(A[i]) for i in ids})}")
    print(f"quant_variant={sorted({guess_quant(B[i]) for i in ids})}")
    for label, R in [("base", A), ("variant", B)]:
        print(f"{label}_length={sum(R[i].get('raw_finish_reason')=='length' for i in ids)}/{len(ids)}")
        print(f"{label}_reasoning_present={sum(bool(R[i].get('reasoning_content','').strip()) for i in ids)}/{len(ids)}")
        print(f"{label}_empty_content={sum(not bool(R[i].get('content','').strip()) for i in ids)}/{len(ids)}")
        bnd = [i for i in ids if R[i].get("track") == "boundary"]
        print(f"{label}_boundary_determinate={sum(classify_behavior(R[i].get('content',''))['determinate'] for i in bnd)}/{len(bnd)}")

if __name__ == "__main__":
    main()
