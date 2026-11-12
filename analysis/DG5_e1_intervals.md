<!-- generated 2026-08-17 17:34:15 +0800 by code/scripts/e1_intervals.py (l1-dg5-intervals-1) -->
<!-- sources: results/e1_eval_qwen14b/verdicts_G_CERT.jsonl sha256 007f9b7e128b9b40; results/e1_eval_qwen14b/verdicts_G_FEAS.jsonl sha256 2e35dedecb936343; results/e1_eval_qwen14b/proposals.jsonl sha256 1275be52a6a9e7cc; results/e1_eval_qwen27b/verdicts_G_CERT.jsonl sha256 34f6a4c8b2b26b38; results/e1_eval_qwen27b/verdicts_G_FEAS.jsonl sha256 5741e6c174e36e8d; results/e1_eval_qwen27b/proposals.jsonl sha256 7d930c7633af776c; results/e1_eval_glm9b/verdicts_G_CERT.jsonl sha256 357ff6582097bd5c; results/e1_eval_glm9b/verdicts_G_FEAS.jsonl sha256 c6aa59cb041ee235; results/e1_eval_glm9b/proposals.jsonl sha256 94f9457a32e8776c; results/e1_eval_gpt54mini/verdicts_G_CERT.jsonl sha256 ab58fe9be34e9757; results/e1_eval_gpt54mini/verdicts_G_FEAS.jsonl sha256 0b54b9a910824885; results/e1_eval_gpt54mini/proposals.jsonl sha256 cbfcbd608fa2b03f; results/e1_eval_deepseek/verdicts_G_CERT.jsonl sha256 5c03ca0b5ae739bd; results/e1_eval_deepseek/verdicts_G_FEAS.jsonl sha256 418eaa3f06de2f41; results/e1_eval_deepseek/proposals.jsonl sha256 1e6cef4120af866d; results/e1_eval_sonnet5/verdicts_G_CERT.jsonl sha256 87d3ebaefefe7b70; results/e1_eval_sonnet5/verdicts_G_FEAS.jsonl sha256 4b25bfa946e1f6a8; results/e1_eval_sonnet5/proposals.jsonl sha256 0a1387c342b1b9d5; results/e1_eval_opus5/verdicts_G_CERT.jsonl sha256 2c4a3d99410ce0bc; results/e1_eval_opus5/verdicts_G_FEAS.jsonl sha256 2e3f20d17f1a24f3; results/e1_eval_opus5/proposals.jsonl sha256 170c6b315c419a23; results/e1_eval_sol/verdicts_G_CERT.jsonl sha256 3a06dbde336b0595; results/e1_eval_sol/verdicts_G_FEAS.jsonl sha256 e2436e281abdbd80; results/e1_eval_sol/proposals.jsonl sha256 d1717574dc936577; code/suite/v0.2/suite.jsonl sha256 0a0b471f4d04ba03; analysis/T3_guard_value_curve.csv sha256 e9bf87e3856515e7; analysis/T1_e1_main.csv sha256 8439dadb9dc81c40 -->

# DG5. Cluster-bootstrap intervals on the E1 headline rates

All rates are pooled over repeats in constrained mode, exactly as in `analysis/T3_guard_value_curve.csv`. The interval is a nonparametric cluster bootstrap of the pooled ratio: clusters are drawn with replacement, each drawn cluster contributes all of its rows, and the statistic is the resampled numerator over the resampled denominator. B = 20000 replicates, 2.5/97.5 percentile, fixed seed. The Wilson column is the naive interval that treats rows as independent. The design effect is the squared ratio of the two widths.

**Self-check.** Recomputed from the raw verdict logs before anything else: opus/default V3 separation 398/440 and opus/default benign false block under G_CERT 63/1600, both exactly matching `manuscript/macros.tex` (`\eOneVThreeSepOpus` 90.5%, `\eOneFalseBlockOpus` 3.9%). Every cell's point estimate for the eight published metrics was then re-derived and checked against `analysis/T3_guard_value_curve.csv` (seven of them) and `analysis/T1_e1_main.csv` (the V3 block rate under G_FEAS) to 5e-7; all 80 comparisons matched.

**Reading the design effect.** A value above 1 means the clustered interval is wider than the naive one, and the ratio is how many times more independent rows the naive interval pretends to have. A value below 1 appears where the per-instance rates are homogeneous: the cluster bootstrap holds each instance's rows fixed and resamples only instances, so it charges no within-instance sampling variance, and with a balanced design it can be narrower than a binomial interval. Degenerate cells (0/440, 440/440) give a zero-width interval and no usable design effect.

**Monte-Carlo stability at B = 20000.** Repeating the flagship (opus / default) bootstrap under eight further seeds moves the endpoints by:

| metric | lower endpoint across 8 seeds | upper endpoint across 8 seeds |
|---|---|---|
| benign_false_block_gcert | 0.99% to 1.03% | 8.05% to 8.20% |
| v3_separation | 85.10% to 85.25% | 94.86% to 94.98% |

So an endpoint is trustworthy to about a tenth of a percentage point at this B. Quote endpoints rounded outward if a stated interval must be conservative.

## V3 separation (G_FEAS applies, G_CERT blocks)

Cluster = instance (primary).

| arm / thinking | k/n | point % | 95% CI (instance-clustered) | 95% Wilson (naive) | design effect |
|---|---|---|---|---|---|
| qwen3-14b / - | 543/660 | 82.3 | 75.8 to 87.8 | 79.2 to 85.0 | 4.23 |
| qwen3.6-27b-fp8 / - | 574/660 | 87.0 | 81.1 to 92.1 | 84.2 to 89.3 | 4.58 |
| glm-4-9b / - | 160/220 | 72.7 | 66.2 to 78.6 | 66.5 to 78.2 | 1.13 |
| openai / - | 347/440 | 78.9 | 72.3 to 84.7 | 74.8 to 82.4 | 2.66 |
| deepseek / non_think | 1/440 | 0.2 | 0.0 to 0.7 | 0.0 to 1.3 | 0.36 |
| deepseek / think_high | 0/440 | 0.0 | 0.0 to 0.0 | 0.0 to 0.9 | 0.00 |
| sonnet / disabled | 378/440 | 85.9 | 79.6 to 91.4 | 82.3 to 88.9 | 3.29 |
| opus / default | 398/440 | 90.5 | 85.2 to 95.0 | 87.3 to 92.9 | 3.13 |
| opus / disabled | 396/440 | 90.0 | 84.6 to 94.6 | 86.8 to 92.5 | 3.20 |
| sol / none | 181/220 | 82.3 | 75.2 to 88.2 | 76.7 to 86.8 | 1.65 |

