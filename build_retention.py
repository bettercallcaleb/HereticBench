#!/usr/bin/env python3
import argparse
import heapq
import itertools
import json
import random
from pathlib import Path

TIERS = ["easy", "medium", "hard", "very_hard"]
TIER_INDEX = {x: i for i, x in enumerate(TIERS)}


def row(qid, category, prompt, grading, tier, max_tokens=4096, messages=None):
    return {
        "id": qid,
        "track": "retention",
        "category": category,
        "messages": messages or [{"role": "user", "content": prompt}],
        "grading": grading,
        "max_tokens": max_tokens,
        "difficulty": tier,
        "difficulty_tier": tier,
    }


def state_case(seed, tier):
    r = random.Random(seed)
    idx = TIER_INDEX[tier]
    nvars = [4, 5, 6, 7][idx]
    nops = [14, 22, 30, 40][idx]
    names = [chr(ord("A") + i) for i in range(nvars)]
    s = {k: r.randint(4, 16) for k in names}
    start = dict(s)
    ops = []
    for _ in range(nops):
        typ = r.randrange(6)
        x, y = r.sample(names, 2)
        z = r.choice(names)
        if typ == 0:
            d = r.randint(1, 7)
            if r.random() < 0.5:
                d = -d
            s[x] += d
            ops.append(f"add {d} to {x}")
        elif typ == 1:
            s[x], s[y] = s[y], s[x]
            ops.append(f"swap {x} and {y}")
        elif typ == 2:
            d = r.randint(1, 5)
            s[x] -= d
            s[y] += d
            ops.append(f"move {d} from {x} to {y}")
        elif typ == 3:
            d = r.randint(1, 5)
            if s[x] > s[y]:
                s[z] += d
                ops.append(f"if {x} > {y}, add {d} to {z}; otherwise subtract {d} from {z}")
            else:
                s[z] -= d
                ops.append(f"if {x} > {y}, add {d} to {z}; otherwise subtract {d} from {z}")
        elif typ == 4:
            m = r.randint(2, 5)
            d = r.randint(1, 4)
            if (s[x] + s[y]) % m == 0:
                s[z] += d
            else:
                s[z] -= d
            ops.append(f"if ({x}+{y}) is divisible by {m}, add {d} to {z}; otherwise subtract {d} from {z}")
        else:
            m = r.randint(3, 8)
            c = r.randint(0, 3)
            s[x] += (s[y] % m) - c
            ops.append(f"replace {x} with {x} + ({y} mod {m}) - {c}")
    start_txt = ", ".join(f"{k}={start[k]}" for k in names)
    prompt = f"Start with {start_txt}. Apply these operations in order:\n" + "\n".join(f"{i+1}. {op}" for i, op in enumerate(ops))
    prompt += "\nReturn exactly one line containing all final variables in alphabetical order as A=?,B=?,... with no explanation."
    return prompt, s


def code_case(seed, tier):
    r = random.Random(seed)
    idx = TIER_INDEX[tier]
    n = [6, 9, 13, 17][idx]
    m = [2, 3, 4, 5][idx]
    x = r.randint(2, 8)
    y = r.randint(3, 9)
    arr = [r.randint(1, 9) for _ in range([4, 5, 6, 7][idx])]
    mod1 = r.randint(3, 6)
    mod2 = r.randint(2, 5)
    x0, y0, a0 = x, y, arr[:]
    for i in range(n):
        j = (i + x) % len(arr)
        if (arr[j] + x + i) % mod1 == 0:
            y += arr[j] - (i % 4)
            x += (y % mod2) - 1
        elif (y + i) % 2 == 0:
            arr[j] += x - (i % 5)
            y -= j
        else:
            x += arr[j] % mod2
            arr[j] -= (x + i) % 4
    for k in range(m):
        j = (y + k) % len(arr)
        t = arr[j]
        if (t + x + y) % 2 == 0:
            x -= k + 1
            y += t % 5
        else:
            y -= t % 4
            arr[j] += (x % 3) - k
    expected = [x, y, sum(arr), arr[0] - arr[-1]]
    code = f'''x = {x0}\ny = {y0}\na = {a0}\nfor i in range({n}):\n    j = (i + x) % len(a)\n    if (a[j] + x + i) % {mod1} == 0:\n        y += a[j] - (i % 4)\n        x += (y % {mod2}) - 1\n    elif (y + i) % 2 == 0:\n        a[j] += x - (i % 5)\n        y -= j\n    else:\n        x += a[j] % {mod2}\n        a[j] -= (x + i) % 4\nfor k in range({m}):\n    j = (y + k) % len(a)\n    t = a[j]\n    if (t + x + y) % 2 == 0:\n        x -= k + 1\n        y += t % 5\n    else:\n        y -= t % 4\n        a[j] += (x % 3) - k\nprint(x, y, sum(a), a[0] - a[-1])'''
    prompt = "Without running code, trace this Python program. Return exactly the four printed integers separated by single spaces, with no explanation:\n\n" + code
    return prompt, expected


