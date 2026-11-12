# New macros of the 2026-08-23 review response: names, values, meanings

Every macro the five new generator groups mint, with the value it currently expands to and what it measures. It exists so a drafting session can reach for a number without opening the CSVs.

**The authority is `manuscript/macros.tex`, not this file.** The values below were copied out of it at sha256 `06911e13d2f25ea83e7f6e5418fd62337a1af4a7307046b3ea7107bbb148fb96`; regenerate the file with `python code/scripts/paper_macros.py` and the copies here may go stale, while the macros themselves cannot.

99 macros in 5 groups. Percentage macros carry their own escaped per-cent sign, so prose writes `\dgJackVThreeMin` and never `\dgJackVThreeMin\%`. Damage macros are unitless here: prose adds " bh". Percentage-point macros carry a sign and no per-cent sign.

## The direct benchmark split by instance stratum

Source: `analysis/DG1_direct_guard.csv`, reading=canonical, config=G_CERT.

Table 7's two headline rates cut by the three strata that partition the 2,000 canonical items. The generator asserts the partition and asserts that the split reproduces the pooled 201 of 220 and 21 of 800. The point of the split is the benign column: the whole of the guard's benign cost sits in one constructed storm stratum.

| macro | value | meaning |
| --- | --- | --- |
| `\dgVThreeCanonicalRefusedCNine` | 108 | V3 canonical proposals the guard refuses in c09_storm2_w80 |
| `\dgVThreeCanonicalItemsCNine` | 114 | V3 items in c09_storm2_w80 |
| `\dgVThreeCanonicalShareCNine` | 94.7% | share of V3 canonical proposals refused in c09_storm2_w80 |
| `\dgBenignCanonicalBlocksCNine` | 21 | benign canonical proposals refused in c09_storm2_w80 |
| `\dgBenignCanonicalItemsCNine` | 394 | benign items in c09_storm2_w80 |
| `\dgBenignCanonicalShareCNine` | 5.3% | benign false-block share in c09_storm2_w80 (all 21 pooled false blocks sit here) |
| `\dgVThreeCanonicalRefusedCTenStorm` | 38 | V3 canonical proposals refused in c10_storm2_w80 |
| `\dgVThreeCanonicalItemsCTenStorm` | 41 | V3 items in c10_storm2_w80 |
| `\dgVThreeCanonicalShareCTenStorm` | 92.7% | share of V3 canonical proposals refused in c10_storm2_w80 |
| `\dgBenignCanonicalBlocksCTenStorm` | 0 | benign canonical proposals refused in c10_storm2_w80 (none) |
| `\dgBenignCanonicalItemsCTenStorm` | 153 | benign items in c10_storm2_w80 |
| `\dgBenignCanonicalShareCTenStorm` | 0.0% | benign false-block share in c10_storm2_w80 |
| `\dgVThreeCanonicalRefusedReplay` | 55 | V3 canonical proposals refused in c10_replay_400, the recorded window of work orders |
| `\dgVThreeCanonicalItemsReplay` | 65 | V3 items in c10_replay_400 |
| `\dgVThreeCanonicalShareReplay` | 84.6% | share of V3 canonical proposals refused in c10_replay_400 |
| `\dgBenignCanonicalBlocksReplay` | 0 | benign canonical proposals refused in c10_replay_400 (none) |
| `\dgBenignCanonicalItemsReplay` | 253 | benign items in c10_replay_400 |
| `\dgBenignCanonicalShareReplay` | 0.0% | benign false-block share in c10_replay_400 |

## DG16: leave-one-instance-out envelope

Source: `analysis/DG16_jackknife.csv`, block=envelope, family=instance.

Every published direct-guard rate recomputed 60 times, once with each scheduling instance deleted. Two decimals, because the whole point is a movement smaller than a point. A fold counts only when it removes at least one item from the metric's own denominator, which is why the V3 envelope has 56 folds and the benign one 60.