Sensitivity to the cluster definition (capability set only):

| arm / thinking | by instance | by item | by (instance, family) |
|---|---|---|---|
| qwen3-14b / - | 75.8 to 87.8 (K=56) | 77.3 to 87.3 (K=220) | 76.8 to 87.3 (K=185) |
| qwen3.6-27b-fp8 / - | 81.1 to 92.1 (K=56) | 82.4 to 91.2 (K=220) | 82.1 to 91.4 (K=185) |
| glm-4-9b / - | 66.2 to 78.6 (K=56) | 66.8 to 78.6 (K=220) | 66.7 to 78.5 (K=185) |
| openai / - | 72.3 to 84.7 (K=56) | 73.4 to 84.1 (K=220) | 73.3 to 84.1 (K=185) |
| sonnet / disabled | 79.6 to 91.4 (K=56) | 81.1 to 90.2 (K=220) | 80.9 to 90.6 (K=185) |
| opus / default | 85.2 to 95.0 (K=56) | 86.4 to 94.1 (K=220) | 86.2 to 94.2 (K=185) |
| opus / disabled | 84.6 to 94.6 (K=56) | 85.9 to 93.6 (K=220) | 85.6 to 93.9 (K=185) |
| sol / none | 75.2 to 88.2 (K=56) | 77.3 to 87.3 (K=220) | 76.7 to 87.5 (K=185) |

## V3 block rate under G_CERT

Cluster = instance (primary).

| arm / thinking | k/n | point % | 95% CI (instance-clustered) | 95% Wilson (naive) | design effect |
|---|---|---|---|---|---|
| qwen3-14b / - | 546/660 | 82.7 | 76.2 to 88.4 | 79.7 to 85.4 | 4.48 |
| qwen3.6-27b-fp8 / - | 577/660 | 87.4 | 81.4 to 92.6 | 84.7 to 89.7 | 4.85 |
| glm-4-9b / - | 166/220 | 75.5 | 68.7 to 81.5 | 69.4 to 80.7 | 1.28 |
| openai / - | 349/440 | 79.3 | 72.8 to 85.2 | 75.3 to 82.8 | 2.70 |
| deepseek / non_think | 438/440 | 99.5 | 98.5 to 100.0 | 98.4 to 99.9 | 0.96 |
| deepseek / think_high | 440/440 | 100.0 | 100.0 to 100.0 | 99.1 to 100.0 | 0.00 |
| sonnet / disabled | 380/440 | 86.4 | 80.2 to 91.7 | 82.8 to 89.3 | 3.22 |
| opus / default | 398/440 | 90.5 | 85.2 to 94.9 | 87.3 to 92.9 | 3.07 |
| opus / disabled | 396/440 | 90.0 | 84.5 to 94.6 | 86.8 to 92.5 | 3.23 |
| sol / none | 194/220 | 88.2 | 82.4 to 93.2 | 83.2 to 91.8 | 1.59 |

Sensitivity to the cluster definition (capability set only):

| arm / thinking | by instance | by item | by (instance, family) |
|---|---|---|---|
| qwen3-14b / - | 76.2 to 88.4 (K=56) | 77.7 to 87.7 (K=220) | 77.3 to 87.7 (K=185) |
| qwen3.6-27b-fp8 / - | 81.4 to 92.6 (K=56) | 82.9 to 91.5 (K=220) | 82.6 to 91.8 (K=185) |
| glm-4-9b / - | 68.7 to 81.5 (K=56) | 69.5 to 80.9 (K=220) | 69.5 to 81.1 (K=185) |
| openai / - | 72.8 to 85.2 (K=56) | 74.1 to 84.5 (K=220) | 73.7 to 84.6 (K=185) |
| sonnet / disabled | 80.2 to 91.7 (K=56) | 81.8 to 90.7 (K=220) | 81.4 to 90.9 (K=185) |
| opus / default | 85.2 to 94.9 (K=56) | 86.4 to 94.1 (K=220) | 86.1 to 94.3 (K=185) |
| opus / disabled | 84.5 to 94.6 (K=56) | 85.9 to 93.9 (K=220) | 85.7 to 93.9 (K=185) |
| sol / none | 82.4 to 93.2 (K=56) | 83.6 to 92.3 (K=220) | 83.4 to 92.4 (K=185) |

## V3 block rate under G_FEAS

Cluster = instance (primary).

| arm / thinking | k/n | point % | 95% CI (instance-clustered) | 95% Wilson (naive) | design effect |
|---|---|---|---|---|---|
| qwen3-14b / - | 3/660 | 0.5 | 0.0 to 1.4 | 0.2 to 1.3 | 1.44 |
| qwen3.6-27b-fp8 / - | 3/660 | 0.5 | 0.0 to 1.5 | 0.2 to 1.3 | 1.56 |
| glm-4-9b / - | 6/220 | 2.7 | 0.9 to 5.0 | 1.3 to 5.8 | 0.82 |
| openai / - | 2/440 | 0.5 | 0.0 to 1.5 | 0.1 to 1.6 | 0.92 |
| deepseek / non_think | 437/440 | 99.3 | 98.2 to 100.0 | 98.0 to 99.8 | 1.07 |
| deepseek / think_high | 440/440 | 100.0 | 100.0 to 100.0 | 99.1 to 100.0 | 0.00 |
| sonnet / disabled | 2/440 | 0.5 | 0.0 to 1.5 | 0.1 to 1.6 | 0.93 |
| opus / default | 0/440 | 0.0 | 0.0 to 0.0 | 0.0 to 0.9 | 0.00 |
| opus / disabled | 0/440 | 0.0 | 0.0 to 0.0 | 0.0 to 0.9 | 0.00 |
| sol / none | 13/220 | 5.9 | 3.0 to 9.2 | 3.5 to 9.8 | 0.94 |

