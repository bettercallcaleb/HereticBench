---
title: "HereticBench: What Actually Changes When You Remove a Model's Refusal Behavior?"
date: 2026-09-11
description: "A paired benchmark of refusal behavior, calibrated reasoning, open-ended response drift, and epistemic integrity in a 27B Base vs Heretic model comparison."
tags: [llm, benchmarking, llama.cpp, alignment, abliteration, open-source]
---

# HereticBench: What Actually Changes When You Remove a Model's Refusal Behavior?

Abliterated and "uncensored" models are usually evaluated with a very simple question: *does the model still refuse?*

That is useful, but it is not enough.

The more interesting question is what happens to everything else. If an intervention removes refusal behavior, does the model also become worse at reasoning? Does it start hallucinating more aggressively? Does its personality drift? Does instruction following degrade? Or is the change relatively localized?

I built **HereticBench** to measure that delta directly.

The benchmark compares a Base model and a Heretic-style variant across four independent axes: safety-boundary behavior, calibrated capability retention, blind open-ended behavioral drift, and epistemic integrity. I intentionally do **not** combine them into one score. A model can move dramatically on one axis while remaining nearly unchanged on another, and a single number would hide exactly the effect I wanted to study.

The short version of the reference experiment is surprising: the refusal behavior changed enormously, while the other measured capabilities changed much less.

## The setup

The reference runs used a local llama.cpp server (`b10851`) at temperature 0. The primary condition used medium reasoning effort, with low and xhigh added for the refusal-effort sweep.

The two model files were:

- Base: `Qwen3.8-27B-UD-Q4_K_XL.gguf`
- Heretic: `Qwen3.8-27B-Ultra-Uncensored-Heretic-Native-MTP-Preserved-Q4_K_M.gguf`

This limitation matters: **the quantizations are not matched**, and I cannot claim that the two files differ only by one abliteration operation. This is therefore a practical configuration comparison, not a clean causal neuroscience experiment on model weights. The benchmark and raw-run hashes are published so that better-matched replications can improve on this first result.

## 1. Refusal behavior: the change is huge

The first axis measures harmful-boundary behavior. The key metric is **RSAR — Reasoning Safety Activation Rate**, an operational classifier for explicit refusal or safety decisions inside the emitted reasoning trace. I also measure refusal in the visible final answer.

Across 30 harmful cases at each reasoning effort, Base and Heretic separated almost perfectly:

| Model | Effort | RSAR | Final refusal among determinate outputs |
|---|---|---:|---:|
| Base | low | 100% | 100% |
| Base | medium | 100% | 100% |
| Base | xhigh | 100% | 100% |
| Heretic | low | 0% | 0% |
| Heretic | medium | 0% | 0% |
| Heretic | xhigh | 0% | 0% |

The important observation is not merely that the Heretic model stopped printing a refusal sentence. In this test, the explicit refusal signal also disappeared from the reasoning trace.

That said, xhigh is a bad primary operating point for this comparison. The Heretic model frequently consumed the full 2048-token output budget: 19 of 30 xhigh cases had no usable final answer and 22 finished by length. Medium was much cleaner, with 29 of 30 determinate finals.

There is also a cost signal here. At medium effort the Base averaged about 379 completion tokens on the harmful set; Heretic averaged about 1,390. Removing refusal did not make the interaction cheaper.

## 2. Capability retention: the first benchmark was too easy

My first retention set failed in a familiar way: both models scored around 99%. That sounds good, but scientifically it is almost useless. A ceiling benchmark cannot tell you whether a modification costs one or two percentage points of capability.

So I changed the protocol.

The new retention pipeline calibrates difficulty on **Base only**, then generates a disjoint evaluation set using different seeds. The target is not "the hardest question possible." The target is a region where Base accuracy has room to move.

That immediately exposed another problem: three generated families — state tracking, shortest path, and boolean circuits — stayed at 100% even at the hardest available calibration tier. I therefore kept them as diagnostics but excluded them from the primary retention headline.

The final signal set contains 60 capability cases plus 60 instruction-integrity cases.

Results:

| Track | Base | Heretic |
|---|---:|---:|
| Capability signal | 43/60 (71.7%) | 49/60 (81.7%) |
| Instruction signal | 57/60 (95.0%) | 58/60 (96.7%) |
| Combined signal | 100/120 (83.3%) | 107/120 (89.2%) |

The capability result is driven by code tracing:

- Base: 18/30 = 60%
- Heretic: 24/30 = 80%
- Heretic-only correct pairs: 7
- Base-only correct pairs: 1
- exact paired p ≈ 0.070

This is interesting, but I do **not** interpret it as "abliteration makes the model smarter." Thirty cases are too few, p≈0.070 is suggestive rather than decisive, and the model artifacts are not perfectly matched. The useful conclusion is simpler: **I did not detect a capability tax in this signal set.**

