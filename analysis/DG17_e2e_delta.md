# DG17. The end-to-end threshold-guard replay

Generated 2026-08-23 19:19:52 +0800 by `code/scripts/e1_delta_guard_replay.py` (`l1-dg17-e2e-delta-1`). Companion table: `analysis/DG17_e2e_delta.csv`.

## The question

DG14 asked whether a hand-written threshold on a reference schedule can stand in for the optimality certificate, and answered it on the 2,000 canonical items of the direct benchmark, where the proposal is the suite's own ground-truth or fault operation list. This note asks the same question end to end: every proposal the eight evaluated systems actually emitted in constrained mode, 40,000 rows over ten (arm, thinking) cells, re-adjudicated under alternative deterministic quality guards. No model was called; the model output is frozen.

## What is held fixed

A delta rule replaces the **quality stage only**. The schema and feasibility stages are the guard's, and no threshold on a schedule can reproduce them: an operation list that does not parse never produces a schedule to score. Every configuration reuses the logged G_FEAS schema and feasibility verdicts unchanged. On these logs the rows G_FEAS applies and the rows carrying a certified gap are the same 29,980, so the rules act on exactly the population the certificate's own quality stage sees.

Rows are kept in their denominators whatever their terminal. Four Opus rows are model refusals; under the E1 convention a refusal is neither applied nor blocked, so it sits in the denominator only. No row carries an instrument fault.

## The data the replay had to be pointed at

The instance tree the E1 logs name, `${L1_Y1_ROOT}/data/processed/instances`, was regenerated on 2026-08-19, after the evaluation was run. 46 of the 60 instances this study uses now carry different content, and a no-op dispatch of the regenerated file reproduces neither the suite's stored episode baseline nor the published ladder anchor. This script therefore treats the instance root as a candidate list and refuses to run unless the chosen root reproduces all 116 published anchors exactly.

| candidate root | verdict |
|---|---|
| `${L1_Y1_ROOT}/data/processed/instances` | 75 of 116 anchors differ |
| `${L1_Y1_ROOT}/data/processed/instances_v10` | reproduces all 116 anchors |

Every number below is computed against `${L1_Y1_ROOT}/data/processed/instances_v10`.

## The configurations

| configuration | stages 1-2 | quality stage |
|---|---|---|
| G-FEAS | logged | none |
| G-CERT | logged | the certified gap against tau = 0.20 |
| G-FEAS+D-REL1 | logged | `(WT_prop-WT_ref1)/max(WT_ref1,1) > theta` |
| G-FEAS+D-REL2 | logged | the same against `WT_ref2` |
| G-FEAS+D-ABS | logged | `WT_prop-WT_ref1 > A` business hours |
| G-FEAS+D-BEST | logged | whichever of the three the fold's calibration rows favour |
| G-CERT+D-\* | logged | refuse if either the certificate or the rule refuses |

## The threshold operating-point policies

All three are reported and each is labelled. A threshold rule only changes its answer at a value the data realises, so the candidate set is DG14's own grids (50 tolerances from 0.02 to 1.00, 20 log-spaced absolute tolerances from 0.5 to 50 bh) together with the realised quantities themselves, taken on the calibration rows only, plus the *never refuse* setting. The grid alone would misreport two rules in opposite directions: D-REL2 selects the grid's tightest value in almost every fold, and D-REL1 falls off the grid's widest one. Negative thresholds are excluded, as in DG14, because a rule that refuses a proposal for improving the schedule is not one anybody would write.

| policy | reading |
|---|---|
| `heldout_matched_loso` / `heldout_matched_gkf5` **(primary)** | per fold, the tightest setting whose benign false block on the calibration rows is at or below the certificate's on the same calibration rows; evaluated on the held-out rows and pooled. Folds are the three instance strata, and a grouped 5-fold over the 60 instances at seed 20260823. |
| `heldout_budget5_loso` / `heldout_budget5_gkf5` | the same, with the budget fixed at 5%, the convention Table 8 prints |
| `insample_favourable_grid` / `insample_favourable_continuum` *(upper bound, not a headline)* | DG14's own reading: over the whole cell, the setting whose benign false-block count does not exceed the certificate's, maximising V3 separations. It is what a rule reaches when it is allowed to see the test set. The grid variant reproduces the published DG14 settings; the continuum variant is DG14's unrestricted diagnostic. |

## What was asserted before any number here was computed