Sensitivity to the cluster definition (capability set only):

| arm / thinking | by instance | by item | by (instance, family) |
|---|---|---|---|
| qwen3-14b / - | 0.0 to 1.4 (K=56) | 0.0 to 1.4 (K=220) | 0.0 to 1.4 (K=185) |
| qwen3.6-27b-fp8 / - | 0.0 to 1.5 (K=56) | 0.0 to 1.4 (K=220) | 0.0 to 1.4 (K=185) |
| glm-4-9b / - | 0.9 to 5.0 (K=56) | 0.9 to 5.0 (K=220) | 0.9 to 5.1 (K=185) |
| openai / - | 0.0 to 1.5 (K=56) | 0.0 to 1.4 (K=220) | 0.0 to 1.4 (K=185) |
| sonnet / disabled | 0.0 to 1.5 (K=56) | 0.0 to 1.4 (K=220) | 0.0 to 1.4 (K=185) |
| opus / default | 0.0 to 0.0 (K=56) | 0.0 to 0.0 (K=220) | 0.0 to 0.0 (K=185) |
| opus / disabled | 0.0 to 0.0 (K=56) | 0.0 to 0.0 (K=220) | 0.0 to 0.0 (K=185) |
| sol / none | 3.0 to 9.2 (K=56) | 3.2 to 9.1 (K=220) | 2.8 to 9.5 (K=185) |

## Benign false block under G_CERT

Cluster = instance (primary).

| arm / thinking | k/n | point % | 95% CI (instance-clustered) | 95% Wilson (naive) | design effect |
|---|---|---|---|---|---|
| qwen3-14b / - | 105/2400 | 4.4 | 1.2 to 8.7 | 3.6 to 5.3 | 21.12 |
| qwen3.6-27b-fp8 / - | 132/2400 | 5.5 | 2.6 to 9.6 | 4.7 to 6.5 | 14.91 |
| glm-4-9b / - | 64/800 | 8.0 | 4.8 to 12.3 | 6.3 to 10.1 | 4.01 |
| openai / - | 62/1600 | 3.9 | 1.0 to 8.0 | 3.0 to 4.9 | 13.69 |
| deepseek / non_think | 1555/1600 | 97.2 | 96.3 to 98.1 | 96.3 to 97.9 | 1.23 |
| deepseek / think_high | 1591/1600 | 99.4 | 99.0 to 99.8 | 98.9 to 99.7 | 1.24 |
| sonnet / disabled | 61/1600 | 3.8 | 0.9 to 8.0 | 3.0 to 4.9 | 14.11 |
| opus / default | 63/1600 | 3.9 | 1.0 to 8.1 | 3.1 to 5.0 | 13.72 |
| opus / disabled | 80/1600 | 5.0 | 2.1 to 9.1 | 4.0 to 6.2 | 10.90 |
| sol / none | 69/800 | 8.6 | 5.3 to 12.9 | 6.9 to 10.8 | 3.87 |

Sensitivity to the cluster definition (capability set only):

| arm / thinking | by instance | by item | by (instance, family) |
|---|---|---|---|
| qwen3-14b / - | 1.2 to 8.7 (K=60) | 3.0 to 5.9 (K=800) | 3.0 to 5.8 (K=730) |
| qwen3.6-27b-fp8 / - | 2.6 to 9.6 (K=60) | 4.0 to 7.1 (K=800) | 4.0 to 7.2 (K=730) |
| glm-4-9b / - | 4.8 to 12.3 (K=60) | 6.2 to 9.9 (K=800) | 6.1 to 10.0 (K=730) |
| openai / - | 1.0 to 8.0 (K=60) | 2.6 to 5.2 (K=800) | 2.6 to 5.3 (K=730) |
| sonnet / disabled | 0.9 to 8.0 (K=60) | 2.6 to 5.1 (K=800) | 2.6 to 5.2 (K=730) |
| opus / default | 1.0 to 8.1 (K=60) | 2.7 to 5.3 (K=800) | 2.6 to 5.4 (K=730) |
| opus / disabled | 2.1 to 9.1 (K=60) | 3.6 to 6.5 (K=800) | 3.5 to 6.6 (K=730) |
| sol / none | 5.3 to 12.9 (K=60) | 6.8 to 10.6 (K=800) | 6.7 to 10.7 (K=730) |

## Benign false block under G_FEAS

Cluster = instance (primary).

| arm / thinking | k/n | point % | 95% CI (instance-clustered) | 95% Wilson (naive) | design effect |
|---|---|---|---|---|---|
| qwen3-14b / - | 6/2400 | 0.2 | 0.0 to 0.6 | 0.1 to 0.5 | 2.16 |
| qwen3.6-27b-fp8 / - | 69/2400 | 2.9 | 2.0 to 3.8 | 2.3 to 3.6 | 1.78 |
| glm-4-9b / - | 43/800 | 5.4 | 4.0 to 6.8 | 4.0 to 7.2 | 0.80 |
| openai / - | 20/1600 | 1.2 | 0.6 to 2.0 | 0.8 to 1.9 | 1.47 |
| deepseek / non_think | 1553/1600 | 97.1 | 96.1 to 98.0 | 96.1 to 97.8 | 1.21 |
| deepseek / think_high | 1591/1600 | 99.4 | 99.0 to 99.8 | 98.9 to 99.7 | 1.23 |
| sonnet / disabled | 19/1600 | 1.2 | 0.5 to 1.9 | 0.8 to 1.8 | 1.50 |
| opus / default | 21/1600 | 1.3 | 0.6 to 2.1 | 0.9 to 2.0 | 1.68 |
| opus / disabled | 38/1600 | 2.4 | 1.5 to 3.2 | 1.7 to 3.2 | 1.29 |
| sol / none | 48/800 | 6.0 | 4.2 to 8.0 | 4.6 to 7.9 | 1.30 |

Sensitivity to the cluster definition (capability set only):