| macro | value | meaning |
| --- | --- | --- |
| `\dgJackVThreeMin` | 91.00% | lowest V3 refusal share any single-instance deletion produces |
| `\dgJackVThreeMax` | 92.20% | highest V3 refusal share any single-instance deletion produces |
| `\dgJackVThreeFolds` | 56 | instances carrying at least one V3 item, so the V3 envelope's fold count |
| `\dgJackBenignMin` | 1.27% | lowest benign false-block share any single-instance deletion produces |
| `\dgJackBenignMax` | 2.71% | highest benign false-block share any single-instance deletion produces |
| `\dgJackBenignFolds` | 60 | instances behind the benign envelope (all of them) |

## DG17: the threshold-guard comparison replayed end to end

Source: `analysis/DG17_e2e_delta.csv`, block=headline, in_capability_set=True, primary policy `heldout_matched_loso`.

Every constrained-mode proposal the eight capability cells emitted, re-adjudicated with the logged schema and feasibility verdicts held fixed and the quality stage swapped for a hand-written threshold on a reference schedule. No model was called. Ranges run over the eight capability cells {qwen3-14b/-, qwen3.6-27b-fp8/-, glm-4-9b/-, openai/-, sonnet/disabled, opus/default, opus/disabled, sol/none}; the flagship cell is opus/default. **The V3 column is partly circular** and must never be quoted without one of the suite-construction macros at the end of this section: the suite admits a V3 item on D-REL2's own statistic. D-REL2 is the relative threshold against the proposal's own constraints-removed reference, D-REL1 the relative threshold against the no-op reference, D-ABS the absolute one in business hours.

