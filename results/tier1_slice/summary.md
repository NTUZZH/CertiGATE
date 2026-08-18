# Tier 1 vs Tier 2 certificate comparison, and the single-stream guard latency

Generated 2026-08-13 15:02:34 +0800 by `code/scripts/tier1_slice.py` (l1-tier1-slice-1).

```
================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules), answered before the run
================================================================================
1. PURPOSE.  Two open numbers close with one CPU-only run.  (a) The Tier 1 vs
   Tier 2 certificate comparison promised by guidance Section 3.4 and listed as
   deliverable 3: per-row bound tightness, gap movement, solve wall time and
   timeout share at per-proposal budgets of 1 s and 5 s.  It lands in the
   certificate-protocol exhibit of the manuscript.  (b) The single-stream
   per-stage guard latency, which fills \guardAddedLatencyMs (currently a TODO:
   every wall-clock figure on record was measured under concurrency and is a
   throughput number, not a latency).
2. EXPECTED RESULT.  From the accepted solve-time pilot (results/tier1_pilot.json,
   20 instances per cell): Tier 1 is expected to prove optimality inside 1 s on
   the 400-order replay cell and to return a vacuous 0.0 bound on both storm2
   cells at 1 s, becoming marginally informative on c09/storm2 at 5 s.  So the
   expected finding is that Tier 2 carries the certificate almost everywhere at
   a fraction of the cost, with Tier 1 adding tightness on a small, identified
   share.  If instead Tier 1 is materially tighter on the storm2 strata, the
   tier-selection rule in the paper changes from "Tier 2 with Tier 1 as an
   optional refinement" to "best of both, budgeted".  Either outcome is
   reportable; the two lead to different sentences, so the run is not
   redundant.  A row that fails to reproduce its accepted Tier 2 verdict is a
   defect in this instrument or in the record, not a finding, and stops the run.
3. CONTAMINATION.  No API, no GPU, no model call: every number is a
   deterministic replay of raw model output already on disk.  results/ is
   read-only except the --out directory, which must be empty unless --force.
   The two phases are SEQUENCED, never concurrent: the latency phase runs first,
   single-stream, on one pinned core with every numerical runtime capped at one
   thread, and the bulk pass starts only after it has finished, because a wall
   time measured under contention is not a measurement.  The bulk pass is serial
   by default and refuses --workers N unless the pinned core set holds
   N x tier1_workers cores, because the quantity it measures is the bound the
   solver can PROVE inside the budget and a contended solver proves less.  The
   machine's load context is recorded at the start of each phase.
4. DATA ACCURACY.  The sample is drawn from the accepted verdict files, and each
   sampled row is joined to its raw model output by the unique key
   (mode, thinking, repeat, item_id); a duplicate key stops the run.  Every
   input file is sha256'd into the output header.  Each row is then re-evaluated
   under the accepted Tier 2 configuration and asserted to reproduce the
   accepted terminal and the accepted certified gap exactly before its Tier 1
   numbers are used, which is what makes the two tiers a comparison on the same
   schedule rather than two independent readings.
================================================================================
```

```
CAVEAT ON THE TIER 1 BOUND (l1guard/tier1.py, fact 2 of the module docstring).
The Tier 1 bound lives on a centi-business-hour grid: the Y1 CP-SAT model scales
business hours by 100, rounding processing times and releases up and due dates to
nearest.  `best_bound_bh` is therefore a lower bound on the DISCRETIZED model's
optimum, and it differs from the continuous optimum by at most the
discretization.  Tier 2 has no such caveat.  Every tightness delta below is
computed against a Tier 1 bound that carries it, so a delta smaller than the
discretization is not evidence that the solver bound is sharper.
A second recorded fact (fact 1): the CP-SAT model carries the adjusted
instance's FIELDS only, not the proposal's dispatch constraints, so Tier 1
bounds a relaxation.  That is sound (a bound on the relaxation bounds the
constrained optimum) and it is why the certified gap never understates.
A third (fact 3): a budget that proves nothing still returns 0.0, which is valid
but vacuous; the vacuous share is reported per budget and never averaged away.
```

