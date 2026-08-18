<!-- generated 2026-08-17 17:32:17 +0800 by analysis/DG9_stratum_split.py (l1-dg9-stratum-1) -->

# DG9. The E1 headline rates, split by stratum

The 2,000 suite instructions replay on 60 frozen instances in three strata. Two of the three are constructed high-load scenarios drawn from a fitted Poisson model of the campus, and one is a recorded window of the corpus. Every rate below is the published pooled rate restricted to one stratum's rows; the three strata sum exactly to the pooled numerator and denominator on every cell and metric, which the script asserts before writing.

Constrained mode, repeats pooled, cells are (arm, thinking) over the seven schema-enforced arms. Intervals are instance-clustered bootstraps with 24, 12 and 24 clusters, so they are wide; read them as an order of magnitude for the uncertainty, not as a test.

Pass-through is read two ways, as in `analysis/DG7_passthrough.csv`. The total reading counts any applied terminal; the non-empty reading adds `n_ops > 0` to the numerator, so a violation applied as a no-op does not count as having passed through. The denominator is the same in both. The `_strict` rows apply the V4/V6 content rule (`code/scripts/passthrough_rule.py`) to the total reading: an applied V4 or V6 row counts unless its operations are exactly the item's non-empty `gold_ops`.

## V3 separation (G-FEAS applies, G-CERT blocks)

| arm / thinking | C9 storm2 (24 inst.) | C10 storm2 (12 inst.) | C10 replay 400 (24 inst.) | all three pooled |
|---|---|---|---|---|
| qwen3-14b / - | 89.5% (306/342) [81.9 to 95.7] | 85.4% (105/123) [69.7 to 97.4] | 67.7% (132/195) [52.5 to 78.3] | 82.3% (543/660) [75.9 to 87.9] |
| qwen3.6-27b-fp8 / - | 91.2% (312/342) [84.0 to 96.9] | 85.4% (105/123) [75.0 to 95.0] | 80.5% (157/195) [64.3 to 92.0] | 87.0% (574/660) [81.0 to 92.1] |
| glm-4-9b / - | 79.8% (91/114) [71.3 to 87.5] | 70.7% (29/41) [58.5 to 82.9] | 61.5% (40/65) [46.8 to 72.3] | 72.7% (160/220) [66.3 to 78.6] |
| openai / - | 86.4% (197/228) [78.7 to 93.1] | 79.3% (65/82) [63.3 to 93.6] | 65.4% (85/130) [50.9 to 76.0] | 78.9% (347/440) [72.3 to 84.7] |
| sonnet / disabled | 87.7% (200/228) [79.7 to 94.4] | 87.8% (72/82) [76.2 to 97.6] | 81.5% (106/130) [64.7 to 93.4] | 85.9% (378/440) [79.6 to 91.5] |
| opus / default | 93.0% (212/228) [87.0 to 97.6] | 92.7% (76/82) [81.8 to 100.0] | 84.6% (110/130) [70.0 to 94.9] | 90.5% (398/440) [85.2 to 94.8] |
| opus / disabled | 92.5% (211/228) [86.7 to 97.3] | 91.5% (75/82) [77.9 to 100.0] | 84.6% (110/130) [70.2 to 95.1] | 90.0% (396/440) [84.6 to 94.5] |
| sol / none | 92.1% (105/114) [84.8 to 97.5] | 90.2% (37/41) [79.1 to 100.0] | 60.0% (39/65) [41.7 to 73.2] | 82.3% (181/220) [75.3 to 88.3] |

## Benign false block under G-CERT

| arm / thinking | C9 storm2 (24 inst.) | C10 storm2 (12 inst.) | C10 replay 400 (24 inst.) | all three pooled |
|---|---|---|---|---|
| qwen3-14b / - | 7.5% (89/1182) [1.3 to 16.5] | 2.8% (13/459) [0.5 to 5.7] | 0.4% (3/759) [0.0 to 1.2] | 4.4% (105/2400) [1.2 to 8.7] |
| qwen3.6-27b-fp8 / - | 9.1% (107/1182) [3.4 to 17.2] | 3.5% (16/459) [1.4 to 5.5] | 1.2% (9/759) [0.0 to 2.4] | 5.5% (132/2400) [2.5 to 9.7] |
| glm-4-9b / - | 10.7% (42/394) [4.5 to 19.6] | 7.8% (12/153) [4.9 to 11.1] | 4.0% (10/253) [2.0 to 5.9] | 8.0% (64/800) [4.8 to 12.3] |
| openai / - | 7.1% (56/788) [1.4 to 15.7] | 1.0% (3/306) [0.0 to 2.5] | 0.6% (3/506) [0.0 to 1.3] | 3.9% (62/1600) [1.0 to 8.0] |
| sonnet / disabled | 6.9% (54/788) [1.1 to 15.6] | 1.0% (3/306) [0.0 to 1.9] | 0.8% (4/506) [0.0 to 1.9] | 3.8% (61/1600) [0.9 to 7.9] |
| opus / default | 6.9% (54/788) [1.1 to 15.5] | 1.3% (4/306) [0.0 to 2.7] | 1.0% (5/506) [0.0 to 2.1] | 3.9% (63/1600) [1.0 to 8.1] |
| opus / disabled | 8.0% (63/788) [2.2 to 16.7] | 2.9% (9/306) [1.0 to 4.9] | 1.6% (8/506) [0.4 to 2.8] | 5.0% (80/1600) [2.0 to 9.1] |
| sol / none | 8.9% (35/394) [3.2 to 17.3] | 3.3% (5/153) [1.3 to 5.4] | 11.5% (29/253) [7.1 to 15.9] | 8.6% (69/800) [5.3 to 13.0] |

