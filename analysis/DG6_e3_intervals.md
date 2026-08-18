<!--
  generated 2026-08-17 18:05:45 +0800 by e3_intervals.py (l1-dg6-intervals-2)
  paired bootstrap: 20000 resamples, numpy default_rng seeded [20260814, cell index]; percentile intervals
  second interval: Newcombe (1998) method 10 for paired proportions (MOVER over two Wilson intervals with the observed phi)
  third interval: cluster bootstrap resampling whole scheduling instances
  self-check: the 18 loose-budget and 18 tight-budget 2x2 tables are rebuilt from results/e3_replay_*/verdicts.jsonl and asserted cell for cell against analysis/E8_adjudication.csv; the exact McNemar p-values, the Wilcoxon p-values, the Holm corrections and the published minima are recomputed rather than read
  the reported passthrough outcome is the V4/V6 content rule (code/scripts/passthrough_rule.py): an applied V4 or V6 row counts unless the applied operations are exactly the item's non-empty gold_ops; false_block and catch are dispositions and are unchanged; the e8_* columns of a passthrough row carry E8's earlier disposition-only reading and are not this one
  /home/ziheng/PaperL1/results/e3_replay_qwen14b/verdicts.jsonl sha256 02000960325ccbef18394354273795ab22638e252eb7a1f4478a8ad26ad99606
  /home/ziheng/PaperL1/results/e3_replay_qwen27b/verdicts.jsonl sha256 a21c32d9ff46d67068822a7b95db6bb4041d268e6816bf7351af8899ef3462de
  /home/ziheng/PaperL1/results/e3_replay_openai/verdicts.jsonl sha256 168a8b20626a3b70ea16308f7a56af95abe146da4e5607fdb3d3b6f36692dfee
  /home/ziheng/PaperL1/results/e3_replay_deepseek/verdicts.jsonl sha256 8e42a2c7a2730cee28e6de7aba54b4f96f88c87a712eb5a95c83fb8549106d4b
  /home/ziheng/PaperL1/results/e3_replay_sonnet/verdicts.jsonl sha256 8784318b09fb75599bb1d562cf156c3838b407833647fe82712e333b3d46ca36
  /home/ziheng/PaperL1/results/e3_replay_opus/verdicts.jsonl sha256 9af87fa798a1aede09a82db34cadee9455d6d20b65302c16f0a4ac89b2453a17
  /home/ziheng/PaperL1/analysis/E8_adjudication.csv sha256 38a6b4222d44e3e3d55ecf9e27864b953093da88f8e79b8cc5c5ae921dfc9eaf
  end-task quality: suite sha256 0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a
  end-task quality: adjustment schema sha256 1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321
  end-task quality: e3_analyze reconciliation 7533/7533 passed
  end-task quality is recomputed by e3_analyze.load_arm / evaluate_rows / build_entries (the guard re-evaluation), because wwt_original_bh is not in results/e3_replay_*/verdicts.jsonl
  margins: 5.0 pp is the primary binary margin and 10.0 bh the primary quality margin; both are set at roughly a quarter of the effect the guard itself produces on the same items at the same budget (MULTI-G vs MULTI-UG, loose): 15.6 to 24.0 pp on violation pass-through under the content rule (16.7 to 25.0 pp under E8's disposition-only reading) and 36.8 to 44.3 bh on mean per-item quality, over the five arms whose unguarded variant emits executable proposals
-->

# DG6. Intervals, equivalence tests and design power for the E3 agent-layer comparison

SINGLE+G minus MULTI-G, on the same items, at both budget levels. A negative risk difference means MULTI-G has the higher rate on that outcome; whether that favours MULTI-G depends on the outcome, and the `favours` column states which architecture the sign is good for.

The `passthrough` outcome applies the V4/V6 content rule (`code/scripts/passthrough_rule.py`): an applied V4 or V6 row counts as pass-through unless the applied operations are exactly the item's non-empty ground truth. `false_block` and `catch` are dispositions, which the rule does not reach, so they are unchanged. The self-check below still reconciles against `E8_adjudication.csv`, which carries the earlier disposition-only reading of pass-through, so the E8 columns of a `passthrough` row are that reading and not this one.

Source files, filters and hashes are in the comment header of `DG6_e3_intervals.csv`. The script is `code/scripts/e3_intervals.py`.

## Self-check

All 11791 assertions passed (0 failed). What was reproduced:

- The 18 loose-budget and 18 tight-budget SINGLE+G vs MULTI-G 2x2 tables, rebuilt from `results/e3_replay_<arm>/verdicts.jsonl` (repeat 0, last row per key), match `analysis/E8_adjudication.csv` on `n_units`, `a_only`, `b_only`, `both` and `neither`, 36 of 36 tables and 180 of 180 cells.
- Every exact McNemar p-value and every Wilcoxon p-value recomputed from those tables equals E8's `p_raw` to six significant figures, 48 of 48.
- The published minima: the smallest uncorrected p-value at the loose budget is 0.0923 (Qwen3.6-27B-FP8, violation catch), the smallest Holm-corrected p-value at the loose budget is 1.00, and 9 of the 24 tight-budget SINGLE+G vs MULTI-G cells are significant under Holm over the whole family of 96. All three matched exactly.
- The interval estimators were validated before use: the Wilson endpoints solve the score equation to 1e-8, and the square-and-add combination reproduces Newcombe's published worked example (56/70 against 48/80 gives 0.0524 to 0.3339 at 95%).

## The margins, and why they are what they are

A margin chosen because it passes is worthless, so both margins are set as a fraction of an effect this paper has already measured on the same items, at the same budget, with the same guard: the effect of adding the guard at a fixed architecture (MULTI-G against MULTI-UG at the loose budget).

| reference effect (MULTI-G vs MULTI-UG, loose) | value |
| --- | --- |
| violation pass-through, five arms with executable unguarded proposals | 15.6 to 24.0 pp |
| the same, under the disposition-only reading E8 carries | 16.7 to 25.0 pp |
| mean per-item end-task quality, same five arms | 36.8 to 44.3 bh |

- **Binary outcomes: 5 pp primary.** Five percentage points is 32% of the smallest guard effect on violation pass-through (15.6 pp), so declaring the two architectures equivalent at this margin still preserves 68% of the effect the guard itself buys. The conventional half-of-the-reference-effect rule would license 7.8 pp, so 5 pp is the stricter choice. In workload terms it is 4.8 instructions out of the 96 labelled violations, or roughly one violating instruction per twenty.
- **2.5 pp and 10 pp** are reported beside it. 10 pp is the loosest defensible margin: it is 64% of the smallest guard effect, at the edge of the conventional rule.
- **End-task quality: 10 bh primary**, on the mean per-item paired difference in weighted business hours. Ten weighted business hours is 27% of the smallest guard effect on the same quantity (36.8 bh), which matches the binary margin's preservation fraction. 5 bh and 20 bh are reported beside it.

## What the design could have detected

Exact trinomial power for the two-sided exact McNemar test at n = 96 paired items. `best case` puts every discordant pair in one direction, which is the easiest structure to detect, so the figure is a floor: no allocation of the discordant pairs makes a smaller risk difference detectable.

| level | alpha | fewest one-directional discordant pairs that can reach significance | smallest |RD| at 80% power, best case |
| --- | --- | --- | --- |
| uncorrected | 5.00e-02 | 6 of 96 (6.2 pp) | 8.1 pp |
| Holm, per-question family (m = 12) | 4.17e-03 | 9 of 96 (9.4 pp) | 11.6 pp |
| Holm, whole family, realised threshold for a loose cell | 6.58e-04 | 12 of 96 (12.5 pp) | 15.1 pp |
| Holm, whole family, first-step bound (0.05/96) | 5.21e-04 | 12 of 96 (12.5 pp) | 15.1 pp |

The first-step bound 0.05/96 is conservative, because a loose-budget cell with a real effect would not have been the smallest p-value in the family: nine tight-budget cells and the guard contrasts already sit below it. The realised threshold, found by putting a candidate p-value back into the observed family of 96 and asking what Holm does with it, is 6.58e-04, and it does not change the answer.

Under the correction the manuscript reports, the test cannot return a significant result at all unless at least 12 of the 96 pairs are discordant, and it needs a true risk difference of at least 15.1 pp before it reaches 80% power even when every discordant pair points the same way.

At the loose budget the observed discordance is far below that. Of the 18 binary cells, 6 had enough discordant pairs for an uncorrected significant result to be arithmetically possible, and 2 had enough for a Holm-corrected one. On end-task quality the same arithmetic applies to the number of items whose schedules differ at all, because the signed-rank test with every difference in one direction gives the same p-value as McNemar with every discordant pair in one direction: 4 of the 6 arms had enough differing items for an uncorrected significant result and 1 for a Holm-corrected one.

**Taking the 24 loose-budget cells together, 3 of 24 could have returned a Holm-significant result at any true effect size, and 10 of 24 could have returned an uncorrected one.** The loose-budget null is therefore in large part a statement about the instrument, not about the architectures.

Holding each cell's discordance rate at its observed value, 80% power is out of reach at any risk difference in 14 of the 18 loose binary cells even with no correction at all. The 4 cells where an uncorrected test could have reached 80% power needed a true difference of 8.2 to 11.0 pp.

## Loose budget: SINGLE+G minus MULTI-G

| arm | outcome | n | a-only / b-only | RD | 95% CI (bootstrap) | 95% CI (Newcombe) | 90% CI (bootstrap) | favours | 2.5 pp | 5 pp | 10 pp |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |
| qwen14b | false_block | 96 | 0 / 0 | +0.00 pp | [+0.00, +0.00] | [-3.77, +3.77] | [+0.00, +0.00] | neither | indet | equiv | equiv |
| qwen14b | catch | 96 | 1 / 0 | +1.04 pp | [+0.00, +3.12] | [-2.68, +5.57] | [+0.00, +3.12] | SINGLE+G | indet | equiv | equiv |
| qwen14b | passthrough | 96 | 2 / 6 | -4.17 pp | [-10.42, +1.04] | [-10.03, +1.62] | [-9.38, +0.00] | SINGLE+G | indet | indet | equiv |
| qwen27b | false_block | 96 | 0 / 2 | -2.08 pp | [-5.21, +0.00] | [-7.10, +1.81] | [-5.21, +0.00] | SINGLE+G | indet | indet | equiv |
| qwen27b | catch | 96 | 3 / 10 | -7.29 pp | [-14.58, +0.00] | [-15.21, +0.08] | [-13.54, -1.04] | MULTI-G | indet | indet | indet |
| qwen27b | passthrough | 96 | 3 / 3 | +0.00 pp | [-5.21, +5.21] | [-5.13, +5.13] | [-4.17, +4.17] | neither | indet | equiv | equiv |
| openai | false_block | 96 | 0 / 0 | +0.00 pp | [+0.00, +0.00] | [-3.77, +3.77] | [+0.00, +0.00] | neither | indet | equiv | equiv |
| openai | catch | 96 | 0 / 2 | -2.08 pp | [-5.21, +0.00] | [-6.99, +1.81] | [-5.21, +0.00] | MULTI-G | indet | indet | equiv |
| openai | passthrough | 96 | 6 / 4 | +2.08 pp | [-4.17, +8.33] | [-4.33, +8.48] | [-3.12, +7.29] | MULTI-G | indet | indet | equiv |
| deepseek | false_block | 96 | 0 / 0 | +0.00 pp | [+0.00, +0.00] | [-3.85, +3.85] | [+0.00, +0.00] | neither | indet | equiv | equiv |
| deepseek | catch | 96 | 4 / 0 | +4.17 pp | [+1.04, +8.33] | [-0.44, +10.23] | [+1.04, +7.29] | SINGLE+G | indet | indet | equiv |
| deepseek | passthrough | 96 | 4 / 10 | -6.25 pp | [-13.54, +1.04] | [-14.21, +1.43] | [-12.50, +0.00] | SINGLE+G | indet | indet | indet |
| sonnet | false_block | 96 | 0 / 0 | +0.00 pp | [+0.00, +0.00] | [-3.85, +3.85] | [+0.00, +0.00] | neither | indet | equiv | equiv |
| sonnet | catch | 96 | 0 / 2 | -2.08 pp | [-5.21, +0.00] | [-7.20, +1.79] | [-5.21, +0.00] | MULTI-G | indet | indet | equiv |
| sonnet | passthrough | 96 | 4 / 3 | +1.04 pp | [-4.17, +6.25] | [-4.55, +6.68] | [-3.12, +5.21] | MULTI-G | indet | indet | equiv |
| opus | false_block | 96 | 0 / 1 | -1.04 pp | [-3.12, +0.00] | [-5.67, +2.90] | [-3.12, +0.00] | SINGLE+G | indet | equiv | equiv |
| opus | catch | 96 | 0 / 1 | -1.04 pp | [-3.12, +0.00] | [-5.67, +2.90] | [-3.12, +0.00] | MULTI-G | indet | equiv | equiv |
| opus | passthrough | 96 | 2 / 1 | +1.04 pp | [-2.08, +4.17] | [-2.96, +5.16] | [-2.08, +4.17] | MULTI-G | indet | equiv | equiv |

| arm | end-task quality | n | differing items | estimate | 95% CI (bootstrap) | 90% CI (bootstrap) | favours | 5 bh | 10 bh | 20 bh |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- |
| qwen14b | mean | 240 | 14 | -0.531 bh | [-1.56, +0.30] | [-1.37, +0.18] | SINGLE+G | equiv | equiv | equiv |
| qwen14b | median | 240 | 14 | +0.000 bh | [+0.00, +0.00] | [+0.00, +0.00] | neither | equiv | equiv | equiv |
| qwen14b | pseudomedian | 240 | 14 | +0.000 bh | not bootstrapped | - | neither | indet | indet | indet |
| qwen14b | identical objective share | 240 | 14 | 94.2% | - | - | - | - | - | - |
| qwen27b | mean | 240 | 1 | -0.740 bh | [-2.22, +0.00] | [-2.22, +0.00] | SINGLE+G | equiv | equiv | equiv |
| qwen27b | median | 240 | 1 | +0.000 bh | [+0.00, +0.00] | [+0.00, +0.00] | neither | equiv | equiv | equiv |
| qwen27b | pseudomedian | 240 | 1 | +0.000 bh | not bootstrapped | - | neither | indet | indet | indet |
| qwen27b | identical objective share | 240 | 1 | 99.6% | - | - | - | - | - | - |
| openai | mean | 240 | 6 | -1.389 bh | [-4.11, -0.01] | [-4.06, -0.01] | SINGLE+G | equiv | equiv | equiv |
| openai | median | 240 | 6 | +0.000 bh | [+0.00, +0.00] | [+0.00, +0.00] | neither | equiv | equiv | equiv |
| openai | pseudomedian | 240 | 6 | +0.000 bh | not bootstrapped | - | neither | indet | indet | indet |
| openai | identical objective share | 240 | 6 | 97.5% | - | - | - | - | - | - |
| deepseek | mean | 240 | 9 | +0.192 bh | [-0.27, +0.72] | [-0.21, +0.62] | MULTI-G | equiv | equiv | equiv |
| deepseek | median | 240 | 9 | +0.000 bh | [+0.00, +0.00] | [+0.00, +0.00] | neither | equiv | equiv | equiv |
| deepseek | pseudomedian | 240 | 9 | +0.000 bh | not bootstrapped | - | neither | indet | indet | indet |
| deepseek | identical objective share | 240 | 9 | 96.2% | - | - | - | - | - | - |
| sonnet | mean | 240 | 6 | -0.180 bh | [-0.53, +0.00] | [-0.52, -0.00] | SINGLE+G | equiv | equiv | equiv |
| sonnet | median | 240 | 6 | +0.000 bh | [+0.00, +0.00] | [+0.00, +0.00] | neither | equiv | equiv | equiv |
| sonnet | pseudomedian | 240 | 6 | +0.000 bh | not bootstrapped | - | neither | indet | indet | indet |
| sonnet | identical objective share | 240 | 6 | 97.5% | - | - | - | - | - | - |
| opus | mean | 240 | 1 | +0.101 bh | [+0.00, +0.30] | [+0.00, +0.30] | MULTI-G | equiv | equiv | equiv |
| opus | median | 240 | 1 | +0.000 bh | [+0.00, +0.00] | [+0.00, +0.00] | neither | equiv | equiv | equiv |
| opus | pseudomedian | 240 | 1 | +0.000 bh | not bootstrapped | - | neither | indet | indet | indet |
| opus | identical objective share | 240 | 1 | 99.6% | - | - | - | - | - | - |

## Tight budget: SINGLE+G minus MULTI-G

| arm | outcome | n | a-only / b-only | RD | 95% CI (bootstrap) | 95% CI (Newcombe) | 90% CI (bootstrap) | favours | 2.5 pp | 5 pp | 10 pp |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |
| qwen14b | false_block | 96 | 3 / 0 | +3.12 pp | [+0.00, +7.29] | [-1.24, +8.79] | [+1.04, +6.25] | MULTI-G | indet | indet | equiv |
| qwen14b | catch | 96 | 29 / 0 | +30.21 pp | [+20.83, +39.58] | [+21.08, +40.01] | [+22.92, +37.50] | SINGLE+G | REFUTED | REFUTED | REFUTED |
| qwen14b | passthrough | 96 | 8 / 0 | +8.33 pp | [+3.12, +14.58] | [+2.75, +15.59] | [+4.17, +13.54] | MULTI-G | REFUTED | indet | indet |
| qwen27b | false_block | 96 | 3 / 0 | +3.12 pp | [+0.00, +7.29] | [-1.24, +8.79] | [+1.04, +6.25] | MULTI-G | indet | indet | equiv |
| qwen27b | catch | 96 | 17 / 0 | +17.71 pp | [+10.42, +26.04] | [+10.29, +26.54] | [+11.46, +23.96] | SINGLE+G | REFUTED | REFUTED | REFUTED |
| qwen27b | passthrough | 96 | 10 / 0 | +10.42 pp | [+5.21, +16.67] | [+4.37, +18.12] | [+5.21, +15.62] | MULTI-G | REFUTED | REFUTED | indet |
| openai | false_block | 96 | 6 / 0 | +6.25 pp | [+2.08, +11.46] | [+1.15, +12.97] | [+2.08, +10.42] | MULTI-G | indet | indet | indet |
| openai | catch | 96 | 35 / 2 | +34.38 pp | [+23.96, +44.79] | [+23.68, +44.43] | [+26.04, +43.75] | SINGLE+G | REFUTED | REFUTED | REFUTED |
| openai | passthrough | 96 | 19 / 0 | +19.79 pp | [+12.50, +28.12] | [+12.24, +28.76] | [+13.54, +27.08] | MULTI-G | REFUTED | REFUTED | REFUTED |
| deepseek | false_block | 96 | 7 / 1 | +6.25 pp | [+1.04, +12.50] | [+0.24, +13.33] | [+2.08, +11.46] | MULTI-G | indet | indet | indet |
| deepseek | catch | 96 | 11 / 0 | +11.46 pp | [+5.21, +17.71] | [+5.20, +19.36] | [+6.25, +16.67] | SINGLE+G | REFUTED | REFUTED | indet |
| deepseek | passthrough | 96 | 3 / 0 | +3.12 pp | [+0.00, +7.29] | [-1.24, +8.79] | [+1.04, +6.25] | MULTI-G | indet | indet | equiv |
| sonnet | false_block | 96 | 1 / 4 | -3.12 pp | [-8.33, +1.04] | [-9.26, +2.05] | [-7.29, +0.00] | SINGLE+G | indet | indet | equiv |
| sonnet | catch | 96 | 20 / 1 | +19.79 pp | [+11.46, +28.12] | [+11.41, +28.75] | [+12.50, +27.08] | SINGLE+G | REFUTED | REFUTED | REFUTED |
| sonnet | passthrough | 96 | 8 / 3 | +5.21 pp | [-1.04, +12.50] | [-1.78, +12.77] | [+0.00, +10.42] | MULTI-G | indet | indet | indet |
| opus | false_block | 96 | 3 / 0 | +3.12 pp | [+0.00, +7.29] | [-0.91, +8.81] | [+1.04, +6.25] | MULTI-G | indet | indet | equiv |
| opus | catch | 96 | 27 / 0 | +28.12 pp | [+19.79, +37.50] | [+19.33, +37.63] | [+20.83, +35.42] | SINGLE+G | REFUTED | REFUTED | REFUTED |
| opus | passthrough | 96 | 5 / 3 | +2.08 pp | [-3.13, +8.33] | [-4.27, +8.79] | [-3.12, +7.29] | MULTI-G | indet | indet | equiv |

| arm | end-task quality | n | differing items | estimate | 95% CI (bootstrap) | 90% CI (bootstrap) | favours | 5 bh | 10 bh | 20 bh |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- |
| qwen14b | mean | 240 | 9 | +0.708 bh | [-0.03, +1.68] | [+0.06, +1.51] | MULTI-G | equiv | equiv | equiv |
| qwen14b | median | 240 | 9 | +0.000 bh | [+0.00, +0.00] | [+0.00, +0.00] | neither | equiv | equiv | equiv |
| qwen14b | pseudomedian | 240 | 9 | +0.000 bh | not bootstrapped | - | neither | indet | indet | indet |
| qwen14b | identical objective share | 240 | 9 | 96.2% | - | - | - | - | - | - |
| qwen27b | mean | 240 | 15 | -0.149 bh | [-0.39, +0.03] | [-0.35, +0.01] | SINGLE+G | equiv | equiv | equiv |
| qwen27b | median | 240 | 15 | +0.000 bh | [+0.00, +0.00] | [+0.00, +0.00] | neither | equiv | equiv | equiv |
| qwen27b | pseudomedian | 240 | 15 | +0.000 bh | not bootstrapped | - | neither | indet | indet | indet |
| qwen27b | identical objective share | 240 | 15 | 93.8% | - | - | - | - | - | - |
| openai | mean | 240 | 16 | +1.924 bh | [-0.06, +4.95] | [+0.08, +4.33] | MULTI-G | equiv | equiv | equiv |
| openai | median | 240 | 16 | +0.000 bh | [+0.00, +0.00] | [+0.00, +0.00] | neither | equiv | equiv | equiv |
| openai | pseudomedian | 240 | 16 | +0.000 bh | not bootstrapped | - | neither | indet | indet | indet |
| openai | identical objective share | 240 | 16 | 93.3% | - | - | - | - | - | - |
| deepseek | mean | 240 | 2 | -0.004 bh | [-0.02, +0.00] | [-0.01, +0.00] | SINGLE+G | equiv | equiv | equiv |
| deepseek | median | 240 | 2 | +0.000 bh | [+0.00, +0.00] | [+0.00, +0.00] | neither | equiv | equiv | equiv |
| deepseek | pseudomedian | 240 | 2 | +0.000 bh | not bootstrapped | - | neither | indet | indet | indet |
| deepseek | identical objective share | 240 | 2 | 99.2% | - | - | - | - | - | - |
| sonnet | mean | 240 | 15 | +0.022 bh | [-0.61, +0.87] | [-0.51, +0.69] | MULTI-G | equiv | equiv | equiv |
| sonnet | median | 240 | 15 | +0.000 bh | [+0.00, +0.00] | [+0.00, +0.00] | neither | equiv | equiv | equiv |
| sonnet | pseudomedian | 240 | 15 | +0.000 bh | not bootstrapped | - | neither | indet | indet | indet |
| sonnet | identical objective share | 240 | 15 | 93.8% | - | - | - | - | - | - |
| opus | mean | 240 | 14 | +0.307 bh | [-0.27, +1.16] | [-0.20, +0.99] | MULTI-G | equiv | equiv | equiv |
| opus | median | 240 | 14 | +0.000 bh | [+0.00, +0.00] | [+0.00, +0.00] | neither | equiv | equiv | equiv |
| opus | pseudomedian | 240 | 14 | +0.000 bh | not bootstrapped | - | neither | indet | indet | indet |
| opus | identical objective share | 240 | 14 | 94.2% | - | - | - | - | - | - |

## Instance clustering

The 240 items are drawn from 55 scheduling instances, up to 12 items per instance, so the paired differences are not independent across items. A cluster bootstrap that resamples whole instances is reported beside the item bootstrap. The largest absolute difference between a cluster-bootstrap endpoint and the corresponding item-bootstrap endpoint, over the 18 loose-budget binary cells, is 0.96 pp; over all 36 binary cells it is 1.48 pp. Clustering therefore does not change any verdict: the contrast is taken within an item, so the instance-level component of the variance cancels before the paired difference is formed.

## The honest answer

**One sentence.** At the loose budget the two architectures are equivalent within 10 percentage points on 16 of the 18 binary arm-by-outcome cells and within 5 points on 9, and equivalent within 10 weighted business hours on end-task quality on all 6 arms, but the design never had the power to say more than that: no paired difference exceeds 7.3 pp, yet the intervals still admit differences of up to 15.2 pp, so the null is a statement of no *detectable* difference, not of no difference.

Cell counts at the loose budget, by margin, over the 18 binary cells (equivalence established / indeterminate / refuted):

- **2.5 pp**: 0 established, 18 indeterminate, 0 refuted.
- **5.0 pp**: 9 established, 9 indeterminate, 0 refuted.
- **10.0 pp**: 16 established, 2 indeterminate, 0 refuted.

Sensitivity to the interval level and to the estimator. The verdicts above use the 90% intervals, which is the level that corresponds to a TOST at 5%. Counting instead by containment of a single estimator's interval, over the same 18 loose binary cells:

| interval | 2.5 pp | 5 pp | 10 pp |
| --- | ---: | ---: | ---: |
| 90% bootstrap | 4/18 | 9/18 | 16/18 |
| 95% bootstrap | 4/18 | 8/18 | 15/18 |
| 90% Newcombe | 0/18 | 9/18 | 16/18 |
| 95% Newcombe | 0/18 | 4/18 | 14/18 |
| 90% cluster bootstrap | 4/18 | 12/18 | 16/18 |

No cell is *refuted* at any margin at the loose budget: the sample is never large enough to affirm a difference as big as 2.5 pp. At the tight budget, by contrast, 8 of 18 cells are refuted at 5 pp, which is the availability effect the manuscript already reports.

The verdict rule is conservative on purpose: a cell counts as equivalent only if the 90% bootstrap interval, the 90% Newcombe interval and the 90% cluster-bootstrap interval all lie inside the margin. Four loose cells have no discordant pair at all, so their item bootstrap degenerates to the single point 0 and would declare equivalence at any margin on its own; the Newcombe interval is what keeps those cells honest, and it is why they are indeterminate at 2.5 pp.

**The cells that do NOT reach equivalence at 10 pp.** Both are reported here rather than absorbed into the null, and they do not agree on which architecture is ahead:

- **qwen27b / catch** (higher is better): risk difference -7.3 pp, 90% bootstrap CI [-13.5, -1.0] pp, 90% Newcombe CI [-13.8, -1.2] pp, 90% cluster CI [-13.3, -1.1] pp. MULTI-G has the higher rate on this outcome, and because higher is better on this outcome the difference favours **MULTI-G**.
- **deepseek / passthrough** (lower is better): risk difference -6.2 pp, 90% bootstrap CI [-12.5, +0.0] pp, 90% Newcombe CI [-12.9, +0.1] pp, 90% cluster CI [-13.1, +0.0] pp. MULTI-G has the higher rate on this outcome, and because lower is better on this outcome the difference favours **SINGLE+G**.

A sign convention warning for anyone reading these two cells side by side: both risk differences are negative, so MULTI-G has the higher rate on both, but a higher catch rate is good and a higher pass-through rate is bad. The two cells therefore point in opposite directions on which architecture is ahead, and neither dominates.

