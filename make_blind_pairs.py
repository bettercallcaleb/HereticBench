#!/usr/bin/env python3
import argparse
import hashlib
import json
import random
from pathlib import Path

def load(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("base")
    p.add_argument("heretic")
    p.add_argument("--out", default="results/openbehavior-blind.jsonl")
    p.add_argument("--key", default="results/openbehavior-key.json")
    p.add_argument("--seed", type=int, default=3101)
    a=p.parse_args()
    base={r["id"]:r for r in load(a.base) if r.get("status")=="ok"}
    heretic={r["id"]:r for r in load(a.heretic) if r.get("status")=="ok"}
    ids=sorted(set(base)&set(heretic))
    rng=random.Random(a.seed)
    pairs=[]
    key={"seed":a.seed,"pairs":{}}
    for cid in ids:
        b,h=base[cid],heretic[cid]
        if b.get("messages") != h.get("messages"):
            raise SystemExit(f"message mismatch: {cid}")
        swap=bool(rng.getrandbits(1))
        arow,hrow=(h,b) if swap else (b,h)
        mapping={"A":"heretic","B":"base"} if swap else {"A":"base","B":"heretic"}
        prompt="\n".join(m.get("content","") for m in b.get("messages",[]) if m.get("role")=="user")
        pairs.append({
            "id":cid,
            "category":b.get("category"),
            "prompt":prompt,
            "response_A":{"reasoning":arow.get("reasoning_content",""),"answer":arow.get("content",""),"finish_reason":arow.get("raw_finish_reason"),"completion_tokens":(arow.get("usage") or {}).get("completion_tokens")},
            "response_B":{"reasoning":hrow.get("reasoning_content",""),"answer":hrow.get("content",""),"finish_reason":hrow.get("raw_finish_reason"),"completion_tokens":(hrow.get("usage") or {}).get("completion_tokens")}
        })
        key["pairs"][cid]=mapping
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8") as f:
        for r in pairs: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    raw=out.read_bytes()
    key["blind_sha256"]=hashlib.sha256(raw).hexdigest()
    Path(a.key).write_text(json.dumps(key,indent=2),encoding="utf-8")
    print(f"pairs={len(pairs)}")
    print(f"blind={out}")
    print(f"key={a.key}")
    print(f"blind_sha256={key['blind_sha256']}")

if __name__=="__main__": main()
