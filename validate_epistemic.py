#!/usr/bin/env python3
import argparse, json
from collections import Counter

ALLOWED={"SUPPORTED","CONTRADICTED","UNKNOWN","CONFLICT","FALSE_PREMISE"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('path', nargs='?', default='data/epistemic_integrity.jsonl')
    a=p.parse_args()
    rows=[json.loads(x) for x in open(a.path,encoding='utf-8') if x.strip()]
    ids=[r['id'] for r in rows]
    assert len(ids)==len(set(ids)), 'duplicate ids'
    assert len(rows)==120, f'expected 120 cases, got {len(rows)}'
    assert all(r['track']=='epistemic' for r in rows)
    exp=[r['grading']['expected'] for r in rows]
    assert set(exp)==ALLOWED, set(exp)
    counts=Counter(exp)
    assert all(counts[x]==24 for x in ALLOWED), counts
    cats=Counter(r['category'] for r in rows)
    fam=Counter(r['family_id'] for r in rows)
    assert len(fam)==24 and all(v==5 for v in fam.values()), fam
    print('dataset_valid=1')
    print(f'cases={len(rows)}')
    print('labels='+json.dumps(dict(sorted(counts.items())),sort_keys=True))
    print('categories='+json.dumps(dict(sorted(cats.items())),sort_keys=True))
    print(f'families={len(fam)}')

if __name__=='__main__': main()