## Violation pass-through under G-CERT (total reading)

| arm / thinking | C9 storm2 (24 inst.) | C10 storm2 (12 inst.) | C10 replay 400 (24 inst.) | all three pooled |
|---|---|---|---|---|
| qwen3-14b / - | 56.9% (1050/1845) [50.9 to 61.8] | 63.2% (442/699) [59.9 to 66.7] | 65.9% (696/1056) [62.2 to 69.7] | 60.8% (2188/3600) [57.4 to 63.7] |
| qwen3.6-27b-fp8 / - | 59.2% (1093/1845) [53.0 to 63.9] | 66.5% (465/699) [63.0 to 70.0] | 65.1% (687/1056) [62.2 to 68.0] | 62.4% (2245/3600) [59.0 to 65.1] |
| glm-4-9b / - | 53.7% (330/615) [47.9 to 58.6] | 59.7% (139/233) [55.0 to 64.1] | 63.1% (222/352) [59.3 to 66.7] | 57.6% (691/1200) [54.2 to 60.7] |
| openai / - | 57.9% (712/1230) [51.8 to 62.5] | 62.0% (289/466) [58.3 to 65.5] | 65.2% (459/704) [61.4 to 69.0] | 60.8% (1460/2400) [57.5 to 63.7] |
| sonnet / disabled | 65.9% (810/1230) [59.0 to 70.9] | 70.8% (330/466) [66.6 to 75.1] | 70.5% (496/704) [66.9 to 74.0] | 68.2% (1636/2400) [64.5 to 71.2] |
| opus / default | 74.4% (915/1230) [66.7 to 79.9] | 80.5% (375/466) [76.6 to 84.5] | 80.1% (564/704) [75.4 to 84.8] | 77.2% (1854/2400) [73.1 to 80.6] |
| opus / disabled | 69.4% (854/1230) [62.2 to 74.6] | 74.7% (348/466) [71.0 to 78.6] | 74.7% (526/704) [70.7 to 78.9] | 72.0% (1728/2400) [68.2 to 75.1] |
| sol / none | 70.9% (436/615) [63.5 to 76.4] | 76.4% (178/233) [72.6 to 80.4] | 73.9% (260/352) [68.4 to 79.6] | 72.8% (874/1200) [68.8 to 76.3] |

## Violation pass-through under G-CERT (non-empty reading)

| arm / thinking | C9 storm2 (24 inst.) | C10 storm2 (12 inst.) | C10 replay 400 (24 inst.) | all three pooled |
|---|---|---|---|---|
| qwen3-14b / - | 46.2% (853/1845) [41.3 to 50.4] | 51.2% (358/699) [46.5 to 55.7] | 55.8% (589/1056) [51.5 to 59.8] | 50.0% (1800/3600) [47.0 to 52.9] |
| qwen3.6-27b-fp8 / - | 42.3% (781/1845) [37.8 to 46.4] | 44.3% (310/699) [40.6 to 48.1] | 52.1% (550/1056) [48.3 to 56.1] | 45.6% (1641/3600) [42.8 to 48.4] |
| glm-4-9b / - | 51.5% (317/615) [46.3 to 56.0] | 56.7% (132/233) [52.1 to 60.6] | 61.4% (216/352) [57.8 to 64.8] | 55.4% (665/1200) [52.2 to 58.3] |
| openai / - | 51.1% (628/1230) [45.6 to 55.4] | 57.5% (268/466) [53.0 to 62.1] | 60.7% (427/704) [56.3 to 64.9] | 55.1% (1323/2400) [51.9 to 58.2] |
| sonnet / disabled | 39.3% (483/1230) [35.2 to 43.0] | 41.0% (191/466) [36.0 to 46.4] | 50.3% (354/704) [46.4 to 54.0] | 42.8% (1028/2400) [40.0 to 45.6] |
| opus / default | 37.3% (459/1230) [33.6 to 40.5] | 40.1% (187/466) [35.7 to 44.1] | 41.3% (291/704) [38.1 to 44.3] | 39.0% (937/2400) [36.8 to 41.2] |
| opus / disabled | 36.1% (444/1230) [32.6 to 39.2] | 39.5% (184/466) [35.5 to 43.8] | 42.2% (297/704) [38.3 to 46.2] | 38.5% (925/2400) [36.1 to 40.8] |
| sol / none | 37.1% (228/615) [33.0 to 40.8] | 37.8% (88/233) [32.7 to 43.0] | 46.3% (163/352) [42.2 to 50.6] | 39.9% (479/1200) [37.2 to 42.7] |

