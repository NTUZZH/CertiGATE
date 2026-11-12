# DG2. Where the guard's benign false blocks come from

<!-- generated 2026-08-16 14:29:05 +0800 by code/scripts/falseblock_decompose.py (l1-falseblock-decompose-1) -->
<!-- capability set: mode M_constrained, primary_class benign, infra rows dropped, DeepSeek excluded (json_object wire, no schema enforcement) -->
<!-- tau 0.2 (provisional), LB floor 1.0 bh, G_CERT config_hash 52c094406252bf1a -->
<!-- in DG2_falseblock_decomposition.csv the anchor/replay columns are blank on an arm with more than one thinking cell (opus) and carried on that arm's arm_pooled row instead, so no reader can double count them -->
<!-- results/e1_eval_qwen14b/verdicts_G_CERT.jsonl sha256 007f9b7e128b9b40a1c8a6f20e1d7bf0688e7597c9ccf802b3d4603e11d5ff82 -->
<!-- results/e1_eval_qwen27b/verdicts_G_CERT.jsonl sha256 34f6a4c8b2b26b38a69a21c1a22d0d0ee7715b2d15a095399aa505c279377d10 -->
<!-- results/e1_eval_glm9b/verdicts_G_CERT.jsonl sha256 357ff6582097bd5c6656c14e6c47a6c85b5cb2c699e2206d1f8722ff1f0e6ed4 -->
<!-- results/e1_eval_gpt54mini/verdicts_G_CERT.jsonl sha256 ab58fe9be34e97572208247ee13fbf9710af6b14f5b0004390faeb4031f1a78d -->
<!-- results/e1_eval_deepseek/verdicts_G_CERT.jsonl sha256 5c03ca0b5ae739bd89388dcbcc7226c27e93384508e134dfb2afa6fb7f431208 -->
<!-- results/e1_eval_sonnet5/verdicts_G_CERT.jsonl sha256 87d3ebaefefe7b70915a861cc2f61dd3fb5e7e08df5f83756cf78ce5aa8f102c -->
<!-- results/e1_eval_opus5/verdicts_G_CERT.jsonl sha256 2c4a3d99410ce0bc38a8c230ffa3770f8f1fc20d514c732abf4d53d898f77744 -->
<!-- results/e1_eval_sol/verdicts_G_CERT.jsonl sha256 3a06dbde336b05951afd45cf08f609612a095c7a0d1861f68c447e6c7ab16dab -->
<!-- analysis/T3_guard_value_curve.csv sha256 f5df92e8a6638869c8f9cc56270d0d4a4d48c910c9fedb60889817b9a4c694ca -->
<!-- analysis/ladder/rule_anchor.csv sha256 ca31ec0bf9805ef42390e8663257e204da7da4191eb0b2052ad4f0225cb52fc7 -->
<!-- results/tier1_slice/rows.jsonl sha256 b43875f5c938c9d2e814a76d088bde22ba6655e88fbead88a3e2c5d38b255093 -->

Proposition 1 makes the certificate stage one-sided: a loose lower bound can only refuse a proposal that deserved acceptance, never accept one that deserved refusal. This diagnostic measures how much of the measured false-block rate that slack actually explains.

**Self-check.** The per-arm benign false-block rate is recomputed here from `results/e1_eval_*/verdicts_G_CERT.jsonl` and compared against the published `benign_false_block_gcert` column of `analysis/T3_guard_value_curve.csv`. All 10 published arm rows match to six decimals.

## 1. Stage decomposition of the benign false blocks

Capability set: `mode == M_constrained`, `primary_class == benign`, rows with an `infra_error` finding dropped, DeepSeek excluded (its `M_constrained` is JSON-object mode, so its false blocks measure the absence of schema enforcement). Each arm contributes 800 benign twins per repeat.

