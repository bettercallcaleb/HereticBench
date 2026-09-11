# Limitations

The reference findings are intentionally narrow. Important limitations:

1. **Not a matched causal ablation.** Base and Heretic used different GGUF quantizations (`UD-Q4_K_XL` vs `Q4_K_M`), and the benchmark metadata does not independently establish that the two files differ only by the safety intervention.
2. **Single model family/configuration.** Results should not be generalized to other model sizes, architectures, abliteration methods, quantizations, templates, or inference backends without replication.
3. **Operational safety classifiers.** RSAR and refusal detection are heuristic text classifiers. They measure emitted reasoning/final behavior, not hidden neural mechanisms.
4. **Finite harmful coverage.** The 30 harmful effort-sweep cases establish a strong separation on the tested families, not a universal claim that all safety behavior is removed.
5. **Heretic truncation.** On harmful prompts the Heretic configuration often generated much longer outputs. At xhigh, many runs exhausted the 2048-token budget, making xhigh a poor primary condition.
6. **Retention family selection.** Three generated reasoning families saturated at 100% and were excluded from the primary retention headline. This exclusion was based on Base calibration before the paired signal run, but it still narrows what the headline measures.
7. **OpenBehavior has one frozen blind review.** The A/B identity was genuinely hidden, but the current release does not provide inter-rater reliability or multiple independent judges.
8. **OpenBehavior is not a factuality benchmark.** A tie-heavy result means no clear blind preference under the rubric, not proof that both answers were objectively correct.
9. **Epistemic taxonomy ambiguity.** `FALSE_PREMISE` and `CONTRADICTED` can overlap semantically. Three Heretic strict misses were of exactly this form; reasoning showed the premise was rejected rather than accepted.
10. **No multilingual or multi-turn suite in v1.** Those are reasonable extensions, but were deliberately left out to freeze the first release.
11. **No claim that Heretic is smarter.** The +20 pp code-trace difference is suggestive (`p≈0.070` in 30 paired cases), not statistically decisive and may reflect configuration differences.
12. **No claim of zero collateral cost.** Failure to detect broad degradation on these tests is not proof that no degradation exists.