## The supporting rates

| metric | arm / thinking | C9 storm2 | C10 storm2 | C10 replay 400 | pooled |
|---|---|---|---|---|---|
| v3_block_gfeas | qwen3-14b / - | 0.9% (3/342) | 0.0% (0/123) | 0.0% (0/195) | 0.5% (3/660) |
| v3_block_gfeas | qwen3.6-27b-fp8 / - | 0.9% (3/342) | 0.0% (0/123) | 0.0% (0/195) | 0.5% (3/660) |
| v3_block_gfeas | glm-4-9b / - | 3.5% (4/114) | 2.4% (1/41) | 1.5% (1/65) | 2.7% (6/220) |
| v3_block_gfeas | openai / - | 0.9% (2/228) | 0.0% (0/82) | 0.0% (0/130) | 0.5% (2/440) |
| v3_block_gfeas | sonnet / disabled | 0.9% (2/228) | 0.0% (0/82) | 0.0% (0/130) | 0.5% (2/440) |
| v3_block_gfeas | opus / default | 0.0% (0/228) | 0.0% (0/82) | 0.0% (0/130) | 0.0% (0/440) |
| v3_block_gfeas | opus / disabled | 0.0% (0/228) | 0.0% (0/82) | 0.0% (0/130) | 0.0% (0/440) |
| v3_block_gfeas | sol / none | 0.0% (0/114) | 0.0% (0/41) | 20.0% (13/65) | 5.9% (13/220) |
| benign_false_block_gfeas | qwen3-14b / - | 0.5% (6/1182) | 0.0% (0/459) | 0.0% (0/759) | 0.2% (6/2400) |
| benign_false_block_gfeas | qwen3.6-27b-fp8 / - | 3.7% (44/1182) | 3.5% (16/459) | 1.2% (9/759) | 2.9% (69/2400) |
| benign_false_block_gfeas | glm-4-9b / - | 5.6% (22/394) | 7.2% (11/153) | 4.0% (10/253) | 5.4% (43/800) |
| benign_false_block_gfeas | openai / - | 1.8% (14/788) | 1.0% (3/306) | 0.6% (3/506) | 1.2% (20/1600) |
| benign_false_block_gfeas | sonnet / disabled | 1.5% (12/788) | 1.0% (3/306) | 0.8% (4/506) | 1.2% (19/1600) |
| benign_false_block_gfeas | opus / default | 1.5% (12/788) | 1.3% (4/306) | 1.0% (5/506) | 1.3% (21/1600) |
| benign_false_block_gfeas | opus / disabled | 2.7% (21/788) | 2.9% (9/306) | 1.6% (8/506) | 2.4% (38/1600) |
| benign_false_block_gfeas | sol / none | 3.6% (14/394) | 3.3% (5/153) | 11.5% (29/253) | 6.0% (48/800) |
| violation_pass_through_gcert_strict | qwen3-14b / - | 44.8% (827/1845) | 50.4% (352/699) | 54.0% (570/1056) | 48.6% (1749/3600) |
| violation_pass_through_gcert_strict | qwen3.6-27b-fp8 / - | 45.0% (830/1845) | 50.8% (355/699) | 44.8% (473/1056) | 46.1% (1658/3600) |
| violation_pass_through_gcert_strict | glm-4-9b / - | 45.2% (278/615) | 49.4% (115/233) | 52.0% (183/352) | 48.0% (576/1200) |
| violation_pass_through_gcert_strict | openai / - | 44.2% (544/1230) | 46.1% (215/466) | 48.3% (340/704) | 45.8% (1099/2400) |
| violation_pass_through_gcert_strict | sonnet / disabled | 47.6% (585/1230) | 51.1% (238/466) | 48.2% (339/704) | 48.4% (1162/2400) |
| violation_pass_through_gcert_strict | opus / default | 55.2% (679/1230) | 59.4% (277/466) | 57.5% (405/704) | 56.7% (1361/2400) |
| violation_pass_through_gcert_strict | opus / disabled | 50.3% (619/1230) | 53.6% (250/466) | 54.5% (384/704) | 52.2% (1253/2400) |
| violation_pass_through_gcert_strict | sol / none | 52.2% (321/615) | 56.2% (131/233) | 53.4% (188/352) | 53.3% (640/1200) |
| violation_pass_through_gfeas | qwen3-14b / - | 79.0% (1458/1845) | 80.0% (559/699) | 78.7% (831/1056) | 79.1% (2848/3600) |
| violation_pass_through_gfeas | qwen3.6-27b-fp8 / - | 79.9% (1474/1845) | 81.5% (570/699) | 79.9% (844/1056) | 80.2% (2888/3600) |
| violation_pass_through_gfeas | glm-4-9b / - | 72.8% (448/615) | 72.1% (168/233) | 74.4% (262/352) | 73.2% (878/1200) |
| violation_pass_through_gfeas | openai / - | 77.8% (957/1230) | 76.2% (355/466) | 77.3% (544/704) | 77.3% (1856/2400) |
| violation_pass_through_gfeas | sonnet / disabled | 85.9% (1057/1230) | 86.3% (402/466) | 85.5% (602/704) | 85.9% (2061/2400) |
| violation_pass_through_gfeas | opus / default | 95.9% (1180/1230) | 96.8% (451/466) | 95.7% (674/704) | 96.0% (2305/2400) |
| violation_pass_through_gfeas | opus / disabled | 90.8% (1117/1230) | 90.8% (423/466) | 90.3% (636/704) | 90.7% (2176/2400) |
| violation_pass_through_gfeas | sol / none | 92.0% (566/615) | 92.3% (215/233) | 85.8% (302/352) | 90.2% (1083/1200) |
| violation_pass_through_gfeas_nonempty | qwen3-14b / - | 67.0% (1237/1845) | 68.0% (475/699) | 68.6% (724/1056) | 67.7% (2436/3600) |
| violation_pass_through_gfeas_nonempty | qwen3.6-27b-fp8 / - | 61.7% (1138/1845) | 59.4% (415/699) | 67.0% (707/1056) | 62.8% (2260/3600) |
| violation_pass_through_gfeas_nonempty | glm-4-9b / - | 70.4% (433/615) | 69.1% (161/233) | 72.7% (256/352) | 70.8% (850/1200) |
| violation_pass_through_gfeas_nonempty | openai / - | 70.5% (867/1230) | 71.7% (334/466) | 72.7% (512/704) | 71.4% (1713/2400) |
| violation_pass_through_gfeas_nonempty | sonnet / disabled | 57.7% (710/1230) | 56.4% (263/466) | 65.3% (460/704) | 59.7% (1433/2400) |
| violation_pass_through_gfeas_nonempty | opus / default | 56.6% (696/1230) | 56.4% (263/466) | 57.0% (401/704) | 56.7% (1360/2400) |
| violation_pass_through_gfeas_nonempty | opus / disabled | 55.7% (685/1230) | 55.6% (259/466) | 57.8% (407/704) | 56.3% (1351/2400) |
| violation_pass_through_gfeas_nonempty | sol / none | 56.4% (347/615) | 53.6% (125/233) | 58.2% (205/352) | 56.4% (677/1200) |
| violation_pass_through_gfeas_strict | qwen3-14b / - | 66.4% (1226/1845) | 67.1% (469/699) | 66.8% (705/1056) | 66.7% (2400/3600) |
| violation_pass_through_gfeas_strict | qwen3.6-27b-fp8 / - | 64.8% (1196/1845) | 65.8% (460/699) | 59.7% (630/1056) | 63.5% (2286/3600) |
| violation_pass_through_gfeas_strict | glm-4-9b / - | 63.6% (391/615) | 61.8% (144/233) | 63.4% (223/352) | 63.2% (758/1200) |
| violation_pass_through_gfeas_strict | openai / - | 63.2% (777/1230) | 60.3% (281/466) | 60.4% (425/704) | 61.8% (1483/2400) |
| violation_pass_through_gfeas_strict | sonnet / disabled | 66.5% (818/1230) | 66.5% (310/466) | 63.2% (445/704) | 65.5% (1573/2400) |
| violation_pass_through_gfeas_strict | opus / default | 75.4% (928/1230) | 75.8% (353/466) | 73.2% (515/704) | 74.8% (1796/2400) |
| violation_pass_through_gfeas_strict | opus / disabled | 70.4% (866/1230) | 69.7% (325/466) | 70.2% (494/704) | 70.2% (1685/2400) |
| violation_pass_through_gfeas_strict | sol / none | 72.2% (444/615) | 72.1% (168/233) | 65.3% (230/352) | 70.2% (842/1200) |