def _check_constraint(c, pos):
    typ = c[0]
    if typ == "pos":
        return pos[c[1]] == c[2]
    if typ == "before":
        return pos[c[1]] < pos[c[2]]
    if typ == "adj":
        return abs(pos[c[1]] - pos[c[2]]) == 1
    if typ == "not_adj":
        return abs(pos[c[1]] - pos[c[2]]) != 1
    if typ == "gap":
        return abs(pos[c[1]] - pos[c[2]]) == c[3]
    if typ == "between":
        return abs(pos[c[1]] - pos[c[2]]) - 1 == c[3]
    raise ValueError(c)


def _constraint_text(c):
    typ = c[0]
    if typ == "pos":
        return f"{c[1]} is in position {c[2]}."
    if typ == "before":
        return f"{c[1]} is before {c[2]}."
    if typ == "adj":
        return f"{c[1]} is adjacent to {c[2]}."
    if typ == "not_adj":
        return f"{c[1]} is not adjacent to {c[2]}."
    if typ == "gap":
        return f"The positions of {c[1]} and {c[2]} differ by exactly {c[3]}."
    if typ == "between":
        return f"Exactly {c[3]} item(s) are between {c[1]} and {c[2]}."
    raise ValueError(c)


def assignment_case(seed, tier):
    r = random.Random(seed)
    idx = TIER_INDEX[tier]
    n = [6, 7, 8, 8][idx]
    items = [chr(ord("A") + i) for i in range(n)]
    max_positions = [3, 2, 1, 0][idx]
    for attempt in range(200):
        sol = items[:]
        r.shuffle(sol)
        pos = {x: i + 1 for i, x in enumerate(sol)}
        candidates = []
        for x in items:
            if max_positions > 0:
                candidates.append(("pos", x, pos[x]))
        for x, y in itertools.combinations(items, 2):
            if pos[x] < pos[y]:
                candidates.append(("before", x, y))
            else:
                candidates.append(("before", y, x))
            d = abs(pos[x] - pos[y])
            if d == 1:
                candidates.append(("adj", x, y))
            else:
                candidates.append(("not_adj", x, y))
            if d in (2, 3):
                candidates.append(("gap", x, y, d))
            if 1 <= d - 1 <= 3:
                candidates.append(("between", x, y, d - 1))
        r.shuffle(candidates)
        chosen = []
        used_pos = 0
        perms = list(itertools.permutations(items))
        valid = perms
        for c in candidates:
            if c[0] == "pos" and used_pos >= max_positions:
                continue
            nv = []
            for perm in valid:
                p = {x: i + 1 for i, x in enumerate(perm)}
                if _check_constraint(c, p):
                    nv.append(perm)
            if len(nv) < len(valid):
                chosen.append(c)
                valid = nv
                if c[0] == "pos":
                    used_pos += 1
            if len(valid) == 1:
                break
        if len(valid) != 1:
            continue
        changed = True
        while changed:
            changed = False
            for c in chosen[:]:
                trial = [x for x in chosen if x is not c]
                vv = []
                for perm in perms:
                    p = {x: i + 1 for i, x in enumerate(perm)}
                    if all(_check_constraint(x, p) for x in trial):
                        vv.append(perm)
                        if len(vv) > 1:
                            break
                if len(vv) == 1:
                    chosen.remove(c)
                    changed = True
        r.shuffle(chosen)
        prompt = f"{n} items {', '.join(items)} occupy positions 1 through {n}, one each.\n" + "\n".join(f"- {_constraint_text(c)}" for c in chosen)
        prompt += f"\nReturn only the sequence from position 1 to {n} as {n} letters with no spaces."
        expected = "".join(valid[0])
        return prompt, expected
    raise RuntimeError(f"failed assignment generation seed={seed} tier={tier}")


def _dijkstra(nodes, edges, start, target):
    g = {n: [] for n in nodes}
    for a, b, w in edges:
        g[a].append((b, w))
        g[b].append((a, w))
    pq = [(0, (start,), start)]
    best = {start: (0, (start,))}
    while pq:
        d, path, u = heapq.heappop(pq)
        if best.get(u) != (d, path):
            continue
        if u == target:
            return d, list(path)
        for v, w in g[u]:
            cand = (d + w, path + (v,))
            if v not in best or cand < best[v]:
                best[v] = cand
                heapq.heappush(pq, (cand[0], cand[1], v))
    raise RuntimeError("disconnected")


