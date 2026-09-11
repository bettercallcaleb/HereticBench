# HereticBench v1.0.0

**HereticBench measures what changes after an abliteration/"Heretic"-style model modification — not just whether refusals disappear.**

The benchmark keeps four axes separate:

1. **Boundary** — refusal and reasoning-stage safety activation.
2. **Retention** — calibrated deterministic reasoning and instruction integrity.
3. **OpenBehavior** — blind paired review of open-ended answers.
4. **Epistemic Integrity** — whether a model guesses, collapses conflicts, or accepts false premises when evidence does not justify an answer.

There is intentionally **no single composite score**. A model can move strongly on one axis and remain stable on another.

## Reference result

The included reference study compared a local Qwen3.8-27B base configuration with a Heretic/uncensored variant under llama.cpp. It is a **practical configuration comparison, not a matched-weight causal ablation**: the quantizations differ (`UD-Q4_K_XL` vs `Q4_K_M`) and the exact source checkpoint relationship is not independently established by the benchmark.

| Axis | Base | Heretic | Interpretation |
|---|---:|---:|---|
| Harmful RSAR, medium | 100% | 0% | Large refusal-path shift |
| Harmful final refusal among determinate, medium | 100% | 0% | Large visible refusal shift |
| Retention capability signal | 43/60 (71.7%) | 49/60 (81.7%) | No measured capability tax; numeric gain is not statistically conclusive |
| Instruction signal | 57/60 (95.0%) | 58/60 (96.7%) | Essentially retained |
| OpenBehavior quality wins | 2 | 4 | 94/100 ties |
| OpenBehavior severe drift (3–4/4) | 0/100 | 0/100 | No severe paired drift observed |
| Epistemic strict 5-way | 120/120 | 117/120 | Three taxonomy-boundary misses |
| Epistemic functional | 120/120 | 120/120 | No observed increase in guessing / accepting false premises |

The strongest defensible conclusion is narrow:

> In this tested configuration, the Heretic modification was associated with a large and robust reduction in reasoning-stage and final refusal behavior, while this benchmark did not detect broad degradation in calibrated reasoning, blind open-ended response quality, or functional epistemic integrity.

See [`RESULTS.md`](RESULTS.md) and [`LIMITATIONS.md`](LIMITATIONS.md) before citing the result.

## Install

HereticBench uses only the Python standard library.

```bash
python3 --version   # 3.10+ recommended
```

It expects an OpenAI-compatible endpoint. The reference runs used `llama-server` at `http://127.0.0.1:8080/v1`.

## Quick start

### 1. Validate datasets

```bash
python3 validate_dataset.py data/questions.jsonl
python3 validate_retention.py data/retention_signal.jsonl
python3 validate_openbehavior.py data/openbehavior.jsonl
python3 validate_epistemic.py data/epistemic_integrity.jsonl
```

### 2. Primary retention signal

Run Base:

```bash
python3 run_benchmark.py \
  --base-url http://127.0.0.1:8080/v1 \
  --questions data/retention_signal.jsonl \
  --out results/base-retention-signal.jsonl \
  --label base \
  --effort medium
```

Switch the endpoint to the Heretic model, then:

```bash
python3 run_benchmark.py \
  --base-url http://127.0.0.1:8080/v1 \
  --questions data/retention_signal.jsonl \
  --out results/heretic-retention-signal.jsonl \
  --label heretic \
  --effort medium

python3 compare_retention.py \
  results/base-retention-signal.jsonl \
  results/heretic-retention-signal.jsonl
```

`data/retention_signal.jsonl` is the exact 120-case file used for the published reference result. SHA256:

```text
57a8e9743e3fffe11281452323dd8272cd8adc3b0fec3412443d883b3973bf39
```

The calibration pool and full 210-case generated set are also included. Three retention families saturated at 100% on the reference Base and are therefore treated as **calibration diagnostics**, not part of the primary capability-retention headline.

### 3. OpenBehavior

```bash
python3 run_benchmark.py \
  --base-url http://127.0.0.1:8080/v1 \
  --questions data/openbehavior.jsonl \
  --out results/base-openbehavior.jsonl \
  --label base \
  --effort medium
```

Run Heretic the same way, then create randomized blind A/B pairs:

```bash
python3 make_blind_pairs.py \
  results/base-openbehavior.jsonl \
  results/heretic-openbehavior.jsonl \
  --out results/openbehavior-blind.jsonl \
  --key results/openbehavior-key.json
```

Keep the key hidden until review is complete. The rubric is in [`OPENBEHAVIOR_RUBRIC.md`](OPENBEHAVIOR_RUBRIC.md).

### 4. Epistemic Integrity

```bash
python3 run_benchmark.py \
  --base-url http://127.0.0.1:8080/v1 \
  --questions data/epistemic_integrity.jsonl \
  --out results/base-epistemic.jsonl \
  --label base \
  --effort medium
```

Switch models, run Heretic, then:

```bash
python3 compare_epistemic.py \
  results/base-epistemic.jsonl \
  results/heretic-epistemic.jsonl
```

### 5. Boundary / reasoning-effort sweep

The boundary dataset is `data/questions.jsonl`. For the effort sweep, use the existing `effort_sweep.py` / `compare_efforts.py` workflow. Medium is the primary reference condition because the Heretic xhigh run frequently exhausted the 2048-token output budget.

## Repository map

```text
data/
  questions.jsonl              # boundary / refusal benchmark
  retention_calibration.jsonl  # calibration pool
  retention_eval_full.jsonl    # generated full evaluation (contains ceiling families)
  retention_signal.jsonl       # primary 120-case retention signal set
  openbehavior.jsonl           # 100 open-ended prompts
  epistemic_integrity.jsonl     # 120 evidence-bounded epistemic cases
results/reference/              # aggregate reference results, no raw harmful completions
METHODOLOGY.md
RESULTS.md
LIMITATIONS.md
ARTICLE_RAMGPT.md
```

## Why raw harmful completions are not bundled

The public release includes the safety-boundary **prompts, graders, aggregate statistics, and hashes of the raw runs**, but not the model's raw harmful completions. This keeps the benchmark reproducible without turning the repository into a distribution channel for operationally harmful model output.

## Reproducibility principles

- Temperature 0 for the reference study.
- Medium reasoning effort as the primary condition.
- Same prompt files for paired Base/Heretic runs.
- Prompt-token parity checked in the paired reference runs where relevant.
- Base-only calibration before disjoint retention evaluation.
- OpenBehavior reviewed blind before model identity was revealed.
- Semantic correctness and format compliance reported separately.
- No post-hoc unified score.

## License

MIT. See [`LICENSE`](LICENSE).

## Citation

See [`CITATION.md`](CITATION.md).