## The no-AI (RULE) anchor level per stratum

The RULE anchor is the zero-operation proposal: the instruction is not applied at all, so the schedule is the baseline dispatch. There is one anchor per (instance, standing frozen set). The plain mean weights each anchor once; the item-weighted mean weights each anchor by how many suite items run on it, which is the weighting the ladder's rung-1 number carries.

| stratum | instances | anchors | suite items | mean (bh) | median (bh) | min (bh) | max (bh) | item-weighted mean (bh) |
|---|---|---|---|---|---|---|---|---|
| c09_storm2_w80 | 24 | 48 | 1009 | 717.97 | 645.36 | 196.46 | 1566.93 | 719.37 |
| c10_storm2_w80 | 12 | 24 | 386 | 1533.04 | 1366.60 | 548.29 | 2859.51 | 1515.75 |
| c10_replay_400 | 24 | 44 | 605 | 119.14 | 68.00 | 0.00 | 854.92 | 120.99 |
| ALL | 60 | 116 | 2000 | 659.46 | 527.98 | 0.00 | 2859.51 | 692.06 |

## What the three strata are

Read from the instance files themselves. `provenance` is the corpus's own flag: `R` is a recorded replay window built by `fmwos.instances.build_instance` (the first N work orders released after a weekday-08:00 anchor, with the corpus's real order identifiers, buildings and timestamps); `C` is constructed by `fmwos.generator.generate_window`, a homogeneous Poisson superposition per trade drawn over a fixed 80-business-hour window from the campus's fitted parameter pack, with `window_start` literally set to `synthetic`. The `w80` in a storm2 filename is that 80-bh window; the `u100` is the generator's target utilisation of 1.00, reached by scaling the fitted arrival rates by `u_target / u0`.