| arm / thinking | by instance | by item | by (instance, family) |
|---|---|---|---|
| qwen3-14b / - | 0.0 to 0.6 (K=60) | 0.0 to 0.6 (K=800) | 0.0 to 0.6 (K=730) |
| qwen3.6-27b-fp8 / - | 2.0 to 3.8 (K=60) | 1.8 to 4.0 (K=800) | 1.8 to 4.1 (K=730) |
| glm-4-9b / - | 4.0 to 6.8 (K=60) | 3.9 to 7.0 (K=800) | 3.8 to 7.1 (K=730) |
| openai / - | 0.6 to 2.0 (K=60) | 0.6 to 2.0 (K=800) | 0.6 to 2.1 (K=730) |
| sonnet / disabled | 0.5 to 1.9 (K=60) | 0.6 to 1.9 (K=800) | 0.5 to 2.0 (K=730) |
| opus / default | 0.6 to 2.1 (K=60) | 0.6 to 2.1 (K=800) | 0.6 to 2.2 (K=730) |
| opus / disabled | 1.5 to 3.2 (K=60) | 1.4 to 3.4 (K=800) | 1.4 to 3.5 (K=730) |
| sol / none | 4.2 to 8.0 (K=60) | 4.4 to 7.6 (K=800) | 4.3 to 7.8 (K=730) |

## V4 block rate under G_CERT

Cluster = instance (primary).

| arm / thinking | k/n | point % | 95% CI (instance-clustered) | 95% Wilson (naive) | design effect |
|---|---|---|---|---|---|
| qwen3-14b / - | 40/660 | 6.1 | 2.4 to 10.7 | 4.5 to 8.1 | 5.18 |
| qwen3.6-27b-fp8 / - | 18/660 | 2.7 | 0.0 to 7.0 | 1.7 to 4.3 | 7.70 |
| glm-4-9b / - | 9/220 | 4.1 | 0.8 to 8.7 | 2.2 to 7.6 | 2.10 |
| openai / - | 13/440 | 3.0 | 0.0 to 7.3 | 1.7 to 5.0 | 5.01 |
| deepseek / non_think | 411/440 | 93.4 | 89.6 to 96.8 | 90.7 to 95.4 | 2.35 |
| deepseek / think_high | 436/440 | 99.1 | 98.0 to 100.0 | 97.7 to 99.6 | 1.09 |
| sonnet / disabled | 12/440 | 2.7 | 0.0 to 7.1 | 1.6 to 4.7 | 5.08 |
| opus / default | 12/440 | 2.7 | 0.0 to 7.1 | 1.6 to 4.7 | 5.08 |
| opus / disabled | 12/440 | 2.7 | 0.0 to 7.1 | 1.6 to 4.7 | 5.18 |
| sol / none | 17/220 | 7.7 | 3.7 to 12.7 | 4.9 to 12.0 | 1.57 |

Sensitivity to the cluster definition (capability set only):

| arm / thinking | by instance | by item | by (instance, family) |
|---|---|---|---|
| qwen3-14b / - | 2.4 to 10.7 (K=60) | 3.2 to 9.4 (K=220) | 3.2 to 9.4 (K=208) |
| qwen3.6-27b-fp8 / - | 0.0 to 7.0 (K=60) | 0.9 to 5.0 (K=220) | 0.9 to 5.0 (K=208) |
| glm-4-9b / - | 0.8 to 8.7 (K=60) | 1.8 to 6.8 (K=220) | 1.8 to 6.9 (K=208) |
| openai / - | 0.0 to 7.3 (K=60) | 0.9 to 5.2 (K=220) | 0.9 to 5.3 (K=208) |
| sonnet / disabled | 0.0 to 7.1 (K=60) | 0.9 to 5.0 (K=220) | 0.9 to 5.1 (K=208) |
| opus / default | 0.0 to 7.1 (K=60) | 0.9 to 5.0 (K=220) | 0.9 to 5.0 (K=208) |
| opus / disabled | 0.0 to 7.1 (K=60) | 0.9 to 5.0 (K=220) | 0.9 to 5.0 (K=208) |
| sol / none | 3.7 to 12.7 (K=60) | 4.5 to 11.4 (K=220) | 4.4 to 11.4 (K=208) |

## V5 block rate under G_CERT

Cluster = instance (primary).

| arm / thinking | k/n | point % | 95% CI (instance-clustered) | 95% Wilson (naive) | design effect |
|---|---|---|---|---|---|
| qwen3-14b / - | 42/600 | 7.0 | 2.3 to 13.0 | 5.2 to 9.3 | 6.84 |
| qwen3.6-27b-fp8 / - | 24/600 | 4.0 | 0.2 to 9.7 | 2.7 to 5.9 | 9.02 |
| glm-4-9b / - | 39/200 | 19.5 | 14.8 to 24.5 | 14.6 to 25.5 | 0.80 |
| openai / - | 71/400 | 17.8 | 12.8 to 23.4 | 14.3 to 21.8 | 2.00 |
| deepseek / non_think | 26/400 | 6.5 | 2.0 to 12.2 | 4.5 to 9.4 | 4.35 |
| deepseek / think_high | 91/400 | 22.8 | 17.3 to 28.9 | 18.9 to 27.1 | 1.99 |
| sonnet / disabled | 14/400 | 3.5 | 0.0 to 9.1 | 2.1 to 5.8 | 6.06 |
| opus / default | 14/400 | 3.5 | 0.0 to 9.1 | 2.1 to 5.8 | 6.01 |
| opus / disabled | 14/400 | 3.5 | 0.0 to 9.2 | 2.1 to 5.8 | 6.17 |
| sol / none | 7/200 | 3.5 | 0.0 to 9.2 | 1.7 to 7.0 | 2.99 |

Sensitivity to the cluster definition (capability set only):

