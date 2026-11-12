# DG2. Where the guard's benign false blocks come from

<!-- generated 2026-08-14 18:46:44 +0800 by code/scripts/falseblock_decompose.py (l1-falseblock-decompose-1) -->
<!-- capability set: mode M_constrained, primary_class benign, infra rows dropped, DeepSeek excluded (json_object wire, no schema enforcement) -->
<!-- tau 0.2 (provisional), LB floor 1.0 bh, G_CERT config_hash 52c094406252bf1a -->
<!-- in DG2_falseblock_decomposition.csv the anchor/replay columns are blank on an arm with more than one thinking cell (opus) and carried on that arm's arm_pooled row instead, so no reader can double count them -->
<!-- results/e1_eval_qwen14b/verdicts_G_CERT.jsonl sha256 7aa71f03804c3213d7c842ddf1d917f96fa54f4190d076de41187e5177fbcea0 -->
<!-- results/e1_eval_qwen27b/verdicts_G_CERT.jsonl sha256 59f9a49feb1d83cd82f3ac9bbfc1075f3bba80f28e0d50733f62e6acb37122b8 -->
<!-- results/e1_eval_glm9b/verdicts_G_CERT.jsonl sha256 8d020fa65870c4614fc47806d8cd78a7d00b61e2295a4babeebcc2cd7aa42d79 -->
<!-- results/e1_eval_gpt54mini/verdicts_G_CERT.jsonl sha256 fca80b7f847e7826942c8cbb008ce84be0931cf808bca28e661b56e9785d97e8 -->
<!-- results/e1_eval_deepseek/verdicts_G_CERT.jsonl sha256 5c03ca0b5ae739bd89388dcbcc7226c27e93384508e134dfb2afa6fb7f431208 -->
<!-- results/e1_eval_sonnet5/verdicts_G_CERT.jsonl sha256 374dd1a0edc50802d25a40563d0ed6f64ecea4c65c5d4fc1fee79cea5a881fbc -->
<!-- results/e1_eval_opus5/verdicts_G_CERT.jsonl sha256 30805ed2a08c551150a3a5a4ee43d363a74638886e3424c8faaf44195dcee517 -->
<!-- results/e1_eval_sol/verdicts_G_CERT.jsonl sha256 5b7aa9b1a0a863a4e415ad0189fdb8252a6b9843184603bece890893a497a795 -->
<!-- analysis/T3_guard_value_curve.csv sha256 2c2a80eb9d1c19612bbf8557846196ac838b3e528335cd336a760f6276dcd22e -->
<!-- analysis/ladder/rule_anchor.csv sha256 ca31ec0bf9805ef42390e8663257e204da7da4191eb0b2052ad4f0225cb52fc7 -->
<!-- results/tier1_slice/rows.jsonl sha256 b43875f5c938c9d2e814a76d088bde22ba6655e88fbead88a3e2c5d38b255093 -->

Proposition 1 makes the certificate stage one-sided: a loose lower bound can only refuse a proposal that deserved acceptance, never accept one that deserved refusal. This diagnostic measures how much of the measured false-block rate that slack actually explains.

**Self-check.** The per-arm benign false-block rate is recomputed here from `results/e1_eval_*/verdicts_G_CERT.jsonl` and compared against the published `benign_false_block_gcert` column of `analysis/T3_guard_value_curve.csv`. All 10 published arm rows match to six decimals.

## 1. Stage decomposition of the benign false blocks

Capability set: `mode == M_constrained`, `primary_class == benign`, rows with an `infra_error` finding dropped, DeepSeek excluded (its `M_constrained` is JSON-object mode, so its false blocks measure the absence of schema enforcement). Each arm contributes 800 benign twins per repeat.

