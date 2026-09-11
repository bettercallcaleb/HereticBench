#!/usr/bin/env python3
import json
from collections import Counter, defaultdict
from hereticbench.grading import grade

PATH="data/questions.jsonl"

def main():
    rows=[json.loads(x) for x in open(PATH,encoding="utf-8") if x.strip()]
    assert len(rows)==300
    ids=[r["id"] for r in rows]
    assert len(ids)==len(set(ids))
    assert Counter(r["track"] for r in rows)==Counter({"boundary":120,"capability":80,"instruction":60,"termination":40})
    fam=defaultdict(list)
    for r in rows:
        assert r["messages"] and r["messages"][0]["role"]=="user"
        assert r["max_tokens"]>0
        kind=r["grading"]["type"]
        assert kind in {"exact_text","numeric","json_exact","contains","regex","behavior_observation"}
        if r["track"]=="boundary":
            fam[r["family_id"]].append(r["boundary_level_index"])
            assert kind=="behavior_observation"
        else:
            score,_=grade("__definitely_wrong__",r["grading"])
            assert score is not None
    assert len(fam)==30
    assert all(sorted(v)==[0,1,2,3] for v in fam.values())
    print("dataset_valid=1")
    print("cases=300 boundary_families=30")
    print("tracks="+json.dumps(Counter(r["track"] for r in rows),sort_keys=True))
if __name__=="__main__": main()
