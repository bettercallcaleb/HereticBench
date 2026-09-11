from collections import defaultdict
from .common import classify_behavior


def _completion_tokens(row):
    return (row.get("usage") or {}).get("completion_tokens", 0) or 0


def _metric(row, key, fallback=None):
    v = row.get(key)
    if v is None and fallback:
        v = row.get(fallback)
    return v


def summarize(records):
    by_track = defaultdict(list)
    for r in records:
        if r.get("status") == "ok":
            by_track[r["track"]].append(r)
    out = {}
    for track, rows in sorted(by_track.items()):
        semantic = [x for x in rows if _metric(x, "semantic_score", "score") is not None]
        fmt = [x for x in rows if _metric(x, "format_score", "score") is not None]
        s = {
            "n": len(rows),
            "n_scored": len(semantic),
            "mean_score": (sum(_metric(x, "semantic_score", "score") for x in semantic) / len(semantic)) if semantic else None,
            "mean_semantic_score": (sum(_metric(x, "semantic_score", "score") for x in semantic) / len(semantic)) if semantic else None,
            "mean_format_score": (sum(_metric(x, "format_score", "score") for x in fmt) / len(fmt)) if fmt else None,
            "avg_seconds": sum(x.get("elapsed_seconds", 0.0) for x in rows) / len(rows) if rows else 0.0,
            "avg_completion_tokens": sum(_completion_tokens(x) for x in rows) / len(rows) if rows else 0.0,
            "length_finish_rate": sum(x.get("raw_finish_reason") == "length" for x in rows) / len(rows) if rows else 0.0,
            "empty_final_rate": sum(not bool(x.get("content", "").strip()) for x in rows) / len(rows) if rows else 0.0,
            "reasoning_present_rate": sum(bool(x.get("reasoning_content", "").strip()) for x in rows) / len(rows) if rows else 0.0,
        }
        by_category = defaultdict(list)
        for x in rows:
            by_category[x.get("category", "unknown")].append(x)
        s["categories"] = {}
        for cat, cr in sorted(by_category.items()):
            ss = [x for x in cr if _metric(x, "semantic_score", "score") is not None]
            ff = [x for x in cr if _metric(x, "format_score", "score") is not None]
            s["categories"][cat] = {
                "n": len(cr),
                "semantic": sum(_metric(x, "semantic_score", "score") for x in ss) / len(ss) if ss else None,
                "format": sum(_metric(x, "format_score", "score") for x in ff) / len(ff) if ff else None,
            }
        if track == "boundary":
            by_level = defaultdict(list)
            for x in rows:
                by_level[x.get("boundary_level", "unknown")].append(x)
            s["levels"] = {}
            for level, level_rows in sorted(by_level.items(), key=lambda kv: min(x.get("boundary_level_index", 99) for x in kv[1])):
                behaviors = [classify_behavior(x.get("content", "")) for x in level_rows]
                det = [x for x in behaviors if x["determinate"]]
                s["levels"][level] = {
                    "n": len(level_rows),
                    "determinate_n": len(det),
                    "refusal_rate_determinate": (sum(x["refused"] for x in det) / len(det)) if det else None,
                    "caution_rate_determinate": (sum(x["caution"] for x in det) / len(det)) if det else None,
                    "no_final_rate": sum(not x["determinate"] for x in behaviors) / len(behaviors),
                    "length_finish_rate": sum(x.get("raw_finish_reason") == "length" for x in level_rows) / len(level_rows),
                }
        out[track] = s
    return out


def print_summary(summary):
    print("\n=== HereticBench v1.0.0 summary ===")
    for track, s in summary.items():
        sem = "n/a" if s["mean_semantic_score"] is None else f"{s['mean_semantic_score']:.3f}"
        fmt = "n/a" if s["mean_format_score"] is None else f"{s['mean_format_score']:.3f}"
        print(f"{track:18s} n={s['n']:3d} semantic={sem:>5s} format={fmt:>5s} avg_s={s['avg_seconds']:.2f} avg_ctok={s['avg_completion_tokens']:.1f} length={s['length_finish_rate']:.3f} empty={s['empty_final_rate']:.3f}")
        for cat, cs in s.get("categories", {}).items():
            csem = "n/a" if cs["semantic"] is None else f"{cs['semantic']:.3f}"
            cfmt = "n/a" if cs["format"] is None else f"{cs['format']:.3f}"
            print(f"  {cat:24s} n={cs['n']:3d} semantic={csem:>5s} format={cfmt:>5s}")
