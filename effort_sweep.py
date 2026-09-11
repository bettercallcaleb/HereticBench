#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    p.add_argument("--label", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--efforts", default="low,medium,xhigh")
    p.add_argument("--tracks", default="boundary")
    p.add_argument("--boundary-levels", default="harmful")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--max-tokens", type=int, default=None)
    p.add_argument("--timeout", type=int, default=600)
    a = p.parse_args()
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for effort in [x.strip() for x in a.efforts.split(",") if x.strip()]:
        out = out_dir / f"{a.label}-{effort}.jsonl"
        cmd = [sys.executable, "run_benchmark.py", "--base-url", a.base_url,
               "--out", str(out), "--label", f"{a.label}-{effort}",
               "--tracks", a.tracks, "--effort", effort, "--timeout", str(a.timeout)]
        if a.boundary_levels:
            cmd += ["--boundary-levels", a.boundary_levels]
        if a.limit is not None:
            cmd += ["--limit", str(a.limit)]
        if a.max_tokens is not None:
            cmd += ["--max-tokens", str(a.max_tokens)]
        print("RUN", " ".join(cmd), flush=True)
        rc = subprocess.call(cmd)
        if rc != 0:
            raise SystemExit(rc)

if __name__ == "__main__":
    main()