| stratum | provenance | declared u_target | work orders (min/median/max) | technicians | window bh (median) | offered load ratio (min/median/max) | bottleneck-trade ratio (median) | median queue depth over the makespan (min/median/max) |
|---|---|---|---|---|---|---|---|---|
| c09_storm2_w80 | C | 1.00 | 2135 / 2268.0 / 2353 | 99 | 80.00 | 0.918 / 1.001 / 1.081 | 1.338 | 19.0 / 65.0 / 145.0 |
| c10_storm2_w80 | C | 1.00 | 9160 / 9357.5 / 9509 | 154 | 80.00 | 0.954 / 0.988 / 1.053 | 1.403 | 98.0 / 193.5 / 433.0 |
| c10_replay_400 | R | none (recorded) | 400 / 400.0 / 400 | 154 | 8.93 | 0.023 / 0.552 / 4.150 | 1.192 | 0.0 / 0.0 / 0.0 |

The offered-load ratio is `sum(p_bh) / (technicians * window_bh)`, the corpus's own utilisation definition evaluated on the realised file rather than on the fitted parameter pack. It aggregates over trades, so the bottleneck-trade column is given next to it. The median queue depth is the time-weighted median of the number of released but not-yet-started orders under the baseline ATC dispatch.

The queue figure has to be read twice, because the two constructed strata and the recorded one have different shapes. A storm2 instance releases work at a constant rate for 80 business hours against a crew sized to that rate, so the queue is deep for essentially the whole horizon. A replay instance releases its 400 recorded orders over a short window (median 8.9 bh) and then runs a long tail of large jobs with an empty queue, so a median over the whole makespan reports the tail rather than the congestion. The second table takes the same measure over the arrival window only.

| stratum | median queue depth over the arrival window (median over instances) | mean queue depth over the arrival window (median) | peak queue depth (median) | share of orders that waited at all (median) | median wait, bh (median) |
|---|---|---|---|---|---|
| c09_storm2_w80 | 102.0 | 114.3 | 268 | 0.775 | 0.46 |
| c10_storm2_w80 | 540.0 | 637.9 | 1531 | 0.873 | 1.00 |
| c10_replay_400 | 0.0 | 6.4 | 148 | 0.487 | 0.00 |

The suite's own congestion label agrees. `queue_state` (`l1suite.facts.Facts.queue_state`) is the target trade's orders per technician over the whole window: deep at 20 or more, moderate at 5 or more, shallow below 5.

| stratum | deep | moderate | shallow | not applicable |
|---|---|---|---|---|
| c09_storm2_w80 | 555 | 424 | 13 | 17 |
| c10_storm2_w80 | 201 | 179 | 0 | 6 |
| c10_replay_400 | 0 | 214 | 384 | 7 |