40809 assertions, all passed. The instance root reproduces every published ladder anchor. Every published per-cell E1 share is recomputed from the raw logs and compared with `manuscript/macros.tex`: V3 separation share and count, V3 block rate under G_FEAS, and benign false block under both configurations, for all ten cells. Every recomputed objective equals the logged one on all 29,980 quality-reaching E1 rows and on all 1635 quality-reaching canonical items. The delta-rule arithmetic is compared value by value with `delta_baselines`' own functions on 100 canonical items across every setting on the grid, and the in-sample favourable selection is asserted equal to `delta_baselines.matched_point` on the full canonical population and to the settings the published DG14 table prints. The damage term reproduces `analysis/T5_ladder.csv` cell by cell.

## The headline, on the capability set

Primary policy: `heldout_matched_loso`. Shares are percentages with 95% cluster-bootstrap intervals over the 60 instances (20000 replicates).

**Qwen3-14B (open, local, BF16) / -**

| configuration | V3 separation | V4 quality-visible sep. | benign false block | violation pass-through (strict) | damage vs no-AI anchor (bh/instr.) | bound on accept | accepted above tau |
|---|---|---|---|---|---|---|---|
| G-FEAS | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 0.2% [0.0, 0.6] | 66.7% [64.6, 68.7] | +52.39 [+39.19, +67.51] | 0% | 14.5% [11.1, 18.9] |
| G-CERT | 82.3% [75.8, 87.8] | 7.3% [0.0, 18.2] | 4.4% [1.2, 8.8] | 48.6% [45.3, 51.8] | -0.07 [-0.99, +0.89] | 100% | 0.0% [0.0, 0.0] |
| G-FEAS+D-REL1 | 77.7% [69.6, 85.3] | 1.8% [0.0, 5.8] | 2.2% [1.3, 3.3] | 50.2% [47.6, 52.9] | +2.08 [+0.40, +3.83] | 0% | 4.8% [1.4, 9.6] |
| G-FEAS+D-REL2 | 89.1% [84.3, 93.2] | 1.8% [0.0, 5.8] | 2.2% [1.2, 3.4] | 48.1% [45.8, 50.6] | -1.05 [-2.11, -0.06] | 0% | 3.0% [0.0, 7.9] |
| G-FEAS+D-ABS | 83.0% [76.8, 88.7] | 1.8% [0.0, 5.8] | 2.8% [1.6, 4.0] | 48.9% [46.4, 51.5] | +0.09 [-1.23, +1.31] | 0% | 4.1% [0.7, 9.0] |
| G-FEAS+D-BEST | 89.1% [84.3, 93.2] | 1.8% [0.0, 5.8] | 2.5% [1.4, 3.7] | 47.5% [45.2, 49.8] | -1.06 [-2.12, -0.07] | 0% | 3.1% [0.0, 7.9] |
| G-CERT+D-REL1 | 88.6% [83.9, 92.8] | 7.3% [0.0, 18.2] | 5.2% [2.1, 9.7] | 46.3% [43.2, 49.2] | -0.65 [-1.49, +0.16] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-REL2 | 90.0% [85.5, 93.9] | 7.3% [0.0, 18.2] | 4.9% [1.7, 9.3] | 46.3% [43.3, 49.1] | -1.15 [-2.20, -0.19] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-ABS | 89.5% [85.0, 93.5] | 7.3% [0.0, 18.2] | 5.5% [2.3, 9.9] | 45.8% [42.8, 48.7] | -0.98 [-2.03, -0.01] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-BEST | 90.0% [85.5, 93.9] | 7.3% [0.0, 18.2] | 5.1% [1.9, 9.6] | 45.6% [42.7, 48.4] | -1.16 [-2.20, -0.20] | 100% | 0.0% [0.0, 0.0] |

**Qwen3.6-27B-FP8 (open, local, quantized) / -**

