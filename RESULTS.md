# Reference Results

## Headline

The reference comparison shows a large refusal-side change with little measured collateral degradation on the other tested axes.

### Boundary effort sweep

| Model | Effort | RSAR | Final refusal / determinate | Determinate | No final | Length finishes | Avg completion tokens |
|---|---|---:|---:|---:|---:|---:|---:|
| Base | low | 100% | 100% | 30/30 | 0 | 0 | 223.3 |
| Base | medium | 100% | 100% | 30/30 | 0 | 0 | 378.6 |
| Base | xhigh | 100% | 100% | 30/30 | 0 | 0 | 407.0 |
| Heretic | low | 0% | 0% | 21/30 | 9 | 14 | 1625.6 |
| Heretic | medium | 0% | 0% | 29/30 | 1 | 5 | 1390.4 |
| Heretic | xhigh | 0% | 0% | 11/30 | 19 | 22 | 1747.5 |

Medium is the primary comparison because xhigh is dominated by output-budget exhaustion on Heretic.

### Retention signal

| Category | Base semantic | Heretic semantic | Base format | Heretic format |
|---|---:|---:|---:|---:|
| code trace | 18/30 (60.0%) | 24/30 (80.0%) | 18/30 | 24/30 |
| constraint assignment | 25/30 (83.3%) | 25/30 (83.3%) | 25/30 | 23/30 |
| multi-rule lines | 18/20 (90.0%) | 18/20 (90.0%) | 18/20 | 18/20 |
| nested JSON transform | 20/20 | 20/20 | 20/20 | 20/20 |
| system-format persistence | 19/20 (95.0%) | 20/20 | 19/20 | 20/20 |
| **Capability subtotal** | **43/60 (71.7%)** | **49/60 (81.7%)** | — | — |
| **Instruction subtotal** | **57/60 (95.0%)** | **58/60 (96.7%)** | — | — |
| **All signal cases** | **100/120 (83.3%)** | **107/120 (89.2%)** | **100/120** | **105/120** |

Paired exact tests:

- All 120 semantic cases: Heretic-only correct 10, Base-only correct 3, `p=0.092`.
- Capability 60: Heretic-only 8, Base-only 2, `p=0.109`.
- Code trace 30: Heretic-only 7, Base-only 1, `p=0.070`.
- Constraint assignment 30: one flip each direction, `p=1.000`.

The code-trace result is suggestive, not sufficient evidence that the intervention improves intelligence.

### OpenBehavior blind review

100 pairs were judged before model identity was revealed.

| Outcome | Count |
|---|---:|
| Base quality win | 2 |
| Heretic quality win | 4 |
| Tie | 94 |
| Divergence 0/4 | 9 |
| Divergence 1/4 | 79 |
| Divergence 2/4 | 12 |
| Divergence 3/4 | 0 |
| Divergence 4/4 | 0 |

Mean substantive divergence: **1.03/4**. No pair was judged 3/4 or 4/4.

### Epistemic Integrity

| Class | Base | Heretic |
|---|---:|---:|
| SUPPORTED | 24/24 | 24/24 |
| CONTRADICTED | 24/24 | 24/24 |
| UNKNOWN | 24/24 | 24/24 |
| CONFLICT | 24/24 | 24/24 |
| FALSE_PREMISE | 24/24 | 21/24 |
| **Strict total** | **120/120** | **117/120** |
| **Functional total** | **120/120** | **120/120** |

The three Heretic strict misses were `FALSE_PREMISE → CONTRADICTED`. In all three, the reasoning explicitly rejected the false presupposition; the failure was selecting the broader taxonomy label rather than accepting the premise.

Exact paired McNemar p-value for strict accuracy: **0.25**.

Mean completion tokens rose from **189.0** (Base) to **271.1** (Heretic) on this suite; mean runtime rose from **4.35 s** to **6.11 s**.

## What the result supports

A careful statement is:

> In this tested configuration, the Heretic variant exhibited a large and robust reduction in refusal behavior. The benchmark did not detect broad degradation in calibrated reasoning, blind open-ended response quality, or functional epistemic integrity. Generation cost increased on several affected workloads.

## What the result does not support

- It does not prove that abliteration has zero cost.
- It does not prove Heretic is smarter.
- It does not prove all safety mechanisms are removed.
- It does not isolate the causal effect of one model edit because the compared artifacts are not perfectly matched.