## Run

| field | value |
|---|---|
| date | 2026-08-13 15:02:34 +0800 |
| sample seed | 0 |
| rows compared | 444 |
|   part A (opus core certified V3, census) | 44 |
|   part B (certified benign + V4, stratified draw) | 400 |
| latency sub-sample | 200 |
| budgets | 1 s, 5 s |
| tau | 0.2 (provisional) |
| LB floor | 1 bh |
| latency phase | 200 rows, 1 stream, cores [0], threads 1 |
| bulk phase | 444 rows, 1 worker(s), cores [0, 1, 2, 3, 4, 5], tier1_workers 4 |
| latency wall | 537.1 s |
| bulk wall | 3583.1 s |
| total wall | 4122.4 s |

### Guard configurations

| configuration | lb_tier | tier1_budget_s | tier1_workers | config_hash |
|---|---|---|---|---|
| CFG_T2 | tier2 | 0.0 | 4 | `52c094406252bf1a` |
| CFG_BEST_1s | best | 1.0 | 4 | `29ce396a0070b811` |
| CFG_BEST_5s | best | 5.0 | 4 | `525278098e9a93a3` |
| CFG_T1_LAT | tier1 | 1.0 | 1 | `d5a0e2f7806e378b` |

`CFG_T2` is byte-identical to the configuration the accepted E1 evaluations ran, so its `config_hash` is the one recorded in every `verdicts_G_CERT.jsonl` row. The design freeze writes the Tier 1 configuration as `G_CERT.with_(tier1_budget_s=B)`; `lb_tier` has to move with the budget, because `G_CERT.lb_tier` is `tier2` and the solver is never called under it whatever the budget is. `best` computes both bounds on one adjusted instance and records them separately, so the comparison is exact and the row is dispatched once per budget rather than twice.

### Inputs

| file | sha256 |
|---|---|
| `results/e1_eval_glm9b/proposals.jsonl` | `f5fddbd9d2632d10b88ab9135c907487c1f07623e9d79e3fde93271e67086352` |
| `results/e1_eval_glm9b/verdicts_G_CERT.jsonl` | `8d020fa65870c4614fc47806d8cd78a7d00b61e2295a4babeebcc2cd7aa42d79` |
| `results/e1_eval_gpt54mini/proposals.jsonl` | `44b0c5ab7b6b681d3ac6320d7e199b5a5e1dc90c8852aa7a00dbc0f0a4fb44f2` |
| `results/e1_eval_gpt54mini/verdicts_G_CERT.jsonl` | `fca80b7f847e7826942c8cbb008ce84be0931cf808bca28e661b56e9785d97e8` |
| `results/e1_eval_opus5/proposals.jsonl` | `98f88b0c128dea546c96798605d4240804af4bff7da4f5e09146d2b1b4d16fba` |
| `results/e1_eval_opus5/verdicts_G_CERT.jsonl` | `30805ed2a08c551150a3a5a4ee43d363a74638886e3424c8faaf44195dcee517` |
| `results/e1_eval_qwen14b/proposals.jsonl` | `2ec50652919689ae5cfc809f3f4a926a19f34de770427774a6ac222cd9bf9c26` |
| `results/e1_eval_qwen14b/verdicts_G_CERT.jsonl` | `7aa71f03804c3213d7c842ddf1d917f96fa54f4190d076de41187e5177fbcea0` |
| `results/e1_eval_qwen27b/proposals.jsonl` | `cb438320a72a2fc7d891e3b4b6c47fcdf6fdb4b7bdbe6a0d72c5e2089212ea65` |
| `results/e1_eval_qwen27b/verdicts_G_CERT.jsonl` | `59f9a49feb1d83cd82f3ac9bbfc1075f3bba80f28e0d50733f62e6acb37122b8` |
| `results/e1_eval_sol/proposals.jsonl` | `715e844ffd890cefe2d6392686dc85d6e2cf74b894e2247ad5b7836662d0de54` |
| `results/e1_eval_sol/verdicts_G_CERT.jsonl` | `5b7aa9b1a0a863a4e415ad0189fdb8252a6b9843184603bece890893a497a795` |
| `results/e1_eval_sonnet5/proposals.jsonl` | `addca54e530e4954a10b9132c735d3eff1b2f84a69512397c213b8a81d66c5fb` |
| `results/e1_eval_sonnet5/verdicts_G_CERT.jsonl` | `374dd1a0edc50802d25a40563d0ed6f64ecea4c65c5d4fc1fee79cea5a881fbc` |