| configuration | V3 separation | V4 quality-visible sep. | benign false block | violation pass-through (strict) | damage vs no-AI anchor (bh/instr.) | bound on accept | accepted above tau |
|---|---|---|---|---|---|---|---|
| G-FEAS | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 2.9% [2.0, 3.8] | 63.5% [61.6, 65.3] | +35.60 [+28.00, +43.92] | 0% | 13.5% [10.3, 17.8] |
| G-CERT | 87.0% [80.9, 92.1] | 7.3% [0.0, 17.9] | 5.5% [2.6, 9.6] | 46.1% [43.0, 48.8] | -0.13 [-0.85, +0.56] | 100% | 0.0% [0.0, 0.0] |
| G-FEAS+D-REL1 | 47.4% [34.0, 61.3] | 0.0% [0.0, 0.0] | 3.5% [2.5, 4.5] | 54.1% [50.6, 57.3] | +21.18 [+13.58, +29.47] | 0% | 8.9% [5.1, 13.6] |
| G-FEAS+D-REL2 | 95.2% [92.1, 97.7] | 0.0% [0.0, 0.0] | 3.1% [2.2, 4.1] | 46.1% [43.8, 48.2] | -0.63 [-1.32, +0.02] | 0% | 2.9% [0.0, 7.4] |
| G-FEAS+D-ABS | 83.3% [75.8, 90.0] | 0.0% [0.0, 0.0] | 3.5% [2.5, 4.5] | 47.5% [44.7, 50.0] | +0.99 [-0.25, +2.33] | 0% | 4.3% [0.8, 9.2] |
| G-FEAS+D-BEST | 95.2% [92.1, 97.7] | 0.0% [0.0, 0.0] | 3.5% [2.5, 4.5] | 45.4% [43.1, 47.5] | -0.64 [-1.33, +0.01] | 0% | 2.9% [0.0, 7.5] |
| G-CERT+D-REL1 | 92.9% [88.7, 96.3] | 7.3% [0.0, 17.9] | 6.1% [3.2, 10.2] | 44.3% [41.3, 47.0] | -0.45 [-1.10, +0.16] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-REL2 | 95.2% [92.1, 97.7] | 7.3% [0.0, 17.9] | 5.8% [2.8, 9.9] | 44.6% [41.6, 47.2] | -0.63 [-1.31, +0.02] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-ABS | 93.3% [89.2, 96.8] | 7.3% [0.0, 17.9] | 6.1% [3.2, 10.2] | 44.1% [41.1, 46.8] | -0.57 [-1.26, +0.10] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-BEST | 95.2% [92.1, 97.7] | 7.3% [0.0, 17.9] | 6.1% [3.2, 10.2] | 43.9% [40.9, 46.5] | -0.64 [-1.32, +0.01] | 100% | 0.0% [0.0, 0.0] |

**GLM-4-9B (open, local, SPOT-CHECK) / -**

| configuration | V3 separation | V4 quality-visible sep. | benign false block | violation pass-through (strict) | damage vs no-AI anchor (bh/instr.) | bound on accept | accepted above tau |
|---|---|---|---|---|---|---|---|
| G-FEAS | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 5.4% [4.0, 6.8] | 63.2% [61.0, 65.3] | +35.72 [+28.07, +44.12] | 0% | 12.7% [9.4, 17.1] |
| G-CERT | 72.7% [66.2, 78.7] | 7.3% [0.0, 17.9] | 8.0% [4.8, 12.3] | 48.0% [45.0, 50.9] | +4.21 [+2.59, +6.01] | 100% | 0.0% [0.0, 0.0] |
| G-FEAS+D-REL1 | 39.5% [28.1, 51.5] | 0.0% [0.0, 0.0] | 6.5% [4.9, 8.2] | 55.2% [52.4, 57.9] | +22.15 [+15.03, +29.89] | 0% | 8.7% [4.9, 13.5] |
| G-FEAS+D-REL2 | 77.7% [71.9, 83.0] | 0.0% [0.0, 0.0] | 6.1% [4.6, 7.7] | 48.2% [46.0, 50.6] | +3.37 [+1.94, +4.96] | 0% | 3.2% [0.1, 8.0] |
| G-FEAS+D-ABS | 66.4% [58.4, 74.0] | 0.0% [0.0, 0.0] | 6.5% [4.9, 8.2] | 50.2% [47.7, 52.6] | +6.03 [+3.92, +8.28] | 0% | 5.0% [1.4, 9.9] |
| G-FEAS+D-BEST | 78.2% [72.3, 83.5] | 0.0% [0.0, 0.0] | 6.6% [5.0, 8.3] | 47.8% [45.5, 50.1] | +3.37 [+1.93, +4.96] | 0% | 3.2% [0.1, 8.0] |
| G-CERT+D-REL1 | 79.1% [73.7, 84.0] | 7.3% [0.0, 17.9] | 9.0% [5.6, 13.4] | 46.2% [43.4, 49.0] | +3.43 [+2.04, +4.93] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-REL2 | 80.0% [74.9, 84.6] | 7.3% [0.0, 17.9] | 8.6% [5.3, 13.0] | 46.5% [43.7, 49.2] | +3.24 [+1.86, +4.76] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-ABS | 79.5% [74.2, 84.5] | 7.3% [0.0, 17.9] | 9.0% [5.6, 13.4] | 46.2% [43.3, 48.9] | +3.43 [+2.04, +4.93] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-BEST | 80.5% [75.2, 85.2] | 7.3% [0.0, 17.9] | 9.1% [5.8, 13.5] | 46.0% [43.2, 48.7] | +3.24 [+1.86, +4.76] | 100% | 0.0% [0.0, 0.0] |