| arm / thinking | by instance | by item | by (instance, family) |
|---|---|---|---|
| qwen3-14b / - | 2.3 to 13.0 (K=60) | 3.5 to 10.5 (K=200) | 3.5 to 10.7 (K=187) |
| qwen3.6-27b-fp8 / - | 0.2 to 9.7 (K=60) | 1.7 to 6.8 (K=200) | 1.5 to 6.9 (K=187) |
| glm-4-9b / - | 14.8 to 24.5 (K=60) | 14.0 to 25.0 (K=200) | 14.0 to 25.1 (K=187) |
| openai / - | 12.8 to 23.4 (K=60) | 13.0 to 22.8 (K=200) | 12.8 to 23.1 (K=187) |
| sonnet / disabled | 0.0 to 9.1 (K=60) | 1.0 to 6.0 (K=200) | 1.0 to 6.3 (K=187) |
| opus / default | 0.0 to 9.1 (K=60) | 1.0 to 6.0 (K=200) | 1.0 to 6.2 (K=187) |
| opus / disabled | 0.0 to 9.2 (K=60) | 1.0 to 6.0 (K=200) | 1.0 to 6.2 (K=187) |
| sol / none | 0.0 to 9.2 (K=60) | 1.0 to 6.5 (K=200) | 1.0 to 6.2 (K=187) |

## V6 block rate under G_CERT

Cluster = instance (primary).

| arm / thinking | k/n | point % | 95% CI (instance-clustered) | 95% Wilson (naive) | design effect |
|---|---|---|---|---|---|
| qwen3-14b / - | 72/600 | 12.0 | 7.3 to 17.3 | 9.6 to 14.8 | 3.67 |
| qwen3.6-27b-fp8 / - | 30/600 | 5.0 | 1.2 to 9.9 | 3.5 to 7.0 | 6.16 |
| glm-4-9b / - | 28/200 | 14.0 | 9.0 to 19.4 | 9.9 to 19.5 | 1.15 |
| openai / - | 19/400 | 4.8 | 1.0 to 9.6 | 3.1 to 7.3 | 4.05 |
| deepseek / non_think | 338/400 | 84.5 | 77.9 to 90.7 | 80.6 to 87.7 | 3.25 |
| deepseek / think_high | 365/400 | 91.2 | 88.2 to 94.1 | 88.1 to 93.6 | 1.15 |
| sonnet / disabled | 13/400 | 3.2 | 0.0 to 8.0 | 1.9 to 5.5 | 5.00 |
| opus / default | 12/400 | 3.0 | 0.0 to 7.7 | 1.7 to 5.2 | 4.93 |
| opus / disabled | 12/400 | 3.0 | 0.0 to 7.6 | 1.7 to 5.2 | 4.88 |
| sol / none | 6/200 | 3.0 | 0.0 to 7.7 | 1.4 to 6.4 | 2.34 |

Sensitivity to the cluster definition (capability set only):

| arm / thinking | by instance | by item | by (instance, family) |
|---|---|---|---|
| qwen3-14b / - | 7.3 to 17.3 (K=60) | 8.0 to 16.5 (K=200) | 7.6 to 16.7 (K=193) |
| qwen3.6-27b-fp8 / - | 1.2 to 9.9 (K=60) | 2.2 to 8.2 (K=200) | 2.3 to 8.1 (K=193) |
| glm-4-9b / - | 9.0 to 19.4 (K=60) | 9.5 to 19.0 (K=200) | 9.3 to 19.1 (K=193) |
| openai / - | 1.0 to 9.6 (K=60) | 2.0 to 7.8 (K=200) | 2.0 to 7.9 (K=193) |
| sonnet / disabled | 0.0 to 8.0 (K=60) | 1.0 to 6.0 (K=200) | 1.0 to 5.8 (K=193) |
| opus / default | 0.0 to 7.7 (K=60) | 1.0 to 5.5 (K=200) | 1.0 to 5.6 (K=193) |
| opus / disabled | 0.0 to 7.6 (K=60) | 1.0 to 5.5 (K=200) | 1.0 to 5.6 (K=193) |
| sol / none | 0.0 to 7.7 (K=60) | 1.0 to 5.5 (K=200) | 1.0 to 5.5 (K=193) |

## Violation pass-through under G_CERT

Cluster = instance (primary).

| arm / thinking | k/n | point % | 95% CI (instance-clustered) | 95% Wilson (naive) | design effect |
|---|---|---|---|---|---|
| qwen3-14b / - | 2188/3600 | 60.8 | 57.4 to 63.7 | 59.2 to 62.4 | 3.98 |
| qwen3.6-27b-fp8 / - | 2245/3600 | 62.4 | 59.0 to 65.1 | 60.8 to 63.9 | 3.66 |
| glm-4-9b / - | 691/1200 | 57.6 | 54.3 to 60.7 | 54.8 to 60.4 | 1.34 |
| openai / - | 1460/2400 | 60.8 | 57.5 to 63.7 | 58.9 to 62.8 | 2.55 |
| deepseek / non_think | 701/2400 | 29.2 | 26.5 to 31.8 | 27.4 to 31.1 | 2.09 |
| deepseek / think_high | 554/2400 | 23.1 | 20.7 to 25.3 | 21.4 to 24.8 | 1.81 |
| sonnet / disabled | 1636/2400 | 68.2 | 64.5 to 71.1 | 66.3 to 70.0 | 3.16 |
| opus / default | 1854/2400 | 77.2 | 73.1 to 80.6 | 75.5 to 78.9 | 4.92 |
| opus / disabled | 1728/2400 | 72.0 | 68.2 to 75.1 | 70.2 to 73.8 | 3.67 |
| sol / none | 874/1200 | 72.8 | 68.8 to 76.3 | 70.2 to 75.3 | 2.25 |

Sensitivity to the cluster definition (capability set only):