| macro | value | meaning |
| --- | --- | --- |
| `\dgEOneDeltaFlagshipCertVThreeSep` | 90.5% | flagship cell: the certificate's V3 separation |
| `\dgEOneDeltaFlagshipRelTwoVThreeSep` | 99.1% | flagship cell: the best threshold rule's V3 separation |
| `\dgEOneDeltaFlagshipCertFalseBlock` | 3.9% | flagship cell: the certificate's benign false block |
| `\dgEOneDeltaFlagshipRelTwoFalseBlock` | 1.6% | flagship cell: the best threshold rule's benign false block |
| `\dgEOneDeltaCertVThreeSepMin` | 72.7% | certificate V3 separation, lowest of the eight cells (equals the published \eOneVThreeSepMin; asserted) |
| `\dgEOneDeltaCertVThreeSepMax` | 90.5% | certificate V3 separation, highest of the eight cells (equals the published \eOneVThreeSepMax; asserted) |
| `\dgEOneDeltaRelTwoVThreeSepMin` | 77.7% | D-REL2 V3 separation, lowest of the eight cells |
| `\dgEOneDeltaRelTwoVThreeSepMax` | 99.1% | D-REL2 V3 separation, highest of the eight cells |
| `\dgEOneDeltaAbsVThreeSepMin` | 66.4% | D-ABS V3 separation, lowest of the eight cells |
| `\dgEOneDeltaAbsVThreeSepMax` | 86.8% | D-ABS V3 separation, highest of the eight cells |
| `\dgEOneDeltaRelOneVThreeSepMin` | 39.5% | D-REL1 V3 separation, lowest of the eight cells |
| `\dgEOneDeltaRelOneVThreeSepMax` | 77.7% | D-REL1 V3 separation, highest of the eight cells |
| `\dgEOneDeltaCertFalseBlockMin` | 3.8% | certificate benign false block, lowest of the eight cells |
| `\dgEOneDeltaCertFalseBlockMax` | 8.6% | certificate benign false block, highest of the eight cells |
| `\dgEOneDeltaRelTwoFalseBlockMin` | 1.4% | D-REL2 benign false block, lowest of the eight cells |
| `\dgEOneDeltaRelTwoFalseBlockMax` | 6.2% | D-REL2 benign false block, highest of the eight cells |
| `\dgEOneDeltaFlagshipFeasDamage` | +36.96 | flagship cell: damage against the no-AI anchor under the feasibility guard alone, in bh per instruction |
| `\dgEOneDeltaFlagshipFeasDamageLo` | +28.70 | lower end of its 95% cluster-bootstrap interval over the 60 instances |
| `\dgEOneDeltaFlagshipFeasDamageHi` | +45.81 | upper end of that interval |
| `\dgEOneDeltaFlagshipCertDamage` | -0.55 | flagship cell: damage against the no-AI anchor under the certificate |
| `\dgEOneDeltaFlagshipCertDamageLo` | -1.21 | lower end of its 95% interval |
| `\dgEOneDeltaFlagshipCertDamageHi` | +0.07 | upper end of its 95% interval (crosses zero) |
| `\dgEOneDeltaFlagshipRelTwoDamage` | -1.07 | flagship cell: damage against the no-AI anchor under D-REL2 |
| `\dgEOneDeltaFlagshipRelTwoDamageLo` | -1.70 | lower end of its 95% interval |
| `\dgEOneDeltaFlagshipRelTwoDamageHi` | -0.52 | upper end of its 95% interval (below zero) |
| `\dgEOneDeltaCertAcceptedAboveTau` | 0.0% | certificate: share of accepted instructions whose own executed schedule certifies above tau, exactly zero on every cell |
| `\dgEOneDeltaRelTwoAcceptedAboveTauMin` | 2.8% | D-REL2: same share, lowest of the eight cells |
| `\dgEOneDeltaRelTwoAcceptedAboveTauMax` | 3.2% | D-REL2: same share, highest of the eight cells |
| `\dgEOneDeltaAbsAcceptedAboveTauMin` | 4.0% | D-ABS: same share, lowest of the eight cells |
| `\dgEOneDeltaAbsAcceptedAboveTauMax` | 5.0% | D-ABS: same share, highest of the eight cells |
| `\dgEOneDeltaRelOneAcceptedAboveTauMin` | 4.8% | D-REL1: same share, lowest of the eight cells |
| `\dgEOneDeltaRelOneAcceptedAboveTauMax` | 8.9% | D-REL1: same share, highest of the eight cells |
| `\dgEOneDeltaUnionVThreeSepMin` | 80.0% | certificate composed with D-REL2 (refuse if either refuses): V3 separation, lowest of the eight cells |
| `\dgEOneDeltaUnionVThreeSepMax` | 99.1% | the same, highest of the eight cells |
| `\dgEOneDeltaUnionFalseBlockIncMin` | +0.2 | what composing D-REL2 onto the certificate adds to benign false block, in percentage points, smallest of the eight cells |
| `\dgEOneDeltaUnionFalseBlockIncMax` | +0.6 | the same, largest of the eight cells |
| `\dgEOneDeltaUnionFlagshipVThreeSep` | 99.1% | flagship cell under the composed guard: V3 separation |
| `\dgEOneDeltaUnionFlagshipFalseBlock` | 4.2% | flagship cell under the composed guard: benign false block |
| `\dgEOneDeltaRelTwoDispatchMin` | 0.176 | extra reference dispatches per instruction D-REL2 needs after caching, lowest of the eight cells |
| `\dgEOneDeltaRelTwoDispatchMax` | 0.544 | the same, highest of the eight cells (its reference depends on the proposal, so it is not reusable) |
| `\dgEOneDeltaRefDispatchMin` | 0.019 | extra cached dispatches per instruction for D-REL1 and D-ABS together, lowest over both rules and all eight cells |
| `\dgEOneDeltaRefDispatchMax` | 0.058 | the same, highest over both rules and all eight cells |
| `\dgEOneDeltaCertBoundMsMin` | 0.66 | median wall time of the certificate's own bound, in milliseconds, lowest of the eight cells |
| `\dgEOneDeltaCertBoundMsMax` | 0.68 | the same, highest of the eight cells |
| `\dgEOneDeltaCertVFourQualSep` | 64 | quality-visible V4 rows the certificate separates and the feasibility guard does not, pooled over the eight cells |
| `\dgEOneDeltaVFourQualRows` | 880 | quality-visible V4 rows those separations are drawn from, pooled over the eight cells |
| `\dgEOneDeltaBestRuleVFourQualSep` | 3 | the most any of the three threshold rules separates on the same rows |
| `\dgEOneDeltaCertVFourQualSelfBlock` | 64 | of the certificate's quality-visible V4 separations, how many sit on the two instances whose no-op schedule already certifies above tau (all of them) |
| `\dgEOneDeltaCertVThreeSelfBlock` | 128 | of the certificate's V3 separations, how many sit on those two instances |
| `\dgEOneDeltaCertVThreeSepTotal` | 2,977 | the certificate's V3 separations in total, pooled over the eight cells |
| `\dgEOneDeltaCertFalseBlockSelfBlock` | 340 | of the certificate's benign false blocks, how many sit on those two instances |
| `\dgEOneDeltaCertFalseBlockTotal` | 636 | the certificate's benign false blocks in total, pooled over the eight cells |
| `\dgEOneDeltaSuiteVThreeItems` | 220 | V3 items in the frozen suite |
| `\dgEOneDeltaSuiteVThreePositive` | 220 | V3 items whose canonical operation list carries a strictly positive D-REL2 quantity (all of them: the class is admitted on that statistic) |
| `\dgEOneDeltaSuiteVThreeQuantMin` | 0.0140 | smallest canonical D-REL2 quantity over the V3 items |
| `\dgEOneDeltaSuiteVThreeQuantMedian` | 0.548 | median canonical D-REL2 quantity over the V3 items |
| `\dgEOneDeltaSuiteBenignItems` | 800 | benign items in the frozen suite |
| `\dgEOneDeltaSuiteBenignPositive` | 8 | benign items carrying a positive canonical D-REL2 quantity at all |
| `\dgEOneDeltaSuiteBenignQuantMax` | 0.0155 | largest canonical D-REL2 quantity over the benign items |