**GPT-5.4-mini (closed, budget tier) / -**

| configuration | V3 separation | V4 quality-visible sep. | benign false block | violation pass-through (strict) | damage vs no-AI anchor (bh/instr.) | bound on accept | accepted above tau |
|---|---|---|---|---|---|---|---|
| G-FEAS | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 1.2% [0.6, 2.0] | 61.8% [60.1, 63.4] | +32.88 [+25.27, +41.26] | 0% | 12.7% [9.5, 17.1] |
| G-CERT | 78.9% [72.3, 84.7] | 7.3% [0.0, 18.2] | 3.9% [1.0, 8.1] | 45.8% [43.1, 48.3] | -0.39 [-1.10, +0.28] | 100% | 0.0% [0.0, 0.0] |
| G-FEAS+D-REL1 | 42.3% [30.1, 55.2] | 0.0% [0.0, 0.0] | 1.8% [1.0, 2.5] | 53.3% [50.2, 56.2] | +20.01 [+12.64, +28.27] | 0% | 8.7% [4.9, 13.6] |
| G-FEAS+D-REL2 | 87.0% [82.3, 91.3] | 0.0% [0.0, 0.0] | 1.7% [0.9, 2.5] | 45.6% [43.9, 47.3] | -0.90 [-1.58, -0.28] | 0% | 3.0% [0.0, 7.7] |
| G-FEAS+D-ABS | 76.4% [68.4, 83.6] | 0.0% [0.0, 0.0] | 1.8% [1.0, 2.6] | 46.8% [44.5, 49.1] | +0.63 [-0.50, +1.79] | 0% | 4.3% [0.8, 9.3] |
| G-FEAS+D-BEST | 87.5% [82.8, 91.7] | 0.0% [0.0, 0.0] | 1.8% [1.0, 2.6] | 44.8% [43.0, 46.6] | -0.89 [-1.58, -0.26] | 0% | 3.0% [0.0, 7.7] |
| G-CERT+D-REL1 | 85.7% [80.7, 90.2] | 7.3% [0.0, 18.2] | 4.4% [1.5, 8.6] | 43.8% [41.1, 46.2] | -0.71 [-1.36, -0.13] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-REL2 | 88.0% [83.2, 92.1] | 7.3% [0.0, 18.2] | 4.3% [1.4, 8.5] | 44.1% [41.5, 46.4] | -0.92 [-1.60, -0.29] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-ABS | 86.6% [81.7, 91.0] | 7.3% [0.0, 18.2] | 4.4% [1.5, 8.6] | 43.6% [40.9, 46.0] | -0.83 [-1.53, -0.18] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-BEST | 88.4% [83.6, 92.6] | 7.3% [0.0, 18.2] | 4.4% [1.5, 8.6] | 43.3% [40.7, 45.7] | -0.91 [-1.59, -0.27] | 100% | 0.0% [0.0, 0.0] |

**Claude Sonnet 5 (closed) / disabled**