| arm / thinking | by instance | by item | by (instance, family) |
|---|---|---|---|
| qwen3-14b / - | 57.4 to 63.7 (K=60) | 58.0 to 63.5 (K=1200) | 57.8 to 63.8 (K=1110) |
| qwen3.6-27b-fp8 / - | 59.0 to 65.1 (K=60) | 59.6 to 65.1 (K=1200) | 59.4 to 65.3 (K=1110) |
| glm-4-9b / - | 54.3 to 60.7 (K=60) | 54.8 to 60.4 (K=1200) | 54.6 to 60.6 (K=1110) |
| openai / - | 57.5 to 63.7 (K=60) | 58.2 to 63.6 (K=1200) | 57.9 to 63.7 (K=1110) |
| sonnet / disabled | 64.5 to 71.1 (K=60) | 65.5 to 70.8 (K=1200) | 65.4 to 71.0 (K=1110) |
| opus / default | 73.1 to 80.6 (K=60) | 74.9 to 79.6 (K=1200) | 74.6 to 79.8 (K=1110) |
| opus / disabled | 68.2 to 75.1 (K=60) | 69.5 to 74.5 (K=1200) | 69.2 to 74.7 (K=1110) |
| sol / none | 68.8 to 76.3 (K=60) | 70.3 to 75.3 (K=1200) | 70.0 to 75.6 (K=1110) |

## Violation pass-through under G_FEAS

Cluster = instance (primary).

| arm / thinking | k/n | point % | 95% CI (instance-clustered) | 95% Wilson (naive) | design effect |
|---|---|---|---|---|---|
| qwen3-14b / - | 2848/3600 | 79.1 | 77.2 to 81.0 | 77.8 to 80.4 | 2.07 |
| qwen3.6-27b-fp8 / - | 2888/3600 | 80.2 | 78.6 to 81.8 | 78.9 to 81.5 | 1.53 |
| glm-4-9b / - | 878/1200 | 73.2 | 70.8 to 75.6 | 70.6 to 75.6 | 0.90 |
| openai / - | 1856/2400 | 77.3 | 75.3 to 79.4 | 75.6 to 79.0 | 1.51 |
| deepseek / non_think | 722/2400 | 30.1 | 27.8 to 32.3 | 28.3 to 31.9 | 1.54 |
| deepseek / think_high | 571/2400 | 23.8 | 21.8 to 25.7 | 22.1 to 25.5 | 1.33 |
| sonnet / disabled | 2061/2400 | 85.9 | 84.5 to 87.2 | 84.4 to 87.2 | 0.92 |
| opus / default | 2305/2400 | 96.0 | 95.2 to 96.9 | 95.2 to 96.8 | 1.16 |
| opus / disabled | 2176/2400 | 90.7 | 89.4 to 91.9 | 89.4 to 91.8 | 1.15 |
| sol / none | 1083/1200 | 90.2 | 88.9 to 91.5 | 88.4 to 91.8 | 0.60 |

Sensitivity to the cluster definition (capability set only):

| arm / thinking | by instance | by item | by (instance, family) |
|---|---|---|---|
| qwen3-14b / - | 77.2 to 81.0 (K=60) | 76.8 to 81.4 (K=1200) | 76.7 to 81.5 (K=1110) |
| qwen3.6-27b-fp8 / - | 78.6 to 81.8 (K=60) | 77.9 to 82.4 (K=1200) | 77.9 to 82.5 (K=1110) |
| glm-4-9b / - | 70.8 to 75.6 (K=60) | 70.7 to 75.7 (K=1200) | 70.5 to 75.8 (K=1110) |
| openai / - | 75.3 to 79.4 (K=60) | 75.0 to 79.7 (K=1200) | 74.8 to 79.7 (K=1110) |
| sonnet / disabled | 84.5 to 87.2 (K=60) | 83.9 to 87.8 (K=1200) | 83.9 to 87.8 (K=1110) |
| opus / default | 95.2 to 96.9 (K=60) | 95.0 to 97.0 (K=1200) | 95.0 to 97.1 (K=1110) |
| opus / disabled | 89.4 to 91.9 (K=60) | 89.0 to 92.2 (K=1200) | 89.0 to 92.3 (K=1110) |
| sol / none | 88.9 to 91.5 (K=60) | 88.6 to 91.9 (K=1200) | 88.5 to 91.9 (K=1110) |

## Violation pass-through under G_CERT, V4/V6 content rule

Cluster = instance (primary).

| arm / thinking | k/n | point % | 95% CI (instance-clustered) | 95% Wilson (naive) | design effect |
|---|---|---|---|---|---|
| qwen3-14b / - | 1749/3600 | 48.6 | 45.3 to 51.7 | 47.0 to 50.2 | 3.90 |
| qwen3.6-27b-fp8 / - | 1658/3600 | 46.1 | 43.0 to 48.9 | 44.4 to 47.7 | 3.34 |
| glm-4-9b / - | 576/1200 | 48.0 | 45.0 to 50.9 | 45.2 to 50.8 | 1.08 |
| openai / - | 1099/2400 | 45.8 | 43.1 to 48.3 | 43.8 to 47.8 | 1.70 |
| deepseek / non_think | 701/2400 | 29.2 | 26.5 to 31.8 | 27.4 to 31.1 | 2.09 |
| deepseek / think_high | 554/2400 | 23.1 | 20.8 to 25.2 | 21.4 to 24.8 | 1.76 |
| sonnet / disabled | 1162/2400 | 48.4 | 45.2 to 51.4 | 46.4 to 50.4 | 2.37 |
| opus / default | 1361/2400 | 56.7 | 53.1 to 60.0 | 54.7 to 58.7 | 3.00 |
| opus / disabled | 1253/2400 | 52.2 | 48.9 to 55.2 | 50.2 to 54.2 | 2.47 |
| sol / none | 640/1200 | 53.3 | 49.8 to 56.6 | 50.5 to 56.1 | 1.45 |

Sensitivity to the cluster definition (capability set only):

| arm / thinking | by instance | by item | by (instance, family) |
|---|---|---|---|
| qwen3-14b / - | 45.3 to 51.7 (K=60) | 45.7 to 51.4 (K=1200) | 45.6 to 51.6 (K=1110) |
| qwen3.6-27b-fp8 / - | 43.0 to 48.9 (K=60) | 43.3 to 48.9 (K=1200) | 43.1 to 49.0 (K=1110) |
| glm-4-9b / - | 45.0 to 50.9 (K=60) | 45.2 to 50.9 (K=1200) | 45.0 to 51.0 (K=1110) |
| openai / - | 43.1 to 48.3 (K=60) | 43.0 to 48.6 (K=1200) | 42.9 to 48.7 (K=1110) |
| sonnet / disabled | 45.2 to 51.4 (K=60) | 45.7 to 51.2 (K=1200) | 45.5 to 51.4 (K=1110) |
| opus / default | 53.1 to 60.0 (K=60) | 54.0 to 59.5 (K=1200) | 53.7 to 59.7 (K=1110) |
| opus / disabled | 48.9 to 55.2 (K=60) | 49.4 to 55.0 (K=1200) | 49.2 to 55.2 (K=1110) |
| sol / none | 49.8 to 56.6 (K=60) | 50.4 to 56.2 (K=1200) | 50.3 to 56.4 (K=1110) |