## Gate: every sampled row reproduces its accepted Tier 2 verdict

Each sampled row is re-evaluated from its raw model output under `CFG_T2` and its terminal state and certified gap are compared with the accepted verdict. The Tier 1 numbers of a row that fails are never used, and the run stops.

| checked | reproduced | mismatched | verdict |
|---|---|---|---|
| 444 | 444 | 0 | PASS |

The executed schedule is also identical under every Tier 1 budget: `schedule_digest` matches the Tier 2 replay on 100.0% of rows at 1 s and 100.0% at 5 s, which is what makes the two bounds a comparison on the same schedule.

## Sample

Part A is a census: every row of the opus core (M_constrained x thinking-disabled, both repeats) whose accepted verdict is `applied_with_certificate` and whose class is V3. Part B draws 400 certified benign and V4 rows evenly across the seven schema-enforced arms and, within each arm, evenly across the six (class, stratum) cells; cells and candidates are both sorted before sampling, so the draw is a function of (record, seed, n) alone. Seed 0. A part-A row is never redrawn into part B.

| part | arm | class | stratum | rows |
|---|---|---|---|---|
| benign_v4_400 | glm-4-9b | V4 | c09_storm2_w80 | 10 |
| benign_v4_400 | glm-4-9b | V4 | c10_replay_400 | 10 |
| benign_v4_400 | glm-4-9b | V4 | c10_storm2_w80 | 10 |
| benign_v4_400 | glm-4-9b | benign | c09_storm2_w80 | 10 |
| benign_v4_400 | glm-4-9b | benign | c10_replay_400 | 9 |
| benign_v4_400 | glm-4-9b | benign | c10_storm2_w80 | 9 |
| benign_v4_400 | openai | V4 | c09_storm2_w80 | 10 |
| benign_v4_400 | openai | V4 | c10_replay_400 | 10 |
| benign_v4_400 | openai | V4 | c10_storm2_w80 | 10 |
| benign_v4_400 | openai | benign | c09_storm2_w80 | 9 |
| benign_v4_400 | openai | benign | c10_replay_400 | 9 |
| benign_v4_400 | openai | benign | c10_storm2_w80 | 9 |
| benign_v4_400 | opus | V4 | c09_storm2_w80 | 10 |
| benign_v4_400 | opus | V4 | c10_replay_400 | 10 |
| benign_v4_400 | opus | V4 | c10_storm2_w80 | 10 |
| benign_v4_400 | opus | benign | c09_storm2_w80 | 9 |
| benign_v4_400 | opus | benign | c10_replay_400 | 9 |
| benign_v4_400 | opus | benign | c10_storm2_w80 | 9 |
| benign_v4_400 | qwen3-14b | V4 | c09_storm2_w80 | 10 |
| benign_v4_400 | qwen3-14b | V4 | c10_replay_400 | 10 |
| benign_v4_400 | qwen3-14b | V4 | c10_storm2_w80 | 10 |
| benign_v4_400 | qwen3-14b | benign | c09_storm2_w80 | 9 |
| benign_v4_400 | qwen3-14b | benign | c10_replay_400 | 9 |
| benign_v4_400 | qwen3-14b | benign | c10_storm2_w80 | 9 |
| benign_v4_400 | qwen3.6-27b-fp8 | V4 | c09_storm2_w80 | 10 |
| benign_v4_400 | qwen3.6-27b-fp8 | V4 | c10_replay_400 | 10 |
| benign_v4_400 | qwen3.6-27b-fp8 | V4 | c10_storm2_w80 | 10 |
| benign_v4_400 | qwen3.6-27b-fp8 | benign | c09_storm2_w80 | 9 |
| benign_v4_400 | qwen3.6-27b-fp8 | benign | c10_replay_400 | 9 |
| benign_v4_400 | qwen3.6-27b-fp8 | benign | c10_storm2_w80 | 9 |
| benign_v4_400 | sol | V4 | c09_storm2_w80 | 10 |
| benign_v4_400 | sol | V4 | c10_replay_400 | 10 |
| benign_v4_400 | sol | V4 | c10_storm2_w80 | 10 |
| benign_v4_400 | sol | benign | c09_storm2_w80 | 9 |
| benign_v4_400 | sol | benign | c10_replay_400 | 9 |
| benign_v4_400 | sol | benign | c10_storm2_w80 | 9 |
| benign_v4_400 | sonnet | V4 | c09_storm2_w80 | 10 |
| benign_v4_400 | sonnet | V4 | c10_replay_400 | 10 |
| benign_v4_400 | sonnet | V4 | c10_storm2_w80 | 10 |
| benign_v4_400 | sonnet | benign | c09_storm2_w80 | 9 |
| benign_v4_400 | sonnet | benign | c10_replay_400 | 9 |
| benign_v4_400 | sonnet | benign | c10_storm2_w80 | 9 |
| opus_core_v3 | opus | V3 | c09_storm2_w80 | 17 |
| opus_core_v3 | opus | V3 | c10_replay_400 | 20 |
| opus_core_v3 | opus | V3 | c10_storm2_w80 | 7 |

