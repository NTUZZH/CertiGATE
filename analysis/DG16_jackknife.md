# DG16. How far the direct benchmark's rates move when an instance is removed

Generated 2026-08-23 11:24:41 +0800 by `code/scripts/jackknife_direct.py` (`l1-dg16-jackknife-1`). Companion table: `analysis/DG16_jackknife.csv`.

## The question

The direct benchmark's published rates are class shares pooled over 2000 items that sit on only 60 scheduling instances. This note deletes one instance at a time, recomputes every published rate on what is left, and repeats the exercise for the two other partitions of the same items, the 3 strata and the 33 subclasses. No model is in the loop and nothing is re-run: it is a re-read of `analysis/DG1_direct_guard.csv`.

## The design

A fold deletes one cell of a partition and every rate is recomputed on the remaining items. A fold counts as **effective** for a metric when it removes at least one item from that metric's denominator; deleting a V5-only subclass cannot move the V3 refusal rate, so identity folds are counted and reported but never enter a statistic and are never written out. For a metric `p = Y/N` with effective folds `p_(i)`, the table reports the envelope `min p_(i)` and `max p_(i)`, the jackknife standard error `sqrt(((n-1)/n) * sum (p_(i) - p_bar)^2)`, the bias `(n-1)(p_bar - p)`, and the bias-corrected value `p - bias`. Instances are the sampling unit and are what the published intervals cluster on, so only the instance family's standard error is a sampling standard error; strata and subclasses are constructed by the suite generator, and their spread is descriptive.

No estimate here depends on a choice. Every fold of every family is computed, every metric is reported, and the jackknife is an enumeration rather than a resample. The one threshold in the note is presentational: the prose below names the metrics whose subclass envelope spans more than 10 percentage points, and the full table is printed either way.

## Leave one instance out

Percentages; the `min` and `max` columns name the instance whose deletion attains them; `SE` and `bias` are in percentage points. The last column is the cluster-bootstrap standard error the manuscript already publishes for the same rate in `analysis/DG10_direct_guard_intervals.csv`, on the same scale.

The fold count is the number of instances carrying at least one item of that metric's population: 4 of the 60 instances carry no V3 item, so the V3 rate has 56 folds where the benign rate has 60. Those are the same cluster counts the published intervals report.

| metric | full | folds | min (instance) | max (instance) | range (pp) | jackknife SE (pp) | bias (pp) | published SE (pp) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| benign_refusal | 2.62 | 60 | 1.27 (c09_storm2_w80_u100_0008) | 2.71 (c09_storm2_w80_u100_0000) | 1.44 | 1.852 | 0.012 | 1.848 |
| v3_refusal | 91.36 | 56 | 91.00 (c09_storm2_w80_u100_0022) | 92.20 (c10_replay_400_0008) | 1.21 | 2.465 | -0.048 | 2.447 |
| v1_refusal_all_items | 81.25 | 60 | 80.89 (c10_replay_400_0002) | 81.94 (c09_storm2_w80_u100_0020) | 1.04 | 2.500 | 0.093 | 2.472 |
| v1_refusal_representable | 100.00 | 60 | 100.00 (c09_storm2_w80_u100_0000) | 100.00 (c10_storm2_w80_u100_0011) | 0.00 | 0.000 | 0.000 | 0.000 |
| v2_refusal | 100.00 | 60 | 100.00 (c09_storm2_w80_u100_0000) | 100.00 (c10_storm2_w80_u100_0011) | 0.00 | 0.000 | 0.000 | 0.000 |
| v4_refusal | 20.91 | 60 | 19.82 (c09_storm2_w80_u100_0008) | 21.50 (c09_storm2_w80_u100_0015) | 1.68 | 2.410 | 0.006 | 2.407 |
| v5_refusal_all_items | 3.50 | 60 | 1.53 (c09_storm2_w80_u100_0008) | 3.63 (c09_storm2_w80_u100_0015) | 2.10 | 2.488 | 0.010 | 2.482 |
| v6_refusal_all_items | 19.50 | 60 | 18.37 (c09_storm2_w80_u100_0008) | 19.90 (c10_storm2_w80_u100_0000) | 1.53 | 2.261 | -0.003 | 2.276 |
| v6_refusal_representable | 22.29 | 60 | 21.05 (c09_storm2_w80_u100_0008) | 22.67 (c10_storm2_w80_u100_0010) | 1.62 | 2.515 | -0.015 | 2.480 |
| violations_all | 51.92 | 60 | 51.19 (c09_storm2_w80_u100_0008) | 52.23 (c09_storm2_w80_u100_0015) | 1.05 | 1.273 | 0.004 | - |
| benign_block_feas | 0.00 | 60 | 0.00 (c09_storm2_w80_u100_0000) | 0.00 (c10_storm2_w80_u100_0011) | 0.00 | 0.000 | 0.000 | - |
| benign_block_qual | 2.62 | 60 | 1.27 (c09_storm2_w80_u100_0008) | 2.71 (c09_storm2_w80_u100_0000) | 1.44 | 1.852 | 0.012 | - |
| stage_block_schema | 8.25 | 60 | 8.14 (c10_replay_400_0023) | 8.34 (c10_replay_400_0020) | 0.20 | 0.395 | 0.012 | - |
| stage_block_feas | 10.00 | 60 | 9.90 (c10_storm2_w80_u100_0007) | 10.13 (c10_replay_400_0020) | 0.23 | 0.402 | -0.005 | - |
| stage_reached_qual | 81.75 | 60 | 81.53 (c10_replay_400_0020) | 81.89 (c10_replay_400_0023) | 0.37 | 0.500 | -0.007 | - |
| stage_block_qual | 13.95 | 60 | 12.96 (c09_storm2_w80_u100_0008) | 14.19 (c09_storm2_w80_u100_0021) | 1.23 | 1.548 | -0.001 | - |
| all_refusal | 32.20 | 60 | 31.20 (c09_storm2_w80_u100_0008) | 32.41 (c09_storm2_w80_u100_0015) | 1.21 | 1.430 | 0.006 | - |