## Violation pass-through under G_FEAS, V4/V6 content rule

Cluster = instance (primary).

| arm / thinking | k/n | point % | 95% CI (instance-clustered) | 95% Wilson (naive) | design effect |
|---|---|---|---|---|---|
| qwen3-14b / - | 2400/3600 | 66.7 | 64.6 to 68.7 | 65.1 to 68.2 | 1.81 |
| qwen3.6-27b-fp8 / - | 2286/3600 | 63.5 | 61.7 to 65.3 | 61.9 to 65.1 | 1.32 |
| glm-4-9b / - | 758/1200 | 63.2 | 61.0 to 65.3 | 60.4 to 65.8 | 0.62 |
| openai / - | 1483/2400 | 61.8 | 60.1 to 63.5 | 59.8 to 63.7 | 0.74 |
| deepseek / non_think | 722/2400 | 30.1 | 27.8 to 32.4 | 28.3 to 31.9 | 1.56 |
| deepseek / think_high | 571/2400 | 23.8 | 21.7 to 25.7 | 22.1 to 25.5 | 1.37 |
| sonnet / disabled | 1573/2400 | 65.5 | 63.8 to 67.2 | 63.6 to 67.4 | 0.77 |
| opus / default | 1796/2400 | 74.8 | 73.6 to 76.0 | 73.1 to 76.5 | 0.49 |
| opus / disabled | 1685/2400 | 70.2 | 68.6 to 71.8 | 68.3 to 72.0 | 0.77 |
| sol / none | 842/1200 | 70.2 | 68.5 to 71.8 | 67.5 to 72.7 | 0.42 |

Sensitivity to the cluster definition (capability set only):

| arm / thinking | by instance | by item | by (instance, family) |
|---|---|---|---|
| qwen3-14b / - | 64.6 to 68.7 (K=60) | 64.0 to 69.3 (K=1200) | 63.9 to 69.5 (K=1110) |
| qwen3.6-27b-fp8 / - | 61.7 to 65.3 (K=60) | 60.8 to 66.2 (K=1200) | 60.6 to 66.3 (K=1110) |
| glm-4-9b / - | 61.0 to 65.3 (K=60) | 60.4 to 65.8 (K=1200) | 60.2 to 66.0 (K=1110) |
| openai / - | 60.1 to 63.5 (K=60) | 59.1 to 64.5 (K=1200) | 58.9 to 64.6 (K=1110) |
| sonnet / disabled | 63.8 to 67.2 (K=60) | 62.9 to 68.2 (K=1200) | 62.8 to 68.3 (K=1110) |
| opus / default | 73.6 to 76.0 (K=60) | 72.5 to 77.2 (K=1200) | 72.2 to 77.3 (K=1110) |
| opus / disabled | 68.6 to 71.8 (K=60) | 67.6 to 72.7 (K=1200) | 67.5 to 72.8 (K=1110) |
| sol / none | 68.5 to 71.8 (K=60) | 67.6 to 72.8 (K=1200) | 67.4 to 72.8 (K=1110) |

## The ranges the manuscript prints, endpoint by endpoint

Each row is one range macro pair in `manuscript/macros.tex`, evaluated over the eight-cell capability set. `separated` says whether the two endpoints' instance-clustered intervals are disjoint: if they overlap, the spread the range advertises is not resolved by 60 instances.

An endpoint that several arms share to the printed precision is listed with all of them, because the macro names only one.

| range | metric | low endpoint | 95% CI | also at the low endpoint | high endpoint | 95% CI | also at the high endpoint | separated |
|---|---|---|---|---|---|---|---|---|
| `\eOneVThreeSepMin` to `\eOneVThreeSepMax` | v3_separation | 72.7% (glm-4-9b / -) | 66.2 to 78.6 | - | 90.5% (opus / default) | 85.2 to 95.0 | - | yes |
| `\eOneVThreeFeasBlockMin` to `\eOneVThreeFeasBlockMax` | v3_block_gfeas | 0.0% (opus / default) | 0.0 to 0.0 | opus / disabled | 5.9% (sol / none) | 3.0 to 9.2 | - | yes |
| `\eOneFalseBlockMin` to `\eOneFalseBlockMax` | benign_false_block_gcert | 3.8% (sonnet / disabled) | 0.9 to 8.0 | - | 8.6% (sol / none) | 5.3 to 12.9 | - | NO (intervals overlap) |
| `\eOneFalseBlockFeasMin` to `\eOneFalseBlockFeasMax` | benign_false_block_gfeas | 0.2% (qwen3-14b / -) | 0.0 to 0.6 | - | 6.0% (sol / none) | 4.2 to 8.0 | - | yes |
| `\eOneVFourBlockMin` to `\eOneVFourBlockMax` | v4_block_gcert | 2.7% (opus / default) | 0.0 to 7.1 | qwen3.6-27b-fp8 / -, sonnet / disabled, opus / disabled | 7.7% (sol / none) | 3.7 to 12.7 | - | NO (intervals overlap) |
| `\eOneVFiveBlockMin` to `\eOneVFiveBlockMax` | v5_block_gcert | 3.5% (opus / default) | 0.0 to 9.1 | sonnet / disabled, opus / disabled, sol / none | 19.5% (glm-4-9b / -) | 14.8 to 24.5 | - | yes |
| `\eOneVSixBlockMin` to `\eOneVSixBlockMax` | v6_block_gcert | 3.0% (opus / default) | 0.0 to 7.7 | opus / disabled, sol / none | 14.0% (glm-4-9b / -) | 9.0 to 19.4 | - | yes |

