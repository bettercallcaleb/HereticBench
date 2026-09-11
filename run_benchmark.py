#!/usr/bin/env python3
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from hereticbench.client import OpenAICompatClient
from hereticbench.common import classify_behavior, dump_jsonl, load_jsonl
from hereticbench.grading import grade_dual
from hereticbench.reporting import print_summary, summarize

META_KEYS = ["family_id", "boundary_level", "boundary_level_index", "difficulty", "difficulty_tier"]

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_text(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    p.add_argument("--questions", default="data/questions.jsonl")
    p.add_argument("--out", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--model", default=None)
    p.add_argument("--tracks", default=None)
    p.add_argument("--boundary-levels", default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--max-tokens", type=int, default=None)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--effort", default="medium", choices=["default","native","none","low","medium","high","xhigh","max"])
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--quantization", default="unknown")
    p.add_argument("--source-model", default="unknown")
    p.add_argument("--notes", default="")
    p.add_argument("--parity-reference", default=None)
    p.add_argument("--allow-reasoning-when-none", action="store_true")
    return p.parse_args()

def main():
    args = parse_args()
    questions = load_jsonl(args.questions)
    dataset_sha256 = sha256_file(args.questions)
    if args.tracks:
        allowed = {x.strip() for x in args.tracks.split(",") if x.strip()}
        questions = [q for q in questions if q["track"] in allowed]
    if args.boundary_levels:
        levels = {x.strip() for x in args.boundary_levels.split(",") if x.strip()}
        questions = [q for q in questions if q.get("track") != "boundary" or q.get("boundary_level") in levels]
    if args.limit is not None:
        questions = questions[:args.limit]

    reference = {}
    ref_effective_template_sha = None
    if args.parity_reference:
        reference = {r["id"]: r for r in load_jsonl(args.parity_reference) if r.get("status") == "ok"}
        vals = {r.get("effective_template_probe_sha256") for r in reference.values() if r.get("effective_template_probe_sha256")}
        if len(vals) == 1:
            ref_effective_template_sha = next(iter(vals))

    out_path = Path(args.out)
    existing = []
    done = set()
    if args.resume and out_path.exists():
        existing = load_jsonl(out_path)
        done = {r["id"] for r in existing if r.get("status") == "ok"}

    client = OpenAICompatClient(args.base_url, timeout=args.timeout)
    if args.model is None:
        try:
            models = client.models().get("data", [])
            args.model = models[0]["id"] if models else None
        except Exception as e:
            print(f"WARNING: model discovery failed: {e}", file=sys.stderr)

    props = {}
    try:
        props = client.props()
    except Exception as e:
        print(f"WARNING: GET /props failed: {e}", file=sys.stderr)
    server_model_path = props.get("model_path") or args.model
    server_build_info = props.get("build_info") or "unknown"
    server_template_sha = "ignored"
    effective_template_sha = "ignored"

    run_meta = {
        "hereticbench_version": "1.0.0",
        "dataset_sha256": dataset_sha256,
        "endpoint": args.base_url,
        "label": args.label,
        "model": args.model,
        "server_model_path": server_model_path,
        "source_model": args.source_model,
        "quantization": args.quantization,
        "server_build_info": server_build_info,
        "temperature": args.temperature,
        "reasoning_effort": args.effort,
        "notes": args.notes,
        "started_utc": datetime.now(timezone.utc).isoformat(),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.with_suffix(out_path.suffix + ".run.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

    records = list(existing)
    print(f"endpoint={args.base_url} model={args.model} label={args.label} cases={len(questions)} dataset_sha256={dataset_sha256[:12]}")
    print(f"server_build={server_build_info} effort={args.effort}")

    for idx, q in enumerate(questions, 1):
        if q["id"] in done:
            print(f"[{idx}/{len(questions)}] {q['id']} skip")
            continue
        meta = {k: q[k] for k in META_KEYS if k in q}
        print(f"[{idx}/{len(questions)}] {q['id']} {q['track']}/{q['category']}", flush=True)
        record = {
            "id": q["id"], "track": q["track"], "category": q["category"],
            "label": args.label, "model": args.model,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "status": "error", "messages": q["messages"], "grading": q["grading"],
            "dataset_sha256": dataset_sha256,
            "source_model": args.source_model,
            "quantization": args.quantization,
            "server_model_path": server_model_path,
            "server_build_info": server_build_info,
            "reasoning_effort": args.effort,
            **meta,
        }
        try:
            max_tokens = args.max_tokens if args.max_tokens is not None else q.get("max_tokens", 512)
            res = client.chat(q["messages"], model=args.model, max_tokens=max_tokens,
                              temperature=args.temperature, reasoning_effort=args.effort)
            semantic_score, format_score, detail = grade_dual(res["content"], q["grading"])
            score = semantic_score
            behavior = classify_behavior(res.get("content", ""))
            record.update(res)
            record.update({"score": score, "semantic_score": semantic_score, "format_score": format_score, "grade_detail": detail, "status": "ok", "grader_version": "1.0.0"})
            record["diagnostics"] = {
                "length_truncated": res.get("raw_finish_reason") == "length",
                "content_empty": not bool(res.get("content", "").strip()),
                "reasoning_present": bool(res.get("reasoning_content", "").strip()),
                "visible_behavior": behavior,
                "reasoning_behavior": classify_behavior(res.get("reasoning_content", "")),
                "requested_max_tokens": max_tokens,
            }
            stext = "obs" if score is None else f"sem={semantic_score:.0f} fmt={format_score:.0f}"
            usage = res.get("usage") or {}
            print(f"  {stext} finish={res.get('raw_finish_reason')} ptok={usage.get('prompt_tokens')} ctok={usage.get('completion_tokens')} reasoning={int(bool(res.get('reasoning_content','').strip()))} time={res['elapsed_seconds']:.2f}s")

            violation = False
            if args.effort == "none" and res.get("reasoning_content", "").strip():
                print("  PROTOCOL ERROR: reasoning_content is non-empty although --effort none was requested", file=sys.stderr)
                violation = True
                if not args.allow_reasoning_when_none:
                    records.append(record)
                    dump_jsonl(out_path, records)
                    raise SystemExit(3)

            if q["id"] in reference:
                ref_ptok = (reference[q["id"]].get("usage") or {}).get("prompt_tokens")
                cur_ptok = usage.get("prompt_tokens")
                if ref_ptok is not None and cur_ptok is not None and ref_ptok != cur_ptok:
                    print(f"  INFO: prompt token delta reference={ref_ptok} current={cur_ptok}")
            record["protocol_violation"] = violation
        except SystemExit:
            raise
        except Exception as e:
            record["error"] = repr(e)
            print(f"  ERROR {e}", file=sys.stderr)
        records.append(record)
        dump_jsonl(out_path, records)

    summary = summarize(records)
    print_summary(summary)
    summary_path = out_path.with_suffix(out_path.suffix + ".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"results={out_path}")
    print(f"summary={summary_path}")

if __name__ == "__main__":
    main()