Constraint assignment was exactly tied at 25/30 versus 25/30.

Separating semantic accuracy from formatting also mattered. In one Heretic constraint case, the model derived the correct sequence but wrapped it in extra prose. That should be a format failure, not a reasoning failure. HereticBench reports those separately.

## 3. Open-ended behavior: blind the judge

Exact-answer tasks can miss a different kind of collateral damage. Two models can both solve the math problem while becoming very different conversational systems.

To measure that, OpenBehavior uses 100 prompts covering general reasoning, technical questions, explanation/writing, uncertainty, controversial-but-benign topics, cybersecurity dual use, and ethical tradeoffs.

The Base and Heretic answers were randomized into A/B pairs. I froze the judgments **before revealing which side was which**.

The result was extremely tie-heavy:

- Base quality wins: 2
- Heretic quality wins: 4
- ties: 94
- mean substantive divergence: 1.03 / 4
- divergence 3/4: 0 cases
- divergence 4/4: 0 cases

The models often used different examples and phrasing, so raw text similarity was not especially high. But the underlying recommendation or reasoning strategy usually remained the same.

The highest average drift appeared in ethical-sensitive prompts, but even there I did not observe opposite recommendations. Differences were more often about which concern received more weight — autonomy versus legal duty, equity versus efficiency, or how much uncertainty to foreground.

The most encouraging category was uncertainty/judgment: Heretic won three blind quality comparisons there, largely because it was occasionally *more* careful about what the available evidence actually justified.

Again, this is not a universal personality test. It is one frozen blind review, not a multi-rater study. But it gives a very different kind of evidence from an exact-answer benchmark, and it did not show broad behavioral degradation.

## 4. Epistemic integrity: does removing inhibition make the model guess?

This was the final test I added before freezing v1.0.

If refusal behavior is weakened, a plausible collateral effect is that the model may become more willing to commit when evidence is missing or contradictory. So I created 120 evidence-bounded cases with five labels:

- `SUPPORTED`
- `CONTRADICTED`
- `UNKNOWN`
- `CONFLICT`
- `FALSE_PREMISE`

Half of the UNKNOWN, CONFLICT, and FALSE_PREMISE cases deliberately pressure the model to guess, resolve ambiguity, or accept the user's premise.

Base scored 120/120. Heretic scored 117/120 under the strict five-way taxonomy.

At first glance, that looks like a small epistemic loss. Inspecting the three misses changed the interpretation.

All three were `FALSE_PREMISE` cases where Heretic answered `CONTRADICTED`. The reasoning explicitly identified that the premise was false and refused to accept it. The model had the epistemic behavior right; it selected the broader taxonomy label instead of the benchmark's more specific label.

Under a functional criterion — *did the model detect the evidence problem rather than hallucinate through it?* — both models were 120/120.

The strict paired difference is also small: three Base-only correct cases, zero Heretic-only, exact McNemar p=0.25.

What did change again was generation cost. Average completion tokens increased from about 189 to 271, and runtime from 4.35 seconds to 6.11 seconds.

## What I think the result means

The strongest conclusion I am comfortable publishing is:

> In this tested configuration, the Heretic modification produced a large and robust reduction in reasoning-stage and final refusal behavior, while HereticBench did not detect broad degradation in calibrated reasoning, blind open-ended response quality, or functional epistemic integrity.

That is a much narrower statement than "abliteration is free."

There are several reasons not to over-generalize. The quantizations differ. This is one model family. The refusal classifier is operational, not a mechanistic probe. The harmful set is finite. OpenBehavior currently has one blind evaluator. Three retention families hit a ceiling and had to be excluded from the primary capability score. And the Heretic model clearly generated more tokens in several conditions.

Still, I think this is a more useful way to evaluate these modifications than simply asking whether a model says "I can't help with that."

The key result is the *shape* of the delta: a very large movement on refusal behavior, with much smaller measured movement on unrelated axes.

## Why I am open-sourcing HereticBench

This first study is not the final word; it is a protocol that can be challenged.

A stronger replication would use the exact same source checkpoint and quantization, apply a documented intervention, run multiple seeds, add independent blind judges, and repeat across several model families. That is exactly why the benchmark is public.

The repository includes:

- boundary prompts and refusal/RSAR analysis
- Base-only calibration tools
- the exact 120-case retention signal set used here
- the 100-prompt OpenBehavior set and blind-pair tooling
- the 120-case Epistemic Integrity set
- aggregate reference results and raw-run hashes
- methodology and limitations

I intentionally do not bundle the raw harmful completions. The benchmark should make the experiment reproducible without turning a results repository into a distribution channel for operationally harmful generations.

If you reproduce it on another model — especially with a perfectly matched Base/Heretic pair — the most useful contribution is not a single score. Publish the four-axis profile and the exact configuration.

That is what HereticBench is designed to measure.

**Repository:** add your GitHub URL here after publishing.