| arm | think | benign rows | false blocks | rate | schema | feas | quality | quality as pp of benign rows |
|---|---|---|---|---|---|---|---|---|
| qwen3-14b | - | 2400 | 111 | 4.62% | 0 | 12 | 99 | 4.12 pp |
| qwen3.6-27b-fp8 | - | 2400 | 132 | 5.50% | 0 | 69 | 63 | 2.62 pp |
| glm-4-9b | - | 800 | 74 | 9.25% | 7 | 47 | 20 | 2.50 pp |
| openai | - | 1600 | 63 | 3.94% | 3 | 18 | 42 | 2.62 pp |
| sonnet | disabled | 1600 | 62 | 3.88% | 0 | 20 | 42 | 2.62 pp |
| opus | default | 1600 | 63 | 3.94% | 0 | 21 | 42 | 2.62 pp |
| opus | disabled | 1600 | 80 | 5.00% | 0 | 38 | 42 | 2.62 pp |
| sol | none | 800 | 69 | 8.62% | 21 | 27 | 21 | 2.62 pp |
| **pooled** | - | 12800 | 654 | 5.11% | 31 | 252 | 371 | 2.90 pp |

The two DeepSeek cells, excluded from the pooled figure and printed for completeness:

| arm | think | benign rows | false blocks | rate | schema | feas | quality |
|---|---|---|---|---|---|---|---|
| deepseek | non_think | 1600 | 1555 | 97.19% | 1553 | 0 | 2 |
| deepseek | think_high | 1600 | 1591 | 99.44% | 1591 | 0 | 0 |

Only the quality column can be caused by bound slack. It is 371 of the 654 pooled benign false blocks, which is 2.90% of the pooled benign rows: 2.90 percentage points of the 800 benign twins an arm sees per repeat, ranging from 2.50 pp (glm-4-9b) to 4.12 pp (qwen3-14b) across the arms.

## 2. Deduplication: is (instance, item) a legitimate solve key?

No. The 371 quality-stage refusals collapse to 159 distinct (arm, item) pairs and 35 distinct (instance, item) pairs, but the certificate is computed on the ADJUSTED instance, which is a function of the proposal's operations. 2 of the 35 (instance, item) groups carry more than one accepted certified gap, so solving one representative per (instance, item) would report a bound for a schedule that some of the rows never executed.

- counterexample `c09_storm2_w80_u100_0008|BEN-0287`: accepted certified gaps 0.225024, 0.226190, 0.228070
- counterexample `c09_storm2_w80_u100_0008|BEN-0687`: accepted certified gaps 0.224078, 0.226611, 2.301955

The replay therefore deduplicates on the guard's own input, the tuple (instance file, raw model output, dispatch rule, dispatch seed, frozen seed), which is everything `evaluate_proposal` reads. That is 111 distinct solves covering all 371 rows, and each solve's outcome is expanded back over its member rows.

## 3. The Tier 1 rescue replay

Configuration `G_CERT.with_(lb_tier="best", tier1_budget_s=B)`: the certificate takes the maximum of the analytic Tier 2 bound and the CP-SAT Tier 1 bound, which the admissibility appendix records as admissible. Every input first reproduced its accepted Tier 2 terminal and certified gap exactly (gate: 111/111 solves, covering 371/371 rows).

| budget | solves | rows covered | rows rescued | rescue rate | Tier 1 vacuous (solves) | Tier 1 tighter (solves) |
|---|---|---|---|---|---|---|
| 1 s | 111 | 371 | 0 | 0.00% | 110 | 1 |
| 5 s | 111 | 371 | 0 | 0.00% | 6 | 105 |

For the refusals a tighter bound does not rescue, the ratio by which the bound would still have to tighten to reach tau = 0.2, against the largest relative tightening CP-SAT achieves anywhere in `results/tier1_slice/rows.jsonl`:

| budget | rows not rescued | required tightening min | median | max | delivered here, rows where Tier 1 is tighter (median / max) | largest delivered on the accepted tier-1 slice (same budget) |
|---|---|---|---|---|---|---|
| 1 s | 371 | 1.996% | 6.696% | 501.129% | 0.075% / 0.075% | 0.118% |
| 5 s | 371 | 1.873% | 6.454% | 499.927% | 0.121% / 0.228% | 0.223% |