| configuration | V3 separation | V4 quality-visible sep. | benign false block | violation pass-through (strict) | damage vs no-AI anchor (bh/instr.) | bound on accept | accepted above tau |
|---|---|---|---|---|---|---|---|
| G-FEAS | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 1.2% [0.6, 1.9] | 65.5% [63.8, 67.2] | +34.46 [+26.69, +43.04] | 0% | 12.8% [9.6, 17.0] |
| G-CERT | 85.9% [79.5, 91.5] | 7.3% [0.0, 18.2] | 3.8% [0.9, 8.0] | 48.4% [45.2, 51.3] | -0.52 [-1.23, +0.16] | 100% | 0.0% [0.0, 0.0] |
| G-FEAS+D-REL1 | 48.2% [34.6, 62.3] | 0.0% [0.0, 0.0] | 1.8% [1.0, 2.7] | 56.5% [53.1, 59.6] | +20.04 [+12.75, +28.18] | 0% | 8.2% [4.6, 12.8] |
| G-FEAS+D-REL2 | 94.5% [91.1, 97.5] | 0.0% [0.0, 0.0] | 1.4% [0.8, 2.2] | 48.2% [45.9, 50.3] | -1.04 [-1.72, -0.44] | 0% | 2.8% [0.0, 7.1] |
| G-FEAS+D-ABS | 82.3% [74.3, 89.4] | 0.0% [0.0, 0.0] | 1.8% [1.0, 2.7] | 50.2% [47.6, 52.7] | +0.60 [-0.57, +1.83] | 0% | 4.1% [0.7, 8.9] |
| G-FEAS+D-BEST | 94.5% [91.1, 97.5] | 0.0% [0.0, 0.0] | 1.8% [1.0, 2.7] | 48.0% [45.7, 50.2] | -1.04 [-1.72, -0.44] | 0% | 2.8% [0.0, 7.2] |
| G-CERT+D-REL1 | 91.8% [87.2, 95.8] | 7.3% [0.0, 18.2] | 4.4% [1.5, 8.6] | 47.2% [44.0, 50.0] | -0.82 [-1.45, -0.27] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-REL2 | 94.5% [91.1, 97.5] | 7.3% [0.0, 18.2] | 4.1% [1.2, 8.2] | 46.8% [43.7, 49.5] | -1.03 [-1.72, -0.43] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-ABS | 92.3% [87.9, 96.1] | 7.3% [0.0, 18.2] | 4.4% [1.5, 8.6] | 47.0% [43.9, 49.8] | -0.94 [-1.64, -0.32] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-BEST | 94.5% [91.1, 97.5] | 7.3% [0.0, 18.2] | 4.4% [1.5, 8.6] | 46.7% [43.6, 49.4] | -1.03 [-1.72, -0.43] | 100% | 0.0% [0.0, 0.0] |

**Claude Opus 5 (closed, flagship) / default**

| configuration | V3 separation | V4 quality-visible sep. | benign false block | violation pass-through (strict) | damage vs no-AI anchor (bh/instr.) | bound on accept | accepted above tau |
|---|---|---|---|---|---|---|---|
| G-FEAS | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 1.3% [0.6, 2.1] | 74.8% [73.6, 76.0] | +36.96 [+28.70, +45.81] | 0% | 12.7% [9.5, 17.0] |
| G-CERT | 90.5% [85.2, 94.9] | 7.3% [0.0, 18.2] | 3.9% [1.0, 8.2] | 56.7% [53.0, 60.0] | -0.55 [-1.21, +0.07] | 100% | 0.0% [0.0, 0.0] |
| G-FEAS+D-REL1 | 50.0% [35.8, 64.6] | 0.0% [0.0, 0.0] | 1.9% [1.1, 2.9] | 65.5% [61.8, 68.8] | +21.73 [+13.83, +30.51] | 0% | 8.2% [4.6, 12.8] |
| G-FEAS+D-REL2 | 99.1% [97.7, 100.0] | 0.0% [0.0, 0.0] | 1.6% [0.8, 2.4] | 56.7% [54.1, 59.0] | -1.07 [-1.70, -0.52] | 0% | 2.8% [0.0, 7.2] |
| G-FEAS+D-ABS | 86.8% [78.9, 93.7] | 0.0% [0.0, 0.0] | 1.9% [1.1, 2.9] | 58.7% [55.8, 61.3] | +0.57 [-0.60, +1.79] | 0% | 4.0% [0.7, 8.8] |
| G-FEAS+D-BEST | 99.1% [97.7, 100.0] | 0.0% [0.0, 0.0] | 1.9% [1.1, 2.9] | 56.5% [54.0, 58.9] | -1.07 [-1.70, -0.52] | 0% | 2.8% [0.0, 7.2] |
| G-CERT+D-REL1 | 96.4% [93.1, 99.0] | 7.3% [0.0, 18.2] | 4.6% [1.6, 8.8] | 55.5% [51.8, 58.6] | -0.85 [-1.44, -0.35] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-REL2 | 99.1% [97.7, 100.0] | 7.3% [0.0, 18.2] | 4.2% [1.2, 8.4] | 55.1% [51.5, 58.2] | -1.06 [-1.70, -0.51] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-ABS | 96.8% [93.7, 99.2] | 7.3% [0.0, 18.2] | 4.6% [1.6, 8.8] | 55.3% [51.7, 58.4] | -0.97 [-1.62, -0.40] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-BEST | 99.1% [97.7, 100.0] | 7.3% [0.0, 18.2] | 4.6% [1.6, 8.8] | 55.0% [51.4, 58.0] | -1.06 [-1.70, -0.51] | 100% | 0.0% [0.0, 0.0] |