## Sources

- `code/suite/v0.2/suite.jsonl` sha256 `0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a`
- `results/e1_eval_qwen14b/verdicts_G_CERT.jsonl` sha256 `007f9b7e128b9b40a1c8a6f20e1d7bf0688e7597c9ccf802b3d4603e11d5ff82`
- `results/e1_eval_qwen14b/verdicts_G_FEAS.jsonl` sha256 `2e35dedecb9363433618b26c6f0d75f596ce88b931e35443661048d2a8823e23`
- `results/e1_eval_qwen14b/proposals.jsonl` sha256 `1275be52a6a9e7cc36ebcc8c6f193b81a6c84e97671932fdf534e2b7a1c9dd47`
- `results/e1_eval_qwen27b/verdicts_G_CERT.jsonl` sha256 `34f6a4c8b2b26b38a69a21c1a22d0d0ee7715b2d15a095399aa505c279377d10`
- `results/e1_eval_qwen27b/verdicts_G_FEAS.jsonl` sha256 `5741e6c174e36e8d04a366fd648a051ccb6bf6a4ecfa182382cf43ba3f5b1d75`
- `results/e1_eval_qwen27b/proposals.jsonl` sha256 `7d930c7633af776c55abe93c72a33e6132cd9eccdc22d0543ade32f1ec63811d`
- `results/e1_eval_glm9b/verdicts_G_CERT.jsonl` sha256 `357ff6582097bd5c6656c14e6c47a6c85b5cb2c699e2206d1f8722ff1f0e6ed4`
- `results/e1_eval_glm9b/verdicts_G_FEAS.jsonl` sha256 `c6aa59cb041ee235084646d185760383d6d81d979876146af42f136a3694633c`
- `results/e1_eval_glm9b/proposals.jsonl` sha256 `94f9457a32e8776c6f403f4f619b2c96ce1d96bc3c2d1cb8118c1a2808c260bb`
- `results/e1_eval_gpt54mini/verdicts_G_CERT.jsonl` sha256 `ab58fe9be34e97572208247ee13fbf9710af6b14f5b0004390faeb4031f1a78d`
- `results/e1_eval_gpt54mini/verdicts_G_FEAS.jsonl` sha256 `0b54b9a910824885ff330ca5afab191320b01091f6e140d1edeacb395aed092c`
- `results/e1_eval_gpt54mini/proposals.jsonl` sha256 `cbfcbd608fa2b03fa878089bda35dc2e8491307e7ab5c7bea0f6576e28b9a9cd`
- `results/e1_eval_sonnet5/verdicts_G_CERT.jsonl` sha256 `87d3ebaefefe7b70915a861cc2f61dd3fb5e7e08df5f83756cf78ce5aa8f102c`
- `results/e1_eval_sonnet5/verdicts_G_FEAS.jsonl` sha256 `4b25bfa946e1f6a8e56f627b84148f858ce6b2e0dd0e2716fb18d3bbbd257d7c`
- `results/e1_eval_sonnet5/proposals.jsonl` sha256 `0a1387c342b1b9d551ab114ae13c9bf87871c27f7476fd96eecc5e5a1df3f94c`
- `results/e1_eval_opus5/verdicts_G_CERT.jsonl` sha256 `2c4a3d99410ce0bc38a8c230ffa3770f8f1fc20d514c732abf4d53d898f77744`
- `results/e1_eval_opus5/verdicts_G_FEAS.jsonl` sha256 `2e3f20d17f1a24f3e167bd443ae1f05f0bf7e9133777f70ada5dccf237124597`
- `results/e1_eval_opus5/proposals.jsonl` sha256 `170c6b315c419a23e6f4663ed28849e39b2672d4c08aa529d242e31cfd24d95d`
- `results/e1_eval_sol/verdicts_G_CERT.jsonl` sha256 `3a06dbde336b05951afd45cf08f609612a095c7a0d1861f68c447e6c7ab16dab`
- `results/e1_eval_sol/verdicts_G_FEAS.jsonl` sha256 `e2436e281abdbd80e0702d221a839dc3f2c23b973d64fc2c507ca08c9a58762c`
- `results/e1_eval_sol/proposals.jsonl` sha256 `d1717574dc9365777d11455354cc58be02ed4790f792491442adf80f68344195`
- `analysis/T3_guard_value_curve.csv` sha256 `e9bf87e3856515e779897f6af7306a96ea02ea2f5b06eabf1e86f398a91f6911`
- `analysis/T1_e1_main.csv` sha256 `8439dadb9dc81c401eecda7f661f459f54698ab146a7e02408043779dec69b5c`
- `analysis/DG7_passthrough.csv` sha256 `0439d247809b65b818d708912dc6c5ac67b4ba4dde999a21aa61975755606708`
- `analysis/ladder/rule_anchor.json` sha256 `d36b620d9ccd2240bd9e3c32ec1275bdca8ce2391db033d045664d3dcfbc0710`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0000.json` sha256 `683cdb22b8903265bb9f594d1b10dbe8e37b94a9f73a723dd0f217c103da65c3`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0001.json` sha256 `f09856bc8d8a153820866dbd28543653ed963274a8a34a432511f1e83bc40968`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0002.json` sha256 `20b942049e53ef0791a0d7e2c32028d3bcb423812680bbfd6a4f705e33f6e548`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0003.json` sha256 `f3ace9e56e2bbd7d35b18991d2b7e511db9bf7d3148f7c90a5c9293747cac499`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0004.json` sha256 `e7bceaee3533e157855ffc411e427311decbd9e1e2b4ff40cf577fd5ed5767c1`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0005.json` sha256 `b134265cbc1e15053641697e9f923a292cc3bcca8606864e86313a6d0e2a1c72`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0006.json` sha256 `eb84cae9e7f53d0fb99e2b51746f34f30b7fe8f39132b93e6205e321aca61d41`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0007.json` sha256 `4561db94b0a39f52e63516b0b84a0674e0c7a1058f7a19f47587f98df38c16d4`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0008.json` sha256 `dbc455ff695736d8c79bc1acb6771dc418f26a623fa03d37143221b1d9f2243b`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0009.json` sha256 `256437b89826c52313af5676a2fa9552a1d9c77e0eeb6d9177fbd5c10a4e48f2`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0010.json` sha256 `752dfab9aa4443552188cc35693678766c8b4c3a890d0be74cdf21c5b0cf4199`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0011.json` sha256 `00b0d868199ff9a3f8f820c6e1f6ffd40d2a34a99dab5b3c4d1c9831367a6bf3`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0012.json` sha256 `a904d68373b6ab46e273770cf4cfbab8ce42f2b627f3edc970feea72cdb6f3fb`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0013.json` sha256 `bda79b8d4969d7061cef902b05cb8716a2ba392b1777c9ca696ec72d24a1ac8b`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0014.json` sha256 `5716c1aa2b462c36e85438cfb766908b7f1af2577c09e112171f344c5a1d833c`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0015.json` sha256 `e3ab52a8bce2967b9a2a2364c6e322a8b58c6f9d5cc6324675daf5ba87e39768`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0016.json` sha256 `7000dfae012b34270dce778d5619e55a76ffe6ed3f9e7cef43f0401003242957`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0017.json` sha256 `a706977687158fb9081bbd041256ad45748d635ad27a81b37bee4a267951da9a`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0018.json` sha256 `32d0361ad6d43b6e8921377d6084925e22315e7b0a7dba6db3e2378c2eee0a5a`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0019.json` sha256 `4efaeb9dba812f7023fecac7984c4626649c2116c99569ee9d29a213aa0ef37a`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0020.json` sha256 `06a8f16508e9e9c03c653d3cc7cd4e3aaf02c64cdf52a3f88cb85b92088e3223`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0021.json` sha256 `c3467526629726eac0654365d5f277f86b83073625b7d23865ff146340443b5f`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0022.json` sha256 `f75da099d21fd3f8bee303fbdbdec377edfa6f38a5a735ca697b1c1af3dd36c4`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c09/storm2/w80/c09_storm2_w80_u100_0023.json` sha256 `6493954905142e678bbc3c30bc6f062970bd5840028afd7da90daf53dadf2960`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0000.json` sha256 `5e1faaaf97577fe0697f9cffd73ea7b840906fae4097712bb47813aae863d5fd`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0001.json` sha256 `64b74dd856a64b9ba0255f91502923cad674170d30f49e76cad9b3a1c5daa259`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0002.json` sha256 `e1d8ae8110b8040b7b2de364217895bcb4ee840d962ba69cdc393ce5470e2e07`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0003.json` sha256 `cbcd5c8e2c9152856b1959ac6a808dfe6ddc9593163c7a482c303954ce8a72a1`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0004.json` sha256 `090800c87a31c360003010f9a5d9fe27c3a97b4c9275abf09431d602738af773`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0005.json` sha256 `0a29ad0b9b27927a1e17e183dde07ed905ed6c743e7d3522899b395b08f6594b`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0006.json` sha256 `34c570f573fab35f3adfb094c89e4e49c8ee98fd4208440912f5c96cbe77462e`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0007.json` sha256 `935378e0b3784789da3baf4c7b60396f78a24ab632456b4dedd18760bfe10c40`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0008.json` sha256 `f574cc623400e431195196bb828056bf9b5ee40d07e32fa868406183877a38ff`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0009.json` sha256 `6faa8ef0d0ad63c498f589543462b23bd641d43db295f086be2782c5a110c3f0`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0010.json` sha256 `3665c089e29d8ff2041f22fd3f7efff2451bd8f15d143e5dbfede1e9d0560203`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0011.json` sha256 `17b53254506ff6755477d6946b7b3b4545bdb89ebec7f3cdea3f171fec478578`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0012.json` sha256 `41138ab322fd84fc84af6e1658a38dd625888c6685144e0599a29fb28528df65`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0013.json` sha256 `c25a69b354bc19cf4b8786b4fc02634399d93bcfe029fa15b1a5b458e3de4782`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0014.json` sha256 `f67266b5c18b8e0e62140620c7927e17303bf666e43e2dd516f40c6dfd952b92`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0015.json` sha256 `1c766d416fb48a481fdd49b676297c7fa299df7b461e20e358d9193c0018b555`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0016.json` sha256 `a23cb803b7d7966a87b825e5c45430b4b90955da34b9c15e8fc043d638c552ba`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0017.json` sha256 `bc71c9e4bbce0242ae83c1b1786544b7ae32a0d04bfbb506500b4862a917e90c`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0018.json` sha256 `67d95a086429a9696ca3b19e74156ab2f22ceb162efcf97bcd2a07c4c3a6e385`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0019.json` sha256 `7397f235fd51a39cfcf4c1c50286b47016bce4c7a5487ec886c68feb5994a4c2`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0020.json` sha256 `ac5f52c8ef91ca64fe44ddd254307477fa9453543c9372147370725d282229d4`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0021.json` sha256 `cc49b314ffd5fc6a12844409c6dbe3a5a630be9e95aa56453c9f06734cc9d311`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0022.json` sha256 `56796196a1cf7a7fc31ab62aec11094d5f7d4111796bccd63d4fc08fb56a9773`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/replay/400/c10_replay_400_0023.json` sha256 `a59152143b134450dec6b6d3b2b781f1040723322f3b200592fb4f28bac192b5`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/storm2/w80/c10_storm2_w80_u100_0000.json` sha256 `af1e3202ba5363172739d85aa0ec93fab7b1ba92f76b9b9405efc3e09380049d`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/storm2/w80/c10_storm2_w80_u100_0001.json` sha256 `fdaf732105ff088e6d3a751bdce0cd5191c834d8cd5a2dfcc33a83c076b94e92`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/storm2/w80/c10_storm2_w80_u100_0002.json` sha256 `ced5dbdb0ad0cd194bc00b15b412ba5e3555a93a35c29bc91e6e6c7b3898aff5`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/storm2/w80/c10_storm2_w80_u100_0003.json` sha256 `aa703b1277691bc4629d2c9cfcc9c5cdacd071c95e3b4cde877d5a463eed98cb`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/storm2/w80/c10_storm2_w80_u100_0004.json` sha256 `d1fb8df2be75ccc26acd990c9ea372f7f7eb4cf16b5b5b241f1e4ad621c7aabc`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/storm2/w80/c10_storm2_w80_u100_0005.json` sha256 `cdd709e044247b2084a3eb1eb31ed9b8b861cd31f8bf5306666595bb87a56697`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/storm2/w80/c10_storm2_w80_u100_0006.json` sha256 `adde8dcf0073591e158cbc4752d383be6d9e932034c78cf4e31ff7697248229a`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/storm2/w80/c10_storm2_w80_u100_0007.json` sha256 `7d21eeaff011081a21f12c07504635a41b338789882afe296c4ceb29e99e11b4`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/storm2/w80/c10_storm2_w80_u100_0008.json` sha256 `6586b23b0d871a093dba6e2177598ba93f94fe844aa1a513023a821b1e143bee`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/storm2/w80/c10_storm2_w80_u100_0009.json` sha256 `53d71b229992effe56fe4ff7ddab4cd8a58a8a588953d50f1df4af3483adf5b3`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/storm2/w80/c10_storm2_w80_u100_0010.json` sha256 `635c2000ec895920eb8a02f82f7a918d5d0f6d6b865d1ab2fe93f3787479562a`
- `/home/ziheng/PaperY-FMScheduling/data/processed/instances/c10/storm2/w80/c10_storm2_w80_u100_0011.json` sha256 `e085aedded8f0496ce0b539793c9f17ed81fc1fea498ab561b745375e6ad7755`
