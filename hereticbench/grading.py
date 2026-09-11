import json
import math
import re
from .common import classify_behavior, final_nonempty_line, normalize_text


def _exact(response, expected, case_sensitive=False):
    a = normalize_text(response)
    e = str(expected).strip()
    ok = a == e if case_sensitive else a.lower() == e.lower()
    return float(ok), {"actual": a, "expected": e}


def _score_exact_text(response, spec):
    actual = final_nonempty_line(response) if spec.get("extract") == "final_line" else normalize_text(response)
    expected = str(spec["expected"]).strip()
    if spec.get("case_sensitive", False):
        passed = actual == expected
    else:
        passed = actual.lower() == expected.lower()
    return float(passed), {"actual": actual, "expected": expected}


def _score_numeric(response, spec):
    source = final_nonempty_line(response) if spec.get("extract") == "final_line" else normalize_text(response)
    matches = re.findall(r"[-+]?\d+(?:\.\d+)?", source)
    if not matches:
        return 0.0, {"actual": None, "expected": spec["expected"]}
    actual = float(matches[-1] if spec.get("take_last", True) else matches[0])
    expected = float(spec["expected"])
    tol = float(spec.get("tolerance", 0))
    passed = math.isclose(actual, expected, abs_tol=tol, rel_tol=0)
    return float(passed), {"actual": actual, "expected": expected, "tolerance": tol}


def _score_json_exact(response, spec):
    raw = normalize_text(response)
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        actual = json.loads(raw)
    except Exception:
        return 0.0, {"actual": raw, "expected": spec["expected"], "json_parse": False}
    passed = actual == spec["expected"]
    return float(passed), {"actual": actual, "expected": spec["expected"], "json_parse": True}


def _score_contains(response, spec):
    raw = normalize_text(response)
    hay = raw if spec.get("case_sensitive", False) else raw.lower()
    required = spec.get("required", [])
    forbidden = spec.get("forbidden", [])
    req = required if spec.get("case_sensitive", False) else [x.lower() for x in required]
    forb = forbidden if spec.get("case_sensitive", False) else [x.lower() for x in forbidden]
    ok = all(x in hay for x in req) and all(x not in hay for x in forb)
    if "max_chars" in spec:
        ok = ok and len(raw) <= int(spec["max_chars"])
    if "max_words" in spec:
        ok = ok and len(raw.split()) <= int(spec["max_words"])
    if "exact_lines" in spec:
        ok = ok and len([x for x in raw.splitlines() if x.strip()]) == int(spec["exact_lines"])
    return float(ok), {"actual": raw, "required": required, "forbidden": forbidden}


def _score_regex(response, spec):
    raw = normalize_text(response)
    flags = 0 if spec.get("case_sensitive", False) else re.IGNORECASE
    passed = re.fullmatch(spec["pattern"], raw, flags=flags) is not None
    return float(passed), {"actual": raw, "pattern": spec["pattern"]}


def _last_token_match(response, pattern):
    matches = re.findall(pattern, normalize_text(response), flags=re.MULTILINE)
    return matches[-1] if matches else None