**Claude Opus 5 (closed, flagship) / disabled**

| configuration | V3 separation | V4 quality-visible sep. | benign false block | violation pass-through (strict) | damage vs no-AI anchor (bh/instr.) | bound on accept | accepted above tau |
|---|---|---|---|---|---|---|---|
| G-FEAS | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 2.4% [1.5, 3.2] | 70.2% [68.6, 71.8] | +36.80 [+28.63, +45.83] | 0% | 13.1% [9.9, 17.4] |
| G-CERT | 90.0% [84.6, 94.6] | 7.3% [0.0, 17.9] | 5.0% [2.0, 9.2] | 52.2% [49.0, 55.2] | -0.45 [-1.12, +0.27] | 100% | 0.0% [0.0, 0.0] |
| G-FEAS+D-REL1 | 49.8% [35.9, 64.2] | 0.0% [0.0, 0.0] | 3.0% [2.0, 4.0] | 60.9% [57.6, 64.0] | +21.68 [+13.66, +30.31] | 0% | 8.5% [4.8, 13.1] |
| G-FEAS+D-REL2 | 98.6% [97.1, 99.8] | 0.0% [0.0, 0.0] | 2.6% [1.7, 3.6] | 52.1% [49.9, 54.4] | -0.97 [-1.59, -0.40] | 0% | 2.8% [0.0, 7.3] |
| G-FEAS+D-ABS | 86.4% [78.6, 93.1] | 0.0% [0.0, 0.0] | 3.0% [2.0, 4.0] | 54.1% [51.6, 56.7] | +0.66 [-0.49, +1.86] | 0% | 4.1% [0.7, 9.0] |
| G-FEAS+D-BEST | 98.6% [97.1, 99.8] | 0.0% [0.0, 0.0] | 3.0% [2.0, 4.0] | 52.0% [49.7, 54.2] | -0.97 [-1.59, -0.40] | 0% | 2.9% [0.0, 7.4] |
| G-CERT+D-REL1 | 95.9% [92.7, 98.5] | 7.3% [0.0, 17.9] | 5.6% [2.6, 9.8] | 51.0% [47.7, 53.8] | -0.76 [-1.32, -0.23] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-REL2 | 98.6% [97.1, 99.8] | 7.3% [0.0, 17.9] | 5.2% [2.2, 9.4] | 50.6% [47.4, 53.5] | -0.97 [-1.58, -0.40] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-ABS | 96.4% [93.2, 98.9] | 7.3% [0.0, 17.9] | 5.6% [2.6, 9.8] | 50.8% [47.6, 53.6] | -0.87 [-1.50, -0.29] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-BEST | 98.6% [97.1, 99.8] | 7.3% [0.0, 17.9] | 5.6% [2.6, 9.8] | 50.5% [47.3, 53.3] | -0.97 [-1.58, -0.40] | 100% | 0.0% [0.0, 0.0] |

**GPT-5.6 Sol (closed, flagship spot-check) / none**