| arm | think | benign rows | false blocks | rate | schema | feas | quality | quality as pp of benign rows |
|---|---|---|---|---|---|---|---|---|
| qwen3-14b | - | 2400 | 105 | 4.38% | 0 | 6 | 99 | 4.12 pp |
| qwen3.6-27b-fp8 | - | 2400 | 132 | 5.50% | 0 | 69 | 63 | 2.62 pp |
| glm-4-9b | - | 800 | 64 | 8.00% | 7 | 36 | 21 | 2.62 pp |
| openai | - | 1600 | 62 | 3.88% | 3 | 17 | 42 | 2.62 pp |
| sonnet | disabled | 1600 | 61 | 3.81% | 0 | 19 | 42 | 2.62 pp |
| opus | default | 1600 | 63 | 3.94% | 0 | 21 | 42 | 2.62 pp |
| opus | disabled | 1600 | 80 | 5.00% | 0 | 38 | 42 | 2.62 pp |
| sol | none | 800 | 69 | 8.62% | 21 | 27 | 21 | 2.62 pp |
| **pooled** | - | 12800 | 636 | 4.97% | 31 | 233 | 372 | 2.91 pp |

The two DeepSeek cells, excluded from the pooled figure and printed for completeness:

| arm | think | benign rows | false blocks | rate | schema | feas | quality |
|---|---|---|---|---|---|---|---|
| deepseek | non_think | 1600 | 1555 | 97.19% | 1553 | 0 | 2 |
| deepseek | think_high | 1600 | 1591 | 99.44% | 1591 | 0 | 0 |

Only the quality column can be caused by bound slack. It is 372 of the 636 pooled benign false blocks, which is 2.91% of the pooled benign rows: 2.91 percentage points of the 800 benign twins an arm sees per repeat, ranging from 2.62 pp (glm-4-9b) to 4.12 pp (qwen3-14b) across the arms.

## 2. Deduplication: is (instance, item) a legitimate solve key?

No. The 372 quality-stage refusals collapse to 160 distinct (arm, item) pairs and 35 distinct (instance, item) pairs, but the certificate is computed on the ADJUSTED instance, which is a function of the proposal's operations. 2 of the 35 (instance, item) groups carry more than one accepted certified gap, so solving one representative per (instance, item) would report a bound for a schedule that some of the rows never executed.

- counterexample `c09_storm2_w80_u100_0008|BEN-0287`: accepted certified gaps 0.225024, 0.226190, 0.228070
- counterexample `c09_storm2_w80_u100_0008|BEN-0687`: accepted certified gaps 0.224078, 0.226611, 2.301955

The replay therefore deduplicates on the guard's own input, the tuple (instance file, raw model output, dispatch rule, dispatch seed, frozen seed), which is everything `evaluate_proposal` reads. That is 112 distinct solves covering all 372 rows, and each solve's outcome is expanded back over its member rows.

## 3. The Tier 1 rescue replay

Configuration `G_CERT.with_(lb_tier="best", tier1_budget_s=B)`: the certificate takes the maximum of the analytic Tier 2 bound and the CP-SAT Tier 1 bound, which the admissibility appendix records as admissible. Every input first reproduced its accepted Tier 2 terminal and certified gap exactly (gate: 112/112 solves, covering 372/372 rows).

| budget | solves | rows covered | rows rescued | rescue rate | Tier 1 vacuous (solves) | Tier 1 tighter (solves) |
|---|---|---|---|---|---|---|
| 1 s | 112 | 372 | 0 | 0.00% | 111 | 1 |
| 5 s | 112 | 372 | 0 | 0.00% | 6 | 106 |

For the refusals a tighter bound does not rescue, the ratio by which the bound would still have to tighten to reach tau = 0.2, against the largest relative tightening CP-SAT achieves anywhere in `results/tier1_slice/rows.jsonl`:

| budget | rows not rescued | required tightening min | median | max | delivered here, rows where Tier 1 is tighter (median / max) | largest delivered on the accepted tier-1 slice (same budget) |
|---|---|---|---|---|---|---|
| 1 s | 372 | 1.996% | 6.696% | 501.129% | 0.075% / 0.075% | 0.118% |
| 5 s | 372 | 1.873% | 6.454% | 499.927% | 0.121% / 0.228% | 0.223% |