## Per-repeat spread (uneven pooling made visible)

| arm / thinking | repeats | V3 separation % | benign FB G_CERT % | benign FB G_FEAS % | violation pass-through G_CERT % |
|---|---|---|---|---|---|
| qwen3-14b / - | 3 | 82.3; 82.3; 82.3 | 4.5; 4.5; 4.1 | 0.2; 0.2; 0.2 | 60.8; 60.7; 60.8 |
| qwen3.6-27b-fp8 / - | 3 | 87.3; 86.8; 86.8 | 5.8; 5.4; 5.4 | 3.1; 2.8; 2.8 | 62.1; 62.5; 62.5 |
| glm-4-9b / - | 1 | 72.7 | 8.0 | 5.4 | 57.6 |
| openai / - | 2 | 78.2; 79.5 | 3.8; 4.0 | 1.1; 1.4 | 61.2; 60.5 |
| deepseek / non_think | 2 | 0.0; 0.5 | 97.1; 97.2 | 97.0; 97.1 | 29.2; 29.2 |
| deepseek / think_high | 2 | 0.0; 0.0 | 99.6; 99.2 | 99.6; 99.2 | 23.4; 22.8 |
| sonnet / disabled | 2 | 85.9; 85.9 | 3.9; 3.8 | 1.2; 1.1 | 68.1; 68.2 |
| opus / default | 2 | 90.5; 90.5 | 3.9; 4.0 | 1.2; 1.4 | 77.2; 77.3 |
| opus / disabled | 2 | 89.5; 90.5 | 5.0; 5.0 | 2.4; 2.4 | 72.3; 71.7 |
| sol / none | 1 | 82.3 | 8.6 | 6.0 | 72.8 |

## Where the false blocks land

Benign rows under G_CERT, pooled over repeats. `instances hit` counts the distinct frozen instances that produce at least one false block, out of the 60 in the suite.

| arm / thinking | false blocks / benign rows | instances hit / 60 | top instance | top 2 instances | top template family |
|---|---|---|---|---|---|
| qwen3-14b / - | 105/2400 | 12 | c09_storm2_w80_u100_0018 (33, 31.4%) | 66 (62.9%) | objective_shifting (22, 21.0%) |
| qwen3.6-27b-fp8 / - | 132/2400 | 25 | c09_storm2_w80_u100_0008 (33, 25.0%) | 63 (47.7%) | freeze_shift_contradiction (74, 56.1%) |
| glm-4-9b / - | 64/800 | 34 | c09_storm2_w80_u100_0018 (11, 17.2%) | 22 (34.4%) | freeze_shift_contradiction (30, 46.9%) |
| openai / - | 62/1600 | 14 | c09_storm2_w80_u100_0008 (22, 35.5%) | 42 (67.7%) | freeze_shift_contradiction (18, 29.0%) |
| deepseek / non_think | 1555/1600 | 60 | c09_storm2_w80_u100_0000 (50, 3.2%) | 96 (6.2%) | reorder_block_tight (140, 9.0%) |
| deepseek / think_high | 1591/1600 | 60 | c09_storm2_w80_u100_0000 (50, 3.1%) | 96 (6.0%) | reorder_block_tight (140, 8.8%) |
| sonnet / disabled | 61/1600 | 13 | c09_storm2_w80_u100_0008 (22, 36.1%) | 42 (68.9%) | freeze_shift_contradiction (22, 36.1%) |
| opus / default | 63/1600 | 13 | c09_storm2_w80_u100_0008 (22, 34.9%) | 42 (66.7%) | freeze_shift_contradiction (25, 39.7%) |
| opus / disabled | 80/1600 | 22 | c09_storm2_w80_u100_0008 (22, 27.5%) | 42 (52.5%) | freeze_shift_contradiction (42, 52.5%) |
| sol / none | 69/800 | 32 | c09_storm2_w80_u100_0008 (11, 15.9%) | 21 (30.4%) | freeze_shift_contradiction (25, 36.2%) |

### Is the concentration predictable across arms?

The reference set is the 13 instances the flagship (opus / default) hits under G_CERT. For each other capability-set arm the table gives the share of ITS false blocks that land inside that set, and the share that land on the single template family `freeze_shift_contradiction`.

| arm / thinking | false blocks | on the flagship's instances | on freeze_shift_contradiction |
|---|---|---|---|
| glm-4-9b / - | 64 | 40.6% | 46.9% |
| openai / - | 62 | 90.3% | 29.0% |
| opus / default | 63 | 100.0% | 39.7% |
| opus / disabled | 80 | 82.5% | 52.5% |
| qwen3-14b / - | 105 | 70.5% | 5.7% |
| qwen3.6-27b-fp8 / - | 132 | 75.0% | 56.1% |
| sol / none | 69 | 56.5% | 36.2% |
| sonnet / disabled | 61 | 93.4% | 36.1% |

Across the eight capability-set arms, 50 of the 60 instances produce at least one false block under G_CERT and 2 produce one under every arm.

## What these intervals do not establish

1. **They are uncertainty over instances, not over models or prompts.** One arm's interval says how much its rate would move on a fresh draw of 60 instances from the same generator. It says nothing about a different model family, a different prompt version, or a different tau.
2. **Sixty clusters is a small bootstrap.** The percentile interval is known to under-cover with few clusters, so these intervals are, if anything, optimistic. They are not corrected (no BCa, no small-cluster t-adjustment).
3. **The 60 instances come from only three strata** (c09_storm2_w80 with 24 instances, c10_replay_400 with 24, c10_storm2_w80 with 12). Clustering at instance level treats instances inside a stratum as exchangeable. If stratum-level correlation exists the true interval is wider, and a three-cluster bootstrap cannot measure it.
4. **A design effect below 1 is not evidence of extra precision.** It reflects that the cluster bootstrap conditions on each instance's own rows, which the balanced design makes near-identical across instances for some metrics.
5. **The concentration result is descriptive.** It says where the false blocks landed on these 60 instances; it does not prove the same instances would be the costly ones on a new portfolio, though the cross-arm table above shows the pattern is largely shared across proposers.