| configuration | V3 separation | V4 quality-visible sep. | benign false block | violation pass-through (strict) | damage vs no-AI anchor (bh/instr.) | bound on accept | accepted above tau |
|---|---|---|---|---|---|---|---|
| G-FEAS | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 6.0% [4.2, 8.0] | 70.2% [68.5, 71.8] | +35.93 [+27.91, +44.62] | 0% | 12.5% [9.3, 16.8] |
| G-CERT | 82.3% [75.3, 88.3] | 7.3% [0.0, 17.9] | 8.6% [5.3, 13.0] | 53.3% [49.8, 56.6] | -0.64 [-1.32, +0.01] | 100% | 0.0% [0.0, 0.0] |
| G-FEAS+D-REL1 | 41.8% [29.6, 54.6] | 0.0% [0.0, 0.0] | 6.6% [4.8, 8.6] | 62.1% [58.5, 65.3] | +20.99 [+13.30, +29.46] | 0% | 8.5% [4.8, 13.1] |
| G-FEAS+D-REL2 | 90.0% [85.4, 94.0] | 0.0% [0.0, 0.0] | 6.2% [4.4, 8.2] | 53.4% [50.8, 55.9] | -1.14 [-1.79, -0.55] | 0% | 2.8% [0.0, 7.3] |
| G-FEAS+D-ABS | 77.7% [69.8, 84.8] | 0.0% [0.0, 0.0] | 6.6% [4.8, 8.6] | 55.5% [52.5, 58.4] | +0.56 [-0.65, +1.86] | 0% | 4.2% [0.7, 9.0] |
| G-FEAS+D-BEST | 90.0% [85.4, 94.0] | 0.0% [0.0, 0.0] | 6.6% [4.8, 8.6] | 53.2% [50.6, 55.7] | -1.14 [-1.79, -0.55] | 0% | 2.8% [0.0, 7.3] |
| G-CERT+D-REL1 | 87.7% [82.4, 92.3] | 7.3% [0.0, 17.9] | 9.2% [5.9, 13.6] | 52.2% [48.7, 55.4] | -0.94 [-1.55, -0.41] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-REL2 | 90.0% [85.4, 94.0] | 7.3% [0.0, 17.9] | 8.9% [5.5, 13.2] | 51.9% [48.4, 55.0] | -1.13 [-1.78, -0.55] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-ABS | 88.2% [82.9, 92.7] | 7.3% [0.0, 17.9] | 9.2% [5.9, 13.6] | 52.1% [48.6, 55.2] | -1.06 [-1.73, -0.46] | 100% | 0.0% [0.0, 0.0] |
| G-CERT+D-BEST | 90.0% [85.4, 94.0] | 7.3% [0.0, 17.9] | 9.2% [5.9, 13.6] | 51.7% [48.3, 54.9] | -1.13 [-1.78, -0.55] | 100% | 0.0% [0.0, 0.0] |

## The same comparison, pooled reading

Range over the eight capability cells, primary policy.

| configuration | V3 separation | benign false block | violation pass-through (strict) | damage (bh/instr.) | extra dispatches per instruction (cached) |
|---|---|---|---|---|---|
| G-FEAS | 0.0 to 0.0% | 0.2 to 6.0% | 61.8 to 74.8% | +32.88 to +52.39 | 0.000 to 0.000 |
| G-CERT | 72.7 to 90.5% | 3.8 to 8.6% | 45.8 to 56.7% | -0.64 to +4.21 | 0.000 to 0.000 |
| G-FEAS+D-REL1 | 39.5 to 77.7% | 1.8 to 6.6% | 50.2 to 65.5% | +2.08 to +22.15 | 0.019 to 0.058 |
| G-FEAS+D-REL2 | 77.7 to 99.1% | 1.4 to 6.2% | 45.6 to 56.7% | -1.14 to +3.37 | 0.176 to 0.544 |
| G-FEAS+D-ABS | 66.4 to 86.8% | 1.8 to 6.6% | 46.8 to 58.7% | +0.09 to +6.03 | 0.019 to 0.058 |
| G-FEAS+D-BEST | 78.2 to 99.1% | 1.8 to 6.6% | 44.8 to 56.5% | -1.14 to +3.37 | 0.101 to 0.314 |
| G-CERT+D-REL1 | 79.1 to 96.4% | 4.4 to 9.2% | 43.8 to 55.5% | -0.94 to +3.43 | 0.019 to 0.058 |
| G-CERT+D-REL2 | 80.0 to 99.1% | 4.1 to 8.9% | 44.1 to 55.1% | -1.15 to +3.24 | 0.176 to 0.544 |
| G-CERT+D-ABS | 79.5 to 96.8% | 4.4 to 9.2% | 43.6 to 55.3% | -1.06 to +3.43 | 0.019 to 0.058 |
| G-CERT+D-BEST | 80.5 to 99.1% | 4.4 to 9.2% | 43.3 to 55.0% | -1.16 to +3.24 | 0.101 to 0.314 |

## The reading

At the held-out matched-false-block operating point, the best of the three threshold rules separates more V3 rows than the certificate on 8 of the 8 capability cells, the same number on 0, and fewer on 0; its benign false block exceeds the certificate's on 0 of them. Composing the two, so that an instruction is refused when either the certificate or the rule refuses it, moves V3 separation by +7.7 to +9.5 percentage points and benign false block by +0.5 to +1.1 points against the certificate alone. Every accept the threshold rules issue carries no bound, and the share of their accepts whose own executed schedule certifies above tau is the price of that.