The required tightening is the ratio by which the best deployable bound would have to rise to bring the certified gap down to tau. The two delivered columns are what CP-SAT actually buys: on these rows at 5 s the largest is 0.228%, and the largest anywhere in the accepted tier-1 slice is 0.223%, so the two together put the ceiling on solver-side tightening at about a quarter of one per cent, against a smallest requirement of 1.873%. The two figures are reported separately because neither set is a superset of the other.

Two independent executions of this replay, run 16 minutes apart on the same pinned cores, returned bit-identical Tier 1 bounds and identical rescue verdicts on all 112 solves, so the wall-clock solver budget is not producing a borderline result.

## 4. The instance-side cause

The no-AI RULE anchor is the ATC dispatch of the unmodified instance under the same frozen set (`analysis/ladder/rule_anchor.csv`). Where the anchor itself certifies above tau, no proposal is certifiable on that instance under the deployed bound, doing nothing included.

| arm | quality-stage refusals | anchor gap > tau | objective no worse than anchor | objective equals anchor |
|---|---|---|---|---|
| glm-4-9b | 21 | 20 | 19 | 17 |
| openai | 42 | 42 | 42 | 34 |
| opus | 84 | 84 | 84 | 68 |
| qwen3-14b | 99 | 66 | 63 | 54 |
| qwen3.6-27b-fp8 | 63 | 63 | 63 | 51 |
| sol | 21 | 21 | 21 | 17 |
| sonnet | 42 | 42 | 42 | 34 |
| **pooled** | 372 | 338 | 334 | 275 |

Refusals with an above-tau anchor, by instance:

| instance | refusals | anchor gap |
|---|---|---|
| c09_storm2_w80_u100_0008 | 176 | 0.2266 |
| c09_storm2_w80_u100_0018 | 162 | 0.2867 |

## 5. The decomposition the manuscript states

| category | count | share of pooled benign false blocks | definition |
|---|---|---|---|
| schema | 31 | 4.87% | refused at stage 1: the proposal did not parse against the frozen operation schema (terminal blocked_schema) |
| feasibility | 233 | 36.64% | refused at stage 2: the proposal parsed but the adjusted instance is not executable (terminal blocked_feas) |
| quality_instance_infeasible_at_tau | 338 | 53.14% | refused at stage 3, on an instance whose no-AI RULE anchor already certifies above tau (rule_anchor gap > 0.20): no proposal at all, including doing nothing, is certifiable on this instance under the deployed bound |
| quality_bound_attributable | 0 | 0.00% | refused at stage 3, anchor at or below tau, and the tightest deployable bound (max of Tier 2 and CP-SAT Tier 1 at a 5 s budget) accepts it: the refusal was caused by slack in the analytic bound |
| quality_proposal_attributable | 34 | 5.35% | refused at stage 3, anchor at or below tau, and the tightest deployable bound still refuses it: the realized objective is genuinely far from any bound the guard can prove |
| **total** | 636 | 100.00% | benign false blocks, capability set |

The last three categories are assigned in that order, so the cross-tab is printed as well: no refusal is hidden by the ordering.

| cell | rows |
|---|---|
| anchor_above_tau=0 rescued_5s=0 | 34 |
| anchor_above_tau=1 rescued_5s=0 | 338 |

Per arm, over the quality stage only:

| arm | quality-stage refusals | instance infeasible at tau | bound attributable | proposal attributable |
|---|---|---|---|---|
| glm-4-9b | 21 | 20 | 0 | 1 |
| openai | 42 | 42 | 0 | 0 |
| opus | 84 | 84 | 0 | 0 |
| qwen3-14b | 99 | 66 | 0 | 33 |
| qwen3.6-27b-fp8 | 63 | 63 | 0 | 0 |
| sol | 21 | 21 | 0 | 0 |
| sonnet | 42 | 42 | 0 | 0 |
| **pooled** | 372 | 338 | 0 | 34 |