The jackknife standard error reproduces the two standard errors the interval file already publishes on all 9 rates it carries: the largest disagreement is 0.016 percentage points against the linearised cluster-robust standard error and 0.035 against the cluster bootstrap. The script asserts the agreement at 0.05 and 0.1 percentage points and exits non-zero otherwise, so the envelope above and the published intervals are two readings of one estimate rather than two estimates.

## Leave one stratum out

Three folds, so the spread is a description of the design rather than a standard error. The strata differ in what they contain, and the table shows how much of each rate each one carries.

| metric | full | without c09_storm2_w80 | without c10_replay_400 | without c10_storm2_w80 | range (pp) |
| --- | --- | --- | --- | --- | --- |
| benign_refusal | 2.62 | 0.00 | 3.84 | 3.25 | 3.84 |
| v3_refusal | 91.36 | 87.74 | 94.19 | 91.06 | 6.46 |
| v1_refusal_all_items | 81.25 | 86.02 | 76.77 | 81.25 | 9.25 |
| v1_refusal_representable | 100.00 | 100.00 | 100.00 | 100.00 | 0.00 |
| v2_refusal | 100.00 | 100.00 | 100.00 | 100.00 | 0.00 |
| v4_refusal | 20.91 | 15.25 | 26.06 | 20.56 | 10.80 |
| v5_refusal_all_items | 3.50 | 0.00 | 4.64 | 4.38 | 4.64 |
| v6_refusal_all_items | 19.50 | 17.78 | 20.00 | 20.00 | 2.22 |
| v6_refusal_representable | 22.29 | 20.25 | 22.90 | 22.86 | 2.65 |
| violations_all | 51.92 | 50.60 | 52.71 | 52.02 | 2.11 |
| benign_block_feas | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| benign_block_qual | 2.62 | 0.00 | 3.84 | 3.25 | 3.84 |
| stage_block_schema | 8.25 | 9.69 | 7.31 | 8.18 | 2.38 |
| stage_block_feas | 10.00 | 8.98 | 10.82 | 9.91 | 1.84 |
| stage_reached_qual | 81.75 | 81.33 | 81.86 | 81.91 | 0.58 |
| stage_block_qual | 13.95 | 11.20 | 15.41 | 14.37 | 4.21 |
| all_refusal | 32.20 | 29.87 | 33.55 | 32.47 | 3.68 |

## Leave one subclass out

33 folds, of which only the ones carrying items of a given metric can move it; the rest are identity folds and are counted rather than printed.