def graph_case(seed, tier):
    r = random.Random(seed)
    idx = TIER_INDEX[tier]
    n = [6, 8, 10, 12][idx]
    nodes = [chr(ord("A") + i) for i in range(n)]
    edges = []
    seen = set()
    for i in range(1, n):
        j = r.randrange(i)
        a, b = nodes[i], nodes[j]
        key = tuple(sorted((a, b)))
        w = r.randint(2, 14)
        edges.append((a, b, w)); seen.add(key)
    extra = [4, 8, 13, 19][idx]
    while extra > 0:
        a, b = r.sample(nodes, 2)
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        edges.append((a, b, r.randint(2, 18)))
        extra -= 1
    start, target = nodes[0], nodes[-1]
    dist, path = _dijkstra(nodes, edges, start, target)
    edge_txt = ", ".join(f"{a}-{b}:{w}" for a, b, w in sorted(edges))
    expected = f"{dist}|{'-'.join(path)}"
    prompt = f"Undirected weighted graph. Edges are NODE-NODE:WEIGHT: {edge_txt}. Find the minimum-cost path from {start} to {target}. If multiple paths have the same minimum cost, choose the lexicographically smallest node sequence. Return only COST|PATH, for example 17|A-C-F, with no explanation."
    return prompt, expected


def boolean_case(seed, tier):
    r = random.Random(seed)
    idx = TIER_INDEX[tier]
    nvars = [5, 6, 7, 8][idx]
    nops = [14, 22, 32, 44][idx]
    names = [chr(ord("A") + i) for i in range(nvars)]
    s = {k: r.randint(0, 1) for k in names}
    start = dict(s)
    ops = []
    for _ in range(nops):
        out = r.choice(names)
        a, b = r.sample(names, 2)
        typ = r.randrange(5)
        if typ == 0:
            s[out] = s[a] ^ s[b]
            ops.append(f"{out} = {a} XOR {b}")
        elif typ == 1:
            s[out] = s[a] & s[b]
            ops.append(f"{out} = {a} AND {b}")
        elif typ == 2:
            s[out] = s[a] | s[b]
            ops.append(f"{out} = {a} OR {b}")
        elif typ == 3:
            s[out] = 1 - s[a]
            ops.append(f"{out} = NOT {a}")
        else:
            c = r.choice(names)
            s[out] = (s[a] ^ s[b]) & (1 - s[c])
            ops.append(f"{out} = ({a} XOR {b}) AND (NOT {c})")
    start_txt = ", ".join(f"{k}={start[k]}" for k in names)
    prompt = f"Boolean values use 0=false and 1=true. Start with {start_txt}. Apply each assignment in order, overwriting the left-hand variable:\n" + "\n".join(f"{i+1}. {op}" for i, op in enumerate(ops))
    prompt += "\nReturn exactly one line containing every final variable in alphabetical order as A=0,B=1,... with no explanation."
    return prompt, s


GENERATORS = {
    "state_tracking_v3": state_case,
    "code_trace_v3": code_case,
    "constraint_assignment_v3": assignment_case,
    "graph_shortest_v3": graph_case,
    "boolean_circuit_v3": boolean_case,
}


def build_calibration(out_path, per_cell=8):
    rows = []
    for cidx, (category, fn) in enumerate(GENERATORS.items()):
        for tidx, tier in enumerate(TIERS):
            for i in range(per_cell):
                seed = 300000 + cidx * 10000 + tidx * 1000 + i
                prompt, expected = fn(seed, tier)
                qid = f"CAL_{category.upper()}_{tier.upper()}_{i+1:02d}"
                if category in {"state_tracking_v3", "boolean_circuit_v3"}:
                    grading = {"type": "kv_state", "expected": expected}
                elif category == "code_trace_v3":
                    grading = {"type": "int_tuple", "expected": expected}
                elif category == "constraint_assignment_v3":
                    grading = {"type": "sequence", "expected": expected, "alphabet": "ABCDEFGH"}
                else:
                    grading = {"type": "token_text", "expected": expected, "pattern": r"\b\d+\|[A-Z](?:-[A-Z])+\b"}
                rows.append(row(qid, category, prompt, grading, tier))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for x in rows:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data/retention_calibration.jsonl")
    p.add_argument("--per-cell", type=int, default=8)
    a = p.parse_args()
    rows = build_calibration(a.out, a.per_cell)
    print(f"wrote {len(rows)} calibration cases to {a.out}")
    for cat in GENERATORS:
        print(cat, sum(x["category"] == cat for x in rows))


if __name__ == "__main__":
    main()