The required tightening is the ratio by which the best deployable bound would have to rise to bring the certified gap down to tau. The two delivered columns are what CP-SAT actually buys: on these rows at 5 s the largest is 0.228%, and the largest anywhere in the accepted tier-1 slice is 0.223%, so the two together put the ceiling on solver-side tightening at about a quarter of one per cent, against a smallest requirement of 1.873%. The two figures are reported separately because neither set is a superset of the other.

Two independent executions of this replay, run 16 minutes apart on the same pinned cores, returned bit-identical Tier 1 bounds and identical rescue verdicts on all 111 solves, so the wall-clock solver budget is not producing a borderline result.

## 4. The instance-side cause

The no-AI RULE anchor is the ATC dispatch of the unmodified instance under the same frozen set (`analysis/ladder/rule_anchor.csv`). Where the anchor itself certifies above tau, no proposal is certifiable on that instance under the deployed bound, doing nothing included.

| arm | quality-stage refusals | anchor gap > tau | objective no worse than anchor | objective equals anchor |
|---|---|---|---|---|
| glm-4-9b | 20 | 19 | 18 | 16 |
| openai | 42 | 42 | 42 | 34 |
| opus | 84 | 84 | 84 | 68 |
| qwen3-14b | 99 | 66 | 63 | 54 |
| qwen3.6-27b-fp8 | 63 | 63 | 63 | 51 |
| sol | 21 | 21 | 21 | 17 |
| sonnet | 42 | 42 | 42 | 34 |
| **pooled** | 371 | 337 | 333 | 274 |

Refusals with an above-tau anchor, by instance:

| instance | refusals | anchor gap |
|---|---|---|
| c09_storm2_w80_u100_0008 | 175 | 0.2266 |
| c09_storm2_w80_u100_0018 | 162 | 0.2867 |

## 5. The decomposition the manuscript states

| category | count | share of pooled benign false blocks | definition |
|---|---|---|---|
| schema | 31 | 4.74% | refused at stage 1: the proposal did not parse against the frozen operation schema (terminal blocked_schema) |
| feasibility | 252 | 38.53% | refused at stage 2: the proposal parsed but the adjusted instance is not executable (terminal blocked_feas) |
| quality_instance_infeasible_at_tau | 337 | 51.53% | refused at stage 3, on an instance whose no-AI RULE anchor already certifies above tau (rule_anchor gap > 0.20): no proposal at all, including doing nothing, is certifiable on this instance under the deployed bound |
| quality_bound_attributable | 0 | 0.00% | refused at stage 3, anchor at or below tau, and the tightest deployable bound (max of Tier 2 and CP-SAT Tier 1 at a 5 s budget) accepts it: the refusal was caused by slack in the analytic bound |
| quality_proposal_attributable | 34 | 5.20% | refused at stage 3, anchor at or below tau, and the tightest deployable bound still refuses it: the realized objective is genuinely far from any bound the guard can prove |
| **total** | 654 | 100.00% | benign false blocks, capability set |

The last three categories are assigned in that order, so the cross-tab is printed as well: no refusal is hidden by the ordering.

| cell | rows |
|---|---|
| anchor_above_tau=0 rescued_5s=0 | 34 |
| anchor_above_tau=1 rescued_5s=0 | 337 |

Per arm, over the quality stage only:

| arm | quality-stage refusals | instance infeasible at tau | bound attributable | proposal attributable |
|---|---|---|---|---|
| glm-4-9b | 20 | 19 | 0 | 1 |
| openai | 42 | 42 | 0 | 0 |
| opus | 84 | 84 | 0 | 0 |
| qwen3-14b | 99 | 66 | 0 | 33 |
| qwen3.6-27b-fp8 | 63 | 63 | 0 | 0 |
| sol | 21 | 21 | 0 | 0 |
| sonnet | 42 | 42 | 0 | 0 |
| **pooled** | 371 | 337 | 0 | 34 |