## DG18: the agent-layer tests with the instance as the exchangeable unit

Source: `analysis/DG18_cluster_tests.csv`.

The declared family of 96 tests behind Section 5.4, re-run with the paired sign flipped at the instance level rather than the item level, under both readings of violation pass-through. **Every verdict the manuscript prints is unchanged**, and the generator asserts it rather than the prose claiming it. Deliberately minimal: a p-value that does not move needs no macro.

| macro | value | meaning |
| --- | --- | --- |
| `\dgClusterTests` | 96 | tests in the declared agent-layer family, one reading |
| `\dgClusterReadings` | 2 | readings of violation pass-through the family was run under |
| `\dgClusterReadingsWord` | two | the same count spelled out, for use as a count noun in prose |
| `\dgClusterCitedTests` | 30 | tests behind a verdict the manuscript prints; every one keeps its verdict, uncorrected and after Holm |
| `\dgClusterHolmFlips` | 2 | tests whose Holm-corrected verdict changes under the disposition reading; neither is printed as a p-value in the paper |
| `\dgClusterHolmFlipsWord` | two | the same count spelled out |
| `\dgClusterHolmFlipsContent` | 2 | the same count under the pass-through content rule, and the same two cells |

## DG19: the certificate's slack where the optimum is proved

Source: `analysis/DG19_tightness.csv`, budget 5 s, population `optimal_positive`.

The certified gap minus the gap to the CP-SAT-proved optimum, on the rows of the Tier-1 slice the solver closed at the 5-second budget with a positive objective. The excess is the bound's slack in the units the tolerance is set in, so it is directly comparable with tau = 0.20. Two boundaries travel with the number and are asserted in the generator: every proof sits in the recorded stratum, and every row of the slice is one the certificate accepted, so the slack is measured away from the refusal boundary rather than on it.

| macro | value | meaning |
| --- | --- | --- |
| `\dgTightRows` | 108 | rows the solver proved optimal with a positive objective, the population of this group |
| `\dgTightInstances` | 15 | instances those rows sit on |
| `\dgTightExcessMedian` | 0.0004 | median slack of the analytic bound, on the same scale as tau |
| `\dgTightExcessMax` | 0.0012 | largest slack observed (reported as observed, without an interval) |
| `\dgTightZeroGapShare` | 63.9% | share of those rows whose certified gap is exactly zero, where the bound already equals the realized objective |
| `\dgTightZeroGapRows` | 69 | the same as a count |
| `\dgTightMinTrueGapForBlock` | 0.1988 | tau minus the largest measured slack: slack of that size can only carry a proposal across the tolerance if its true gap is already at least this large |
| `\dgTightProvedReplay` | 144 | rows of the slice the solver closed, all of them in c10_replay_400 |
| `\dgTightProvedStorm` | 0 | rows closed in the two storm strata (none), which is the coverage boundary of this measurement |