| metric | full | effective folds | identity folds | min (subclass) | max (subclass) | range (pp) |
| --- | --- | --- | --- | --- | --- | --- |
| benign_refusal | 2.62 | 23 | 10 | 2.50 (frozen_order_edit) | 2.84 (dangling_order_id) | 0.34 |
| v3_refusal | 91.36 | 5 | 28 | 89.14 (window_blocked_predecessor) | 93.71 (reorder_cross_trade) | 4.57 |
| v1_refusal_all_items | 81.25 | 6 | 27 | 70.00 (dangling_order_id) | 92.86 (unknown_op) | 22.86 |
| v1_refusal_representable | 100.00 | 4 | 29 | 100.00 (dangling_building_id) | 100.00 (unstaffed_trade) | 0.00 |
| v2_refusal | 100.00 | 5 | 28 | 100.00 (freeze_shift_contradiction) | 100.00 (trade_mismatch) | 0.00 |
| v4_refusal | 20.91 | 7 | 26 | 2.35 (reorder_direction_flipped) | 24.44 (sign_flipped_shift) | 22.09 |
| v5_refusal_all_items | 3.50 | 5 | 28 | 3.12 (conflicting_directives) | 3.89 (open_ended_overreach) | 0.76 |
| v6_refusal_all_items | 19.50 | 5 | 28 | 2.42 (payload_smuggling) | 26.90 (instruction_override) | 24.47 |
| v6_refusal_representable | 22.29 | 4 | 29 | 2.86 (payload_smuggling) | 32.50 (instruction_override) | 29.64 |
| violations_all | 51.92 | 33 | 0 | 49.39 (dangling_order_id) | 54.47 (ambiguous_referent) | 5.09 |
| benign_block_feas | 0.00 | 23 | 10 | 0.00 (dangling_building_id) | 0.00 (wrong_order_same_building) | 0.00 |
| benign_block_qual | 2.62 | 23 | 10 | 2.50 (frozen_order_edit) | 2.84 (dangling_order_id) | 0.34 |
| stage_block_schema | 8.25 | 33 | 0 | 5.59 (dangling_order_id) | 8.87 (reorder_block_tight) | 3.29 |
| stage_block_feas | 10.00 | 33 | 0 | 7.45 (reorder_cycle) | 10.75 (reorder_block_tight) | 3.31 |
| stage_reached_qual | 81.75 | 33 | 0 | 80.38 (reorder_block_tight) | 83.78 (reorder_cycle) | 3.40 |
| stage_block_qual | 13.95 | 33 | 0 | 11.61 (reorder_block_tight) | 14.84 (dangling_order_id) | 3.23 |
| all_refusal | 32.20 | 33 | 0 | 30.96 (reorder_cycle) | 33.33 (sign_flipped_shift) | 2.38 |

`v1_refusal_all_items`, `v4_refusal`, `v6_refusal_all_items`, `v6_refusal_representable` span more than 10 percentage points across subclass folds, and the reason is the suite's design rather than the guard's stability: each of those classes has its refusals concentrated in one designed subclass, so removing that subclass removes most of the numerator. Dropping `dangling_order_id` takes `v1_refusal_all_items` from 81.25 to 70.00; dropping `reorder_direction_flipped` takes `v4_refusal` from 20.91 to 2.35; dropping `payload_smuggling` takes `v6_refusal_all_items` from 19.50 to 2.42; dropping `payload_smuggling` takes `v6_refusal_representable` from 22.29 to 2.86. A subclass is a construction of the suite generator, not a sample, which is why this family is reported as a description of the design and carries no standard error.

## Where the movement sits, and what it agrees with

All 21 benign false blocks of the deployed guard sit on 2 of the 60 instances, `c09_storm2_w80_u100_0008` and `c09_storm2_w80_u100_0018`. Those are exactly the two instances `delta_baselines.FOCUS_INSTANCES` names, the two whose own no-op schedule certifies above the deployed tolerance, and deleting either is the only way to lower the false-block rate at all: every other instance raises it. The leave-one-instance-out minimum, 1.27, is attained on `c09_storm2_w80_u100_0008`.

This agrees with what the repository already reports rather than adding to it. In `analysis/DG5_falseblock_concentration.csv`, all 8 capability-set arms read at `G_CERT` name that same pair as their two most false-blocked instances. The jackknife recovers the concentration; it does not find it.

The same concentration is what makes the leave-one-stratum-out row for the false-block rate read as it does: the whole of the guard's false-block cost lies in `c09_storm2_w80`, so removing that stratum sends the rate to 0.00 while removing either of the other two raises it.

## The reading, for the manuscript

> Deleting any one of the 60 instances leaves the V3 refusal rate between 91.0% and 92.2% and the benign false-block rate between 1.3% and 2.7%, against full-sample values of 91.4% and 2.6%, and the leave-one-instance-out jackknife standard errors of 2.47 and 1.85 percentage points agree with the cluster-bootstrap standard errors reported for the same two rates. Only the two instances whose own no-op schedule already certifies above the deployed tolerance lower the false-block rate when they are removed, so that rate measures the cost of two schedules rather than a property of the benchmark as a whole.

## Provenance and self-check

| input | sha256 |
| --- | --- |
| `analysis/DG1_direct_guard.csv` | 32d8e190b4b0ecb725f2ae3ddcf506dec062e736fb6b0d725a273a3f35293a4f |
| `analysis/DG1_direct_guard_summary.csv` | e48e336e549d1a02342750d56648fe37f42c6390d3acfb6039bb26f89f9a91bb |
| `analysis/DG10_direct_guard_intervals.csv` | 7bc9d93d36b00488535df70f443b16c93336632b654227318fb7ac161962b7de |
| `analysis/DG5_falseblock_concentration.csv` | 179c477c8f987bb0d431e8d946318c7afd4ae4980718d662d7f72d2bb2d47103 |

`manuscript/macros.tex` is read for the published literals only and is never written.

261 assertions pass, covering the population against `analysis/DG1_direct_guard_summary.csv`, every full-sample rate and count against the macros the manuscript prints, every numerator and denominator against `analysis/DG10_direct_guard_intervals.csv`, the jackknife standard error against both published cluster standard errors, the partition property of each fold family, envelope containment of the full-sample value, and the influential-instance agreement above. The script exits non-zero on any failure and writes nothing.
