#!/usr/bin/env python3
import argparse
import json
import random
from pathlib import Path
from build_retention import GENERATORS, row


def make_retention(profile, per_category=30):
    rows=[]
    for cidx, (category, fn) in enumerate(GENERATORS.items()):
        tier=profile["categories"][category]["selected_tier"]
        for i in range(per_category):
            seed=900000 + cidx*10000 + i
            prompt, expected=fn(seed,tier)
            qid=f"RET_{category.upper()}_{i+1:03d}"
            if category in {"state_tracking_v3","boolean_circuit_v3"}:
                grading={"type":"kv_state","expected":expected}
            elif category=="code_trace_v3":
                grading={"type":"int_tuple","expected":expected}
            elif category=="constraint_assignment_v3":
                grading={"type":"sequence","expected":expected,"alphabet":"ABCDEFGH"}
            else:
                grading={"type":"token_text","expected":expected,"pattern":r"\b\d+\|[A-Z](?:-[A-Z])+\b"}
            rows.append(row(qid,category,prompt,grading,tier))
    return rows


def instruction_json_case(seed):
    r=random.Random(seed)
    teams=["red","blue","green"]
    names=["ada","ben","cy","dia","eli","fay","gus","hana","ian","joy","kai","lia"]
    records=[]
    for name in names:
        records.append({"name":name,"team":r.choice(teams),"score":r.randint(40,99),"active":bool(r.randint(0,1))})
    threshold=r.randint(58,76)
    selected=[{"name":x["name"],"score":x["score"]} for x in records if x["active"] and x["score"]>=threshold]
    selected.sort(key=lambda x:(-x["score"],x["name"]))
    expected={"threshold":threshold,"selected":selected,"count":len(selected)}
    prompt=(f"Records: {json.dumps(records,separators=(',',':'))}. Keep only records with active=true and score >= {threshold}. "
            "Sort by score descending, then name alphabetically for ties. Output exactly one JSON object with top-level keys threshold, selected, count in that order. "
            "Each selected entry must contain only name and score in that order. No markdown or extra text.")
    return prompt, expected


def instruction_lines_case(seed):
    r=random.Random(seed)
    pool=["amber","cobalt","delta","ember","fjord","garnet","harbor","indigo","juniper","kernel","lilac","meteor","nectar","onyx","pebble","quartz"]
    words=r.sample(pool,10)
    minlen=r.randint(5,6)
    def vowels(w):
        return sum(ch in "aeiou" for ch in w)
    kept=[w for w in words if len(w)>=minlen and vowels(w)>=2]
    kept.sort(key=lambda w:(-vowels(w),len(w),w))
    expected="\n".join(f"{i+1:02d}|{w.upper()}|{len(w)}|{vowels(w)}" for i,w in enumerate(kept))
    if not expected:
        expected="NONE"
    prompt=(f"Words: {', '.join(words)}. Keep words with length >= {minlen} and at least 2 vowels (a,e,i,o,u). "
            "Sort by vowel count descending, then length ascending, then alphabetically. Output one line per kept word as NN|WORD|LENGTH|VOWELS, NN starting at 01. "
            "WORD must be uppercase. If none remain, output NONE. No bullets, blank lines, markdown, or explanation.")
    return prompt, expected


def instruction_multiturn_case(seed):
    r=random.Random(seed)
    nums=[r.randint(10,99) for _ in range(12)]
    mod=r.choice([3,4,5,6])
    cutoff=r.randint(35,65)
    kept=sorted(set(x for x in nums if x>=cutoff and x%mod!=0), reverse=True)
    expected={"mod":mod,"cutoff":cutoff,"values":kept,"sum":sum(kept)}
    system=("For the next user request, return exactly one JSON object and nothing else. Preserve the requested top-level key order. "
            "Whitespace is allowed. Never use markdown fences or prose around the JSON.")
    user=(f"Numbers: {nums}. Keep unique values >= {cutoff} that are NOT divisible by {mod}; sort descending. "
          f"Return keys mod, cutoff, values, sum in that order, where sum is the sum of the kept values.")
    return [{"role":"system","content":system},{"role":"user","content":user}], expected


def make_instruction():
    rows=[]
    for i in range(20):
        prompt,expected=instruction_json_case(1100000+i)
        rows.append({
            "id":f"INS3_JSON_{i+1:02d}","track":"instruction_v3","category":"nested_json_transform",
            "messages":[{"role":"user","content":prompt}],
            "grading":{"type":"json_object","expected":expected,"key_order":["threshold","selected","count"]},
            "max_tokens":3072,"difficulty":"hard"
        })
    for i in range(20):
        prompt,expected=instruction_lines_case(1110000+i)
        rows.append({
            "id":f"INS3_LINES_{i+1:02d}","track":"instruction_v3","category":"multi_rule_lines",
            "messages":[{"role":"user","content":prompt}],
            "grading":{"type":"exact_text","expected":expected,"case_sensitive":True},
            "max_tokens":3072,"difficulty":"hard"
        })
    for i in range(20):
        messages,expected=instruction_multiturn_case(1120000+i)
        rows.append({
            "id":f"INS3_SYS_{i+1:02d}","track":"instruction_v3","category":"system_format_persistence",
            "messages":messages,
            "grading":{"type":"json_object","expected":expected,"key_order":["mod","cutoff","values","sum"]},
            "max_tokens":3072,"difficulty":"hard"
        })
    return rows


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--profile", default="profiles/retention_profile.json")
    p.add_argument("--out", default="data/retention_eval.jsonl")
    p.add_argument("--per-category", type=int, default=30)
    a=p.parse_args()
    profile=json.loads(Path(a.profile).read_text(encoding="utf-8"))
    missing=[c for c in GENERATORS if c not in profile.get("categories",{})]
    if missing:
        raise SystemExit("profile missing categories: "+", ".join(missing))
    rows=make_retention(profile,a.per_category)+make_instruction()
    ids=[x["id"] for x in rows]
    assert len(ids)==len(set(ids))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out,"w",encoding="utf-8") as f:
        for x in rows:
            f.write(json.dumps(x,ensure_ascii=False)+"\n")
    print(f"wrote {len(rows)} evaluation cases to {a.out}")
    print(f"retention={sum(x['track']=='retention' for x in rows)} instruction_v3={sum(x['track']=='instruction_v3' for x in rows)}")
    for c in GENERATORS:
        print(c, profile["categories"][c]["selected_tier"])

if __name__=="__main__":
    main()