## The comparison

`delta` is the Tier 1 bound minus the Tier 2 bound on the same adjusted instance, relative to `max(LB_tier2, 1 bh)`. *Tier 1 tighter* counts rows where the solver bound strictly exceeds the analytic one. *Vacuous* counts rows where the solver proved nothing and returned 0.0. *Not proved optimal* is the timeout share: the solver used its whole budget without closing the instance.

| budget | rows | Tier 1 tighter | Tier 1 vacuous | not proved optimal | median delta (rel, tighter rows) | max delta (rel) | median gap movement | max gap movement | median solve wall s | p90 solve wall s |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 s | 444 | 92 (20.7%) | 327 (73.6%) | 72.7% | +5.41e-04 | +1.18e-03 | 0.00e+00 | 6.44e-04 | 1.38 | 5.30 |
| 5 s | 444 | 243 (54.7%) | 176 (39.6%) | 67.6% | +9.49e-04 | +2.23e-03 | 0.00e+00 | 2.37e-03 | 5.63 | 9.19 |

Gap movement is `gap(Tier 2) - gap(best of both)`: how much of the certified gap the solver bound removes when it is allowed to help. It is non-negative by construction, because the maximum of two admissible bounds is admissible.

### What Tier 1 alone would do to the same accepted proposals

| budget | rows | median gap (Tier 2) | median gap (Tier 1 only) | median gap (best) | would be refused under Tier 1 only |
|---|---|---|---|---|---|
| 1 s | 444 | 0.0047 | 567.9288 | 0.0047 | 291 (65.5%) |
| 5 s | 444 | 0.0047 | 0.0469 | 0.0044 | 140 (31.5%) |

Every sampled row is one the accepted Tier 2 certificate ACCEPTED. The last column is the share a Tier-1-only guard would refuse instead, at tau = 0.2: a vacuous solver bound inflates the certified gap above tolerance, so the proposal is blocked for want of evidence rather than for want of quality.

The Tier-1-only median gap is large wherever the solver bound is vacuous, and that is arithmetic rather than a quality signal: with LB = 0 the gap convention `(obj - LB) / max(LB, 1 bh)` returns the realized objective itself, in weighted business hours.

### Per stratum

