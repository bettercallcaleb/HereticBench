#!/usr/bin/env python3
import argparse
import re
from collections import Counter, defaultdict
from statistics import mean
from hereticbench.common import classify_behavior, detect_reasoning_refusal_signal, load_jsonl
from hereticbench.grading import grade

LEVELS = ["benign", "ambiguous", "dual_use", "harmful"]

def index(rows):
    return {r["id"]: r for r in rows if r.get("status") == "ok"}

def ptok(r):
    return (r.get("usage") or {}).get("prompt_tokens")

def ctok(r):
    return (r.get("usage") or {}).get("completion_tokens", 0) or 0

def current_score(r):
    return grade(r.get("content", ""), r["grading"])

def behavior(r):
    return classify_behavior(r.get("content", ""))

def reasoning_behavior(r):
    text = r.get("reasoning_content", "")
    return {
        "present": bool(text.strip()),
        "refusal_signal": detect_reasoning_refusal_signal(text),
    }

def guess_quant(r):
    q = str(r.get("quantization") or "")
    if q and q != "unknown":
        return q
    text = str(r.get("server_model_path") or r.get("model") or "")
    m = re.search(r"(?i)(?:UD-)?(?:IQ|Q)\d(?:_[A-Z0-9]+)+", text)
    return m.group(0) if m else "unknown"

def first_refusal_for_family(rows):
    levels = {r.get("boundary_level_index"): behavior(r) for r in rows}
    if len(levels) != 4 or any(not levels[i]["determinate"] for i in range(4)):
        return None
    for i in range(4):
        if levels[i]["refused"]:
            return i
    return 4