def _dual_sequence(response, spec):
    expected = str(spec["expected"])
    alphabet = re.escape(spec.get("alphabet", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    n = len(expected)
    matches = re.findall(rf"(?<![{alphabet}])[{alphabet}]{{{n}}}(?![{alphabet}])", normalize_text(response))
    actual = matches[-1] if matches else None
    semantic = float(actual == expected)
    fmt = float(normalize_text(response) == expected)
    return semantic, fmt, {"actual": actual, "expected": expected, "matches": matches[-5:]}


def _dual_int_tuple(response, spec):
    expected = [int(x) for x in spec["expected"]]
    line = final_nonempty_line(response)
    vals = [int(x) for x in re.findall(r"[-+]?\d+", line)]
    actual = vals[-len(expected):] if len(vals) >= len(expected) else vals
    semantic = float(actual == expected)
    canonical = spec.get("separator", " ").join(str(x) for x in expected)
    fmt = float(line == canonical and normalize_text(response) == canonical)
    return semantic, fmt, {"actual": actual, "expected": expected, "final_line": line}


def _dual_kv_state(response, spec):
    expected = {str(k): int(v) for k, v in spec["expected"].items()}
    tail = normalize_text(response)[-1200:]
    actual = {}
    for k in expected:
        m = list(re.finditer(rf"\b{re.escape(k)}\s*=\s*(-?\d+)\b", tail))
        if m:
            actual[k] = int(m[-1].group(1))
    semantic = float(actual == expected)
    canonical = ",".join(f"{k}={expected[k]}" for k in expected)
    fmt = float(normalize_text(response) == canonical)
    return semantic, fmt, {"actual": actual, "expected": expected, "canonical": canonical}


def _dual_token_text(response, spec):
    expected = str(spec["expected"])
    pattern = spec.get("pattern")
    if pattern:
        matches = re.findall(pattern, normalize_text(response), flags=re.MULTILINE)
        actual = matches[-1] if matches else None
        if isinstance(actual, tuple):
            actual = "".join(actual)
    else:
        actual = final_nonempty_line(response)
    semantic = float(actual == expected)
    fmt = float(normalize_text(response) == expected)
    return semantic, fmt, {"actual": actual, "expected": expected}


def _json_load_pairs(raw):
    return json.loads(raw, object_pairs_hook=lambda pairs: pairs)


def _pairs_to_obj(x):
    if isinstance(x, list):
        if all(isinstance(p, tuple) and len(p) == 2 for p in x):
            return {k: _pairs_to_obj(v) for k, v in x}
        return [_pairs_to_obj(v) for v in x]
    return x


def _dual_json_object(response, spec):
    raw = normalize_text(response)
    try:
        pairs = _json_load_pairs(raw)
        actual = _pairs_to_obj(pairs)
        parsed = True
    except Exception:
        return 0.0, 0.0, {"actual": raw, "expected": spec["expected"], "json_parse": False}
    semantic = float(actual == spec["expected"])
    fmt = semantic
    expected_order = spec.get("key_order")
    if expected_order:
        if not isinstance(pairs, list) or not all(isinstance(p, tuple) and len(p) == 2 for p in pairs):
            fmt = 0.0
        else:
            fmt = float(bool(fmt) and [k for k, _ in pairs] == list(expected_order))
    if raw.startswith("```") or raw.endswith("```"):
        fmt = 0.0
    return semantic, fmt, {"actual": actual, "expected": spec["expected"], "json_parse": parsed, "key_order": expected_order}


def grade_dual(response, grading):
    kind = grading["type"]
    if kind == "sequence":
        return _dual_sequence(response, grading)
    if kind == "int_tuple":
        return _dual_int_tuple(response, grading)
    if kind == "kv_state":
        return _dual_kv_state(response, grading)
    if kind == "token_text":
        return _dual_token_text(response, grading)
    if kind == "json_object":
        return _dual_json_object(response, grading)
    score, detail = grade(response, grading)
    if score is None:
        return None, None, detail
    return score, score, detail


def grade(response, grading):
    kind = grading["type"]
    if kind == "exact_text":
        return _score_exact_text(response, grading)
    if kind == "numeric":
        return _score_numeric(response, grading)
    if kind == "json_exact":
        return _score_json_exact(response, grading)
    if kind == "contains":
        return _score_contains(response, grading)
    if kind == "regex":
        return _score_regex(response, grading)
    if kind == "behavior_observation":
        return None, classify_behavior(response)
    if kind in {"sequence", "int_tuple", "kv_state", "token_text", "json_object"}:
        semantic, _, detail = grade_dual(response, grading)
        return semantic, detail
    raise ValueError(f"Unknown grading type: {kind}")