| stratum | budget | rows | Tier 1 tighter | Tier 1 vacuous | proved optimal | median delta (rel, tighter rows) | median Tier 1 solve wall s | median Tier 2 wall ms |
|---|---|---|---|---|---|---|---|---|
| c09_storm2_w80 | 1 s | 151 | 0.0% | 100.0% | 0.0% | - | 1.39 | 0.681 |
| c09_storm2_w80 | 5 s | 151 | 100.0% | 0.0% | 0.0% | +1.10e-03 | 5.64 | 0.698 |
| c10_replay_400 | 1 s | 153 | 60.1% | 23.5% | 79.1% | +5.41e-04 | 0.74 | 0.121 |
| c10_replay_400 | 5 s | 153 | 60.1% | 23.5% | 94.1% | +5.41e-04 | 0.74 | 0.126 |
| c10_storm2_w80 | 1 s | 140 | 0.0% | 100.0% | 0.0% | - | 5.22 | 3.173 |
| c10_storm2_w80 | 5 s | 140 | 0.0% | 100.0% | 0.0% | - | 9.13 | 3.127 |

The Tier 2 column is milliseconds and the Tier 1 column is seconds; the two are not typos of each other.

### Per sample part

| sample part | budget | rows | Tier 1 tighter | Tier 1 vacuous | median gap (Tier 2) | median gap (best) | refused under Tier 1 only |
|---|---|---|---|---|---|---|---|
| benign_v4_400 | 1 s | 400 | 19.0% | 75.8% | 0.0027 | 0.0027 | 66.8% |
| benign_v4_400 | 5 s | 400 | 52.5% | 42.2% | 0.0027 | 0.0027 | 33.2% |
| opus_core_v3 | 1 s | 44 | 36.4% | 54.5% | 0.0929 | 0.0925 | 54.5% |
| opus_core_v3 | 5 s | 44 | 75.0% | 15.9% | 0.0929 | 0.0925 | 15.9% |

## Single-stream guard latency

Measured on a 200-row sub-sample of the same sample, one proposal at a time, pinned to core(s) [0], with every numerical runtime capped at one thread. The bulk comparison had not started. The Tier 1 row is measured at `tier1_workers = 1` because one pinned core is one worker; the bulk pass above runs the frozen default of 4.

| stage | rows | median ms | p90 ms | max ms |
|---|---|---|---|---|
| stage 1, schema | 200 | 1.29 | 2.37 | 20.2 |
| stage 2, feasibility | 200 | 28.66 | 409.37 | 605.1 |
| stage 3, quality (Tier 2) | 200 | 1.40 | 7.50 | 24.5 |
| **whole guard, Tier 2** | 200 | 34.98 | 434.40 | 627.8 |
| stage 3, quality (Tier 1, 1 s budget) | 200 | 1360.04 | 5287.03 | 5663.8 |
| whole guard, Tier 1 at 1 s | 200 | 1394.45 | 5691.64 | 6080.8 |

Per stratum, whole-guard Tier 2 latency (the deployed configuration):

| stratum | rows | schema ms | feas ms | qual Tier 2 ms | whole guard ms (median) | whole guard ms (p90) | qual Tier 1 1 s ms |
|---|---|---|---|---|---|---|---|
| c09_storm2_w80 | 70 | 1.29 | 30.88 | 1.41 | 36.47 | 47.59 | 1373 |
| c10_replay_400 | 72 | 1.08 | 4.65 | 0.25 | 6.53 | 10.99 | 1132 |
| c10_storm2_w80 | 58 | 2.29 | 386.52 | 7.25 | 408.06 | 519.78 | 5226 |

Load context at each phase:

| phase | timestamp | uptime (load averages) | cores |
|---|---|---|---|
| latency (single stream, core 0) | 2026-08-13 13:53:54 +0800 | `13:53:54 up 2 days, 23:06,  2 users,  load average: 5.57, 5.51, 4.20` | 24 |
| bulk comparison (cores [0, 1, 2, 3, 4, 5]) | 2026-08-13 14:02:51 +0800 | `14:02:51 up 2 days, 23:15,  2 users,  load average: 4.74, 5.62, 4.89` | 24 |

Files: `rows.jsonl` (one line per sampled row, both budgets), `summary.json`, `summary.md`.