def main():
    p = argparse.ArgumentParser()
    p.add_argument("base")
    p.add_argument("variant")
    p.add_argument("--allow-protocol-violations", action="store_true")
    a = p.parse_args()

    A = index(load_jsonl(a.base))
    B = index(load_jsonl(a.variant))
    ids = sorted(set(A) & set(B))
    if not ids:
        raise SystemExit("No paired successful cases")

    issues = []
    warnings = []
    same_msg = sum(A[i].get("messages") == B[i].get("messages") for i in ids)
    same_grade = sum(A[i].get("grading") == B[i].get("grading") for i in ids)
    if same_msg != len(ids):
        issues.append("MESSAGE_MISMATCH")
    if same_grade != len(ids):
        issues.append("GRADING_MISMATCH")

    dsa = {A[i].get("dataset_sha256") for i in ids}
    dsb = {B[i].get("dataset_sha256") for i in ids}
    if dsa != dsb:
        issues.append("DATASET_HASH_MISMATCH")

    deltas = []
    missing = 0
    for i in ids:
        pa, pb = ptok(A[i]), ptok(B[i])
        if pa is None or pb is None:
            missing += 1
        else:
            deltas.append(pb - pa)
    unique_delta = sorted(set(deltas))
    if deltas and any(d != 0 for d in deltas):
        warnings.append("PROMPT_TOKEN_MISMATCH")

    ta = {str(A[i].get("server_chat_template_sha256") or A[i].get("chat_template_sha256") or "unknown") for i in ids}
    tb = {str(B[i].get("server_chat_template_sha256") or B[i].get("chat_template_sha256") or "unknown") for i in ids}
    ea = {str(A[i].get("effective_template_probe_sha256") or "unknown") for i in ids}
    eb = {str(B[i].get("effective_template_probe_sha256") or "unknown") for i in ids}
    known_ea = {x for x in ea if x != "unknown"}
    known_eb = {x for x in eb if x != "unknown"}
    if known_ea and known_eb and known_ea != known_eb:
        warnings.append("EFFECTIVE_CHAT_TEMPLATE_MISMATCH")

    qa = sorted({guess_quant(A[i]) for i in ids})
    qb = sorted({guess_quant(B[i]) for i in ids})
    if qa != qb and qa != ["unknown"] and qb != ["unknown"]:
        warnings.append("QUANTIZATION_MISMATCH")

    effort_a = {str(A[i].get("reasoning_effort", "unknown")) for i in ids}
    effort_b = {str(B[i].get("reasoning_effort", "unknown")) for i in ids}
    if effort_a != effort_b and effort_a != {"unknown"} and effort_b != {"unknown"}:
        issues.append("REASONING_EFFORT_MISMATCH")

    ra_none = [i for i in ids if A[i].get("reasoning_effort") == "none"]
    rb_none = [i for i in ids if B[i].get("reasoning_effort") == "none"]
    a_reasoning_violation = sum(bool(A[i].get("reasoning_content", "").strip()) for i in ra_none)
    b_reasoning_violation = sum(bool(B[i].get("reasoning_content", "").strip()) for i in rb_none)
    if a_reasoning_violation or b_reasoning_violation:
        issues.append("REASONING_PRESENT_WHEN_NONE")

    print("=== PAIR AUDIT ===")
    print(f"paired={len(ids)} same_messages={same_msg}/{len(ids)} same_grading={same_grade}/{len(ids)}")
    print(f"dataset_hash_base={sorted(dsa)}")
    print(f"dataset_hash_variant={sorted(dsb)}")
    print(f"prompt_token_pairs={len(deltas)} missing={missing} unique_variant_minus_base={unique_delta[:20]}")
    print(f"quantization_base={qa} variant={qb}")
    print(f"reasoning_effort_base={sorted(effort_a)} variant={sorted(effort_b)}")
    print(f"reasoning_when_none_base={a_reasoning_violation}/{len(ra_none)} variant={b_reasoning_violation}/{len(rb_none)}")

    print("\n=== SCORED TRACKS ===")
    print("track          n    base  variant   delta  base_len  var_len  base_empty var_empty")
    print("------------- ---  ------  -------  ------  --------  -------  ---------- ---------")
    for track in ["capability", "instruction", "termination"]:
        qids = [i for i in ids if A[i].get("track") == track]
        pairs = []
        for i in qids:
            sa, _ = current_score(A[i])
            sb, _ = current_score(B[i])
            if sa is not None and sb is not None:
                pairs.append((i, sa, sb))
        if not pairs:
            continue
        ba = mean(x[1] for x in pairs)
        vb = mean(x[2] for x in pairs)
        la = mean(A[x[0]].get("raw_finish_reason") == "length" for x in pairs)
        lb = mean(B[x[0]].get("raw_finish_reason") == "length" for x in pairs)
        ea = mean(not bool(A[x[0]].get("content", "").strip()) for x in pairs)
        eb = mean(not bool(B[x[0]].get("content", "").strip()) for x in pairs)
        print(f"{track:13s} {len(pairs):3d}  {ba:6.3f}  {vb:7.3f}  {vb-ba:+6.3f}   {la:7.3f}  {lb:7.3f}    {ea:7.3f}   {eb:7.3f}")

    print("\n=== BOUNDARY PROFILE ===")
    print("level            n  base_det base_ref|det base_no_final  var_det var_ref|det var_no_final")
    print("--------------- ---  -------- ------------ -------------  ------- ----------- ------------")
    for level in LEVELS:
        qids = [i for i in ids if A[i].get("track") == "boundary" and A[i].get("boundary_level") == level]
        if not qids:
            continue
        ba = [behavior(A[i]) for i in qids]
        vb = [behavior(B[i]) for i in qids]
        ba_det = [x for x in ba if x["determinate"]]
        vb_det = [x for x in vb if x["determinate"]]
        br = mean(x["refused"] for x in ba_det) if ba_det else float("nan")
        vr = mean(x["refused"] for x in vb_det) if vb_det else float("nan")
        bnf = mean(not x["determinate"] for x in ba)
        vnf = mean(not x["determinate"] for x in vb)
        print(f"{level:15s} {len(qids):3d}  {len(ba_det):8d} {br:12.3f} {bnf:13.3f}  {len(vb_det):7d} {vr:11.3f} {vnf:12.3f}")

    print("\n=== REASONING -> FINAL SAFETY PATH ===")
    print("level            n  base_rsn base_rsn_ref base_final_ref  var_rsn var_rsn_ref var_final_ref")
    print("--------------- ---  -------- ------------ --------------  ------- ----------- -------------")
    for level in LEVELS:
        qids = [i for i in ids if A[i].get("track") == "boundary" and A[i].get("boundary_level") == level]
        if not qids:
            continue
        def path_stats(M):
            rsn = [reasoning_behavior(M[i]) for i in qids]
            fin = [behavior(M[i]) for i in qids]
            rsn_present = [x for x in rsn if x["present"]]
            fin_det = [x for x in fin if x["determinate"]]
            return (
                len(rsn_present),
                mean(x["refusal_signal"] for x in rsn_present) if rsn_present else float("nan"),
                mean(x["refused"] for x in fin_det) if fin_det else float("nan"),
            )
        ar, arr, afr = path_stats(A)
        brn, brr, bfr = path_stats(B)
        print(f"{level:15s} {len(qids):3d}  {ar:8d} {arr:12.3f} {afr:14.3f}  {brn:7d} {brr:11.3f} {bfr:13.3f}")

    af = defaultdict(list)
    bf = defaultdict(list)
    for i in ids:
        if A[i].get("track") == "boundary":
            af[A[i]["family_id"]].append(A[i])
            bf[B[i]["family_id"]].append(B[i])
    common_fams = sorted(set(af) & set(bf))
    usable = []
    shifts = []
    for fam in common_fams:
        ia = first_refusal_for_family(af[fam])
        ib = first_refusal_for_family(bf[fam])
        if ia is not None and ib is not None:
            usable.append((fam, ia, ib))
            shifts.append(ib - ia)
    print(f"\nboundary_families={len(common_fams)} fully_determinate_paired_families={len(usable)}")
    if usable:
        print(f"mean_first_refusal_index_base={mean(x[1] for x in usable):.3f} variant={mean(x[2] for x in usable):.3f} mean_shift={mean(shifts):+.3f}")
        print("index: 0=benign refusal, 1=ambiguous, 2=dual_use, 3=harmful, 4=no refusal")
        print("shift_histogram=" + str(dict(sorted(Counter(shifts).items()))))
    else:
        print("boundary_shift=INDETERMINATE_DUE_TO_MISSING_FINAL_OUTPUTS")

    print("\n=== TOKEN / TERMINATION ===")
    print(f"avg_completion_tokens base={mean(ctok(A[i]) for i in ids):.1f} variant={mean(ctok(B[i]) for i in ids):.1f}")
    print(f"length_finish_rate base={mean(A[i].get('raw_finish_reason')=='length' for i in ids):.3f} variant={mean(B[i].get('raw_finish_reason')=='length' for i in ids):.3f}")
    print(f"empty_final_rate base={mean(not bool(A[i].get('content','').strip()) for i in ids):.3f} variant={mean(not bool(B[i].get('content','').strip()) for i in ids):.3f}")

    regress = []
    improve = []
    for i in ids:
        sa, _ = current_score(A[i])
        sb, _ = current_score(B[i])
        if sa is None or sb is None:
            continue
        if sa > sb:
            regress.append(i)
        elif sb > sa:
            improve.append(i)
    print(f"scored_regressions={len(regress)} scored_improvements={len(improve)}")
    if regress:
        print("regressions=" + " ".join(regress[:60]))
    if improve:
        print("improvements=" + " ".join(improve[:60]))

    warnings = sorted(set(warnings))
    if warnings:
        print("\nINFO WARNINGS: " + ", ".join(warnings))
    issues = sorted(set(issues))
    if issues:
        print("\nPROTOCOL ISSUES: " + ", ".join(issues))
        if not a.allow_protocol_violations:
            print("RESULT STATUS: CONFOUNDED")
            raise SystemExit(2)
    print("\nRESULT STATUS: VALID CONFIGURATION COMPARISON" if not issues else "\nRESULT STATUS: comparison complete with allowed protocol violations")

if __name__ == "__main__":
    main()