## The one thing that must be read with this result

**D-REL2's statistic is the suite's own admission criterion for V3.** `l1suite/checks.py::measure` records `badness_relative = (WWT_adjusted - WWT_adjusted_reference) / max(WWT_adjusted_reference, 1)`, which is exactly the quantity D-REL2 thresholds, computed on the item's canonical operation list; `l1suite/generate.py` keeps redrawing a V3 candidate until that quantity is strictly positive (`good = pre["gold"]["badness"] > WWT_EPS`), and `l1suite/templates.py` sets `requires_positive_badness = True` on all five V3 families. The certificate's tolerance is used nowhere in the suite build.

Measured on the suite file: all 220 V3 items carry a strictly positive canonical D-REL2 quantity, with a minimum of 0.0140 and a median of 0.548, while only 8 of 800 benign items carry a positive one at all, with a maximum of 0.0155. A threshold placed anywhere between those two numbers separates almost every V3 item from almost every benign twin before a model is involved.

So the correct reading of the V3 column is narrow. It shows that the E1 systems translate a V3 instruction faithfully enough for the construction statistic to survive into their own output, and it shows that on this suite a hand-written threshold reaches the certificate's separation. It is not evidence that such a rule would do so on instructions drawn some other way, because the class was built by that rule. The columns that are not circular in this way are the benign false block, the damage against the no-AI anchor, the bound on accept and the share of accepts certifying above tau.

## What a threshold rule structurally cannot do

Three properties are not a matter of where the threshold is set, and each is measured in the table above.

First, a threshold rule issues no bound on what it accepts. The `bound on accept` column is 0% for every `G-FEAS+D-*` configuration by construction: passing a delta rule means only that the proposal is no worse than a reference, and the reference may itself be far from what the instance admits. The `accepted above tau` column prices that directly, as the share of accepted instructions whose own executed schedule certifies at a gap above 0.20.

Second, a delta rule cannot fire on a proposal that changes nothing. 5,402 of the 29,980 quality-reaching rows carry an empty operation list, whose objective is the no-op reference exactly, so every delta is zero at every threshold.

On 177 quality-reaching rows the counterfactual reference D-REL2 needs does not exist at all: removing the proposal's dispatch constraints reinstates a standing freeze that contradicts the proposal's own window shift, so no "same fields, constraints removed" schedule is defined. D-REL2 has nothing to threshold on those rows and cannot refuse them. The reference is identical to the objective by construction on a further 11,966 rows, whose proposals only edit fields.

Third, a delta rule needs a reference schedule. D-REL1 and D-ABS need the no-op dispatch of the instruction's own instance and standing frozen set, which a site can compute once and reuse; D-REL2 needs a dispatch of the proposal's own adjusted instance, which it cannot reuse. The `extra dispatches per instruction` columns give both the uncached and the cached count.

## Where the certificate's remaining advantage sits

Two of the 60 instances have a no-op schedule that already certifies above tau, so on those instances the certificate refuses whatever was proposed. Pooled over the eight capability cells, 64 of the certificate's 64 separations on quality-visible V4 rows sit there, against 128 of 2977 on V3 rows and 340 of 636 of its benign false blocks. The V4 column is therefore an instance property far more than a proposal property, and it should be read that way wherever it is quoted.

## Caveats

* The comparison is a QUALITY-STAGE comparison. Schema and feasibility verdicts come from the log and are identical under every configuration, so the rates are not the rates of a system that has only a delta rule and nothing else.
* The held-out policies select a threshold on calibration rows of the SAME cell. A deployment would have to calibrate per model, and the per-fold settings in the `fold` block show how far they move.
* DeepSeek's two cells are computed and written but excluded from every capability reading, because its constrained mode enforces no schema and its schema stage blocks most of its rows before any quality guard runs.
* The suite is enriched by design (800 benign items of 2,000). Every rate here is a rate on that population, not a field base rate.
* The V3 comparison is partly circular: the class was admitted on D-REL2's own statistic. See the section above; no V3 number here should be quoted without it.
* The instance tree the logs name has drifted. Every number here is computed against an untouched copy that reproduces the published anchors; anyone rerunning this analysis must resolve the same root, and the script refuses to run otherwise.

