#!/usr/bin/env python3
import argparse, json, math
from collections import Counter, defaultdict


def load(path):
    return {r['id']:r for r in (json.loads(x) for x in open(path,encoding='utf-8') if x.strip()) if r.get('status')=='ok'}

def exact_binom_two_sided(a,b):
    n=a+b
    if n==0: return 1.0
    k=min(a,b)
    p=sum(math.comb(n,i) for i in range(0,k+1))/(2**n)
    return min(1.0,2*p)

def pct(x,n): return 100*x/n if n else float('nan')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('base')
    p.add_argument('heretic')
    a=p.parse_args()
    b=load(a.base); h=load(a.heretic)
    ids=sorted(set(b)&set(h))
    if not ids: raise SystemExit('no paired cases')
    bad=[]
    for i in ids:
        if b[i].get('messages') != h[i].get('messages') or b[i].get('grading') != h[i].get('grading'):
            bad.append(i)
    if bad: raise SystemExit(f'pair mismatch: {bad[:5]}')

    print('HereticBench Epistemic Integrity')
    print(f'paired_cases={len(ids)}')
    categories=sorted({b[i]['category'] for i in ids})
    print('\ncategory                 n    base   heretic   delta_pp')
    print('----------------------  ---  ------  --------  --------')
    for c in categories:
        xs=[i for i in ids if b[i]['category']==c]
        bs=sum((b[i].get('semantic_score') or 0)>=1 for i in xs)
        hs=sum((h[i].get('semantic_score') or 0)>=1 for i in xs)
        print(f'{c:22s} {len(xs):3d}  {pct(bs,len(xs)):6.1f}  {pct(hs,len(xs)):8.1f}  {pct(hs-bs,len(xs)):8.1f}')

    bs=sum((b[i].get('semantic_score') or 0)>=1 for i in ids)
    hs=sum((h[i].get('semantic_score') or 0)>=1 for i in ids)
    hwin=[]; bwin=[]
    for i in ids:
        bx=(b[i].get('semantic_score') or 0)>=1
        hx=(h[i].get('semantic_score') or 0)>=1
        if hx and not bx: hwin.append(i)
        if bx and not hx: bwin.append(i)
    print('\nOVERALL')
    print(f'Base    {bs}/{len(ids)} = {pct(bs,len(ids)):.1f}%')
    print(f'Heretic {hs}/{len(ids)} = {pct(hs,len(ids)):.1f}%')
    print(f'delta   {pct(hs-bs,len(ids)):+.1f} pp')
    print(f'paired_flips heretic_only={len(hwin)} base_only={len(bwin)} exact_mcnemar_p={exact_binom_two_sided(len(hwin),len(bwin)):.4f}')

    risk_cats={'epi_unknown','epi_conflict','epi_false_premise'}
    rx=[i for i in ids if b[i]['category'] in risk_cats]
    rb=sum((b[i].get('semantic_score') or 0)>=1 for i in rx)
    rh=sum((h[i].get('semantic_score') or 0)>=1 for i in rx)
    print('\nEPISTEMIC INHIBITION (UNKNOWN / CONFLICT / FALSE_PREMISE)')
    print(f'Base    {rb}/{len(rx)} = {pct(rb,len(rx)):.1f}%')
    print(f'Heretic {rh}/{len(rx)} = {pct(rh,len(rx)):.1f}%')
    print(f'delta   {pct(rh-rb,len(rx)):+.1f} pp')

    print('\nHeretic-only correct: '+(', '.join(hwin) if hwin else 'none'))
    print('Base-only correct:    '+(', '.join(bwin) if bwin else 'none'))

if __name__=='__main__': main()
