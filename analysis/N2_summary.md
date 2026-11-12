# N2. Pricing accuracy per gate against the oracle

Generated 2026-11-03T21:31:45+08:00 by `code/scripts/n2_pricing.py` (`l1-n2-pricing-2`). Every number here is read from the CSVs named beside it.

Two readings of cost are carried side by side. The **absolute** truth is the executed schedule's gap to the optimum, g_true = (obj - OPT)/max(OPT, 1). The **marginal** truth subtracts what the dispatcher already loses on the untouched instance, m_true = g_true - g_anchor with g_anchor = (ATC_base - OPT_base)/max(OPT_base, 1), so it is the instruction's own cost. G-CERT-M is the certificate read the same way from recorded data only: m_cert = g_cert - g_cert_anchor, referred when m_cert > 0.20, with g_cert still logged on every row.

## Inputs and joins

| input | rows |
|---|---|
| direct benchmark, `analysis/DG1_direct_guard.csv` canonical/G_CERT reaching the quality stage, joined to `results/oracle_v1/items.jsonl` on item and canonical field | 1635 |
| end-to-end, `proposals_index.jsonl` executed rows joined to `verdicts_G_CERT.jsonl` on (source, item, mode, thinking, repeat) and to `proposals.jsonl` for the operations | 33566 |
| distinct constraining operation lists dispatched for WT_ref2 (new this run / total) | 0 / 2398 |
| brackets on disk / needed / needed and present | 1370 / 1340 / 1340 |

Rows and covered rows by operation split (`split` column of the row files):

| dataset | empty | sequencing only | field changing |
|---|---|---|---|
| direct | 255 / 255 covered | 835 / 835 covered | 545 / 545 covered |
| e2e | 8669 / 8669 covered | 14167 / 14167 covered | 10730 / 10730 covered |

Rule settings read: D-REL1 theta = 0.02, D-REL2 theta = 0.02, D-ABS A = 0.8119 bh (`DG14_delta_baselines.csv`, block matched; their benign and V3 tallies reproduce DG14 exactly). DG17 primary-policy settings: 90 (arm, thinking, held-out stratum, rule) cells from `DG17_e2e_delta.csv`; with them the recomputed held-out V3 separation count reproduces DG17 on 30 of 30 (cell, rule) pairs.

Certificate against the oracle files: objective mismatches above 1e-4 bh, direct 0 of 1635, end to end 0 of 33566; bound (logged lb_bh against the bracket's LB2) mismatches, direct 0 of 1635, end to end 0 of 33566. The recorded anchor certificate equals (ATC_base - LB2_base)/max(LB2_base, 1) on all 60 instances (asserted).

## 1. Soundness and pricing error (`N2_pricing_direct.csv`, `N2_pricing_e2e.csv`)

**Direct benchmark, absolute truth, all splits.** Signed error e = price - g_true over covered rows; [lo, hi] where a bracket is wider than 1e-3.

| gate | priced rows | median e | 5th pct | 95th pct | under-priced > 0.05 | over-priced > 0.05 |
|---|---|---|---|---|---|---|
| G-CERT | 1635 | 0.000 | -0.000 | [0.000, 0.003] | 0 = 0.0% (0 undecided) | 0 = 0.0% (1 undecided) |
| G-CERT-M | 1635 | -0.010 | -0.124 | 0.000 | 319 = 19.5% (0 undecided) | 0 = 0.0% (0 undecided) |
| D-REL1 | 1635 | -0.010 | -0.124 | 0.000 | 354 = 21.7% (0 undecided) | 24 = 1.5% (0 undecided) |
| D-REL2 | 1635 | -0.011 | -0.124 | 0.000 | 347 = 21.2% (0 undecided) | 0 = 0.0% (0 undecided) |
| D-ABS | 1635 | -0.010 | -0.124 | 0.000 | 324 = 19.8% (0 undecided) | 23 = 1.4% (1 undecided) |

Soundness: on 1635 covered rows the certificate's gap minus the oracle's optimistic end has minimum -4.98e-07, so it never under-prices g_true (asserted). Rows whose over-pricing exceeds the bracket's own width: 0. The logged bound sits strictly below the bracket's lower end on 0 rows and above it on 0.

**Direct benchmark, marginal truth, by split.** Signed error e = price - m_true.

| split | gate | priced rows | median e | 5th pct | 95th pct | under-priced > 0.05 | over-priced > 0.05 |
|---|---|---|---|---|---|---|---|
| sequencing_only | G-CERT-M | 835 | 0.000 | -0.000 | 0.000 | 0 = 0.0% (0 undecided) | 0 = 0.0% (0 undecided) |
| sequencing_only | D-REL2 | 835 | 0.000 | -0.024 | 0.000 | 19 = 2.3% (1 undecided) | 0 = 0.0% (0 undecided) |
| sequencing_only | G-CERT | 835 | 0.010 | -0.000 | 0.124 | 0 = 0.0% (0 undecided) | 155 = 18.6% (0 undecided) |
| sequencing_only | D-ABS | 835 | 0.000 | -0.000 | 0.000 | 0 = 0.0% (0 undecided) | 0 = 0.0% (0 undecided) |
| field_changing | G-CERT-M | 545 | [-0.000, 0.000] | [-0.002, -0.000] | [0.000, 0.003] | 0 = 0.0% (0 undecided) | 0 = 0.0% (0 undecided) |
| field_changing | D-REL2 | 545 | 0.000 | [-0.011, -0.007] | [0.004, 0.007] | 6 = 1.1% (1 undecided) | 2 = 0.4% (0 undecided) |
| field_changing | G-CERT | 545 | 0.010 | -0.000 | 0.124 | 0 = 0.0% (0 undecided) | 111 = 20.5% (3 undecided) |
| field_changing | D-ABS | 545 | 0.000 | [-0.014, -0.002] | [0.000, 0.014] | 15 = 2.8% (1 undecided) | 26 = 4.8% (1 undecided) |
| empty | G-CERT-M | 255 | 0.000 | -0.000 | 0.000 | 0 = 0.0% (0 undecided) | 0 = 0.0% (0 undecided) |
| empty | D-REL2 | 255 | 0.000 | -0.000 | 0.000 | 0 = 0.0% (0 undecided) | 0 = 0.0% (0 undecided) |
| empty | G-CERT | 255 | 0.012 | 0.000 | 0.124 | 0 = 0.0% (0 undecided) | 53 = 20.8% (0 undecided) |
| empty | D-ABS | 255 | 0.000 | -0.000 | 0.000 | 0 = 0.0% (0 undecided) | 0 = 0.0% (0 undecided) |
| all | G-CERT-M | 1635 | 0.000 | -0.000 | [0.000, 0.001] | 0 = 0.0% (0 undecided) | 0 = 0.0% (0 undecided) |
| all | D-REL2 | 1635 | 0.000 | [-0.017, -0.014] | [0.000, 0.002] | 25 = 1.5% (2 undecided) | 2 = 0.1% (0 undecided) |
| all | G-CERT | 1635 | 0.010 | -0.000 | 0.124 | 0 = 0.0% (0 undecided) | 319 = 19.5% (3 undecided) |
| all | D-ABS | 1635 | 0.000 | [-0.001, -0.000] | [0.000, 0.001] | 15 = 0.9% (1 undecided) | 26 = 1.6% (1 undecided) |

G-CERT-M against m_true (no guarantee, reported): error range per split all [-0.0173, 0.0345] on 1635 rows, 17 rows below zero; empty [-0.0000, 0.0000] on 255 rows, 0 rows below zero; sequencing_only [-0.0001, 0.0345] on 835 rows, 3 rows below zero; field_changing [-0.0173, 0.0332] on 545 rows, 14 rows below zero.

D-REL2 median signed error by stratum, all splits, with the stratum's median reference gap:

| stratum | D-REL2 median e (absolute) | D-REL2 median e (marginal) | G-CERT-M median e (marginal) | median reference gap | median certified anchor gap |
|---|---|---|---|---|---|
| c09_storm2_w80 | [-0.043, -0.042] | 0.000 | 0.000 | [0.040, 0.041] | 0.041 |
| c10_storm2_w80 | [-0.002, -0.000] | [-0.000, 0.000] | [-0.000, 0.000] | [0.001, 0.002] | 0.002 |
| c10_replay_400 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

**End to end, absolute truth, all splits.** Signed error e = price - g_true over covered rows; [lo, hi] where a bracket is wider than 1e-3.

| gate | priced rows | median e | 5th pct | 95th pct | under-priced > 0.05 | over-priced > 0.05 |
|---|---|---|---|---|---|---|
| G-CERT | 33566 | 0.000 | 0.000 | [0.000, 0.003] | 0 = 0.0% (0 undecided) | 0 = 0.0% (14 undecided) |
| G-CERT-M | 33566 | -0.010 | -0.124 | 0.000 | 6580 = 19.6% (0 undecided) | 0 = 0.0% (0 undecided) |
| D-REL1 | 33566 | -0.010 | -0.124 | 0.000 | 6943 = 20.7% (0 undecided) | 512 = 1.5% (0 undecided) |
| D-REL2 | 33363 | -0.011 | -0.124 | 0.000 | 6942 = 20.8% (3 undecided) | 0 = 0.0% (0 undecided) |
| D-ABS | 33566 | -0.010 | -0.124 | 0.000 | 6541 = 19.5% (0 undecided) | 496 = 1.5% (16 undecided) |

Soundness: on 33566 covered rows the certificate's gap minus the oracle's optimistic end has minimum 0.00e+00, so it never under-prices g_true (asserted). Rows whose over-pricing exceeds the bracket's own width: 0. The logged bound sits strictly below the bracket's lower end on 0 rows and above it on 0.

**End to end, marginal truth, by split.** Signed error e = price - m_true.

| split | gate | priced rows | median e | 5th pct | 95th pct | under-priced > 0.05 | over-priced > 0.05 |
|---|---|---|---|---|---|---|---|
| sequencing_only | G-CERT-M | 14167 | 0.000 | 0.000 | 0.000 | 0 = 0.0% (0 undecided) | 0 = 0.0% (0 undecided) |
| sequencing_only | D-REL2 | 14167 | 0.000 | -0.019 | 0.000 | 261 = 1.8% (16 undecided) | 0 = 0.0% (0 undecided) |
| sequencing_only | G-CERT | 14167 | 0.010 | 0.000 | 0.124 | 0 = 0.0% (0 undecided) | 2629 = 18.6% (3 undecided) |
| sequencing_only | D-ABS | 14167 | 0.000 | -0.000 | 0.000 | 0 = 0.0% (0 undecided) | 0 = 0.0% (0 undecided) |
| field_changing | G-CERT-M | 10730 | 0.000 | [-0.002, 0.000] | [0.000, 0.002] | 0 = 0.0% (0 undecided) | 0 = 0.0% (0 undecided) |
| field_changing | D-REL2 | 10527 | 0.000 | [-0.005, -0.003] | [0.002, 0.005] | 57 = 0.5% (6 undecided) | 35 = 0.3% (0 undecided) |
| field_changing | G-CERT | 10730 | 0.010 | 0.000 | 0.124 | 0 = 0.0% (0 undecided) | 2185 = 20.4% (34 undecided) |
| field_changing | D-ABS | 10730 | 0.000 | [-0.003, -0.000] | [0.095, 0.102] | 128 = 1.2% (0 undecided) | 549 = 5.1% (16 undecided) |
| empty | G-CERT-M | 8669 | 0.000 | 0.000 | 0.000 | 0 = 0.0% (0 undecided) | 0 = 0.0% (0 undecided) |
| empty | D-REL2 | 8669 | 0.000 | 0.000 | 0.000 | 0 = 0.0% (0 undecided) | 0 = 0.0% (0 undecided) |
| empty | G-CERT | 8669 | 0.011 | 0.000 | 0.124 | 0 = 0.0% (0 undecided) | 1766 = 20.4% (0 undecided) |
| empty | D-ABS | 8669 | 0.000 | 0.000 | 0.000 | 0 = 0.0% (0 undecided) | 0 = 0.0% (0 undecided) |
| all | G-CERT-M | 33566 | 0.000 | [-0.000, 0.000] | [0.000, 0.001] | 0 = 0.0% (0 undecided) | 0 = 0.0% (0 undecided) |
| all | D-REL2 | 33363 | 0.000 | [-0.006, -0.005] | [0.000, 0.001] | 318 = 1.0% (22 undecided) | 35 = 0.1% (0 undecided) |
| all | G-CERT | 33566 | 0.010 | 0.000 | 0.124 | 0 = 0.0% (0 undecided) | 6580 = 19.6% (37 undecided) |
| all | D-ABS | 33566 | 0.000 | -0.000 | [0.000, 0.001] | 128 = 0.4% (0 undecided) | 549 = 1.6% (16 undecided) |

G-CERT-M against m_true (no guarantee, reported): error range per split all [-0.0173, 0.0345] on 33566 rows, 613 rows below zero; empty [0.0000, 0.0000] on 8669 rows, 0 rows below zero; sequencing_only [-0.0001, 0.0345] on 14167 rows, 141 rows below zero; field_changing [-0.0173, 0.0332] on 10730 rows, 472 rows below zero.

D-REL2 median signed error by stratum, all splits, with the stratum's median reference gap:

| stratum | D-REL2 median e (absolute) | D-REL2 median e (marginal) | G-CERT-M median e (marginal) | median reference gap | median certified anchor gap |
|---|---|---|---|---|---|
| c09_storm2_w80 | -0.043 | 0.000 | 0.000 | [0.040, 0.041] | 0.041 |
| c10_storm2_w80 | [-0.002, -0.000] | 0.000 | 0.000 | [0.001, 0.002] | 0.002 |
| c10_replay_400 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Reference gap per instance (`N2_reference_gap.csv`)

| stratum | instances covered | median oracle gap | max oracle gap | median certified anchor gap | instances certified above 0.20 |
|---|---|---|---|---|---|
| all | 60 | 0.003 | [0.269, 0.287] | 0.003 | 2 |
| c09_storm2_w80 | 24 | [0.040, 0.041] | [0.269, 0.287] | 0.041 | 2 |
| c10_storm2_w80 | 12 | [0.001, 0.002] | 0.090 | 0.002 | 0 |
| c10_replay_400 | 24 | 0.000 | 0.016 | 0.000 | 0 |

## 2. The certificate's referrals under the marginal reading (`N2_cert_marginal.csv`)

| dataset | split | class | G-CERT referred | G-CERT-M referred | removed | added | referred and covered | of these, explained by the anchor gap |
|---|---|---|---|---|---|---|---|---|
| direct | all | benign | 21 | 0 | 21 | 0 | 21 | 21 |
| direct | all | V3 | 201 | 193 | 8 | 0 | 201 | 7 |
| direct | all | V4qv | 44 | 39 | 5 | 0 | 44 | 5 |
| direct | all | all | 279 | 232 | 47 | 0 | 279 | 46 |
| direct | empty | all | 7 | 0 | 7 | 0 | 7 | 7 |
| direct | sequencing_only | benign | 12 | 0 | 12 | 0 | 12 | 12 |
| direct | sequencing_only | V3 | 156 | 149 | 7 | 0 | 156 | 6 |
| direct | sequencing_only | V4qv | 42 | 39 | 3 | 0 | 42 | 3 |
| direct | sequencing_only | all | 214 | 188 | 26 | 0 | 214 | 25 |
| direct | field_changing | benign | 9 | 0 | 9 | 0 | 9 | 9 |
| direct | field_changing | V3 | 45 | 44 | 1 | 0 | 45 | 1 |
| direct | field_changing | V4qv | 2 | 0 | 2 | 0 | 2 | 2 |
| direct | field_changing | all | 58 | 44 | 14 | 0 | 58 | 14 |
| e2e | all | benign | 378 | 34 | 344 | 0 | 378 | 344 |
| e2e | all | V3 | 2986 | 2849 | 137 | 0 | 2986 | 121 |
| e2e | all | V4qv | 64 | 3 | 61 | 0 | 64 | 61 |
| e2e | all | all | 3959 | 2935 | 1024 | 0 | 3959 | 1008 |
| e2e | empty | benign | 4 | 0 | 4 | 0 | 4 | 4 |
| e2e | empty | V3 | 1 | 0 | 1 | 0 | 1 | 1 |
| e2e | empty | all | 292 | 0 | 292 | 0 | 292 | 292 |
| e2e | sequencing_only | benign | 223 | 28 | 195 | 0 | 223 | 195 |
| e2e | sequencing_only | V3 | 2408 | 2288 | 120 | 0 | 2408 | 104 |
| e2e | sequencing_only | V4qv | 61 | 3 | 58 | 0 | 61 | 58 |
| e2e | sequencing_only | all | 2774 | 2362 | 412 | 0 | 2774 | 396 |
| e2e | field_changing | benign | 151 | 6 | 145 | 0 | 151 | 145 |
| e2e | field_changing | V3 | 577 | 561 | 16 | 0 | 577 | 16 |
| e2e | field_changing | V4qv | 3 | 0 | 3 | 0 | 3 | 3 |
| e2e | field_changing | all | 893 | 573 | 320 | 0 | 893 | 320 |

## 3. Disposition agreement with the oracle (`N2_disposition.csv`)

**Direct benchmark, absolute truth**, published operating points, all classes, all splits.

| delta | gate | costly / cheap / undecided | TPR [95% CI] | FPR [95% CI] |
|---|---|---|---|---|
| 0.05 | G-CERT | 530 / 1105 / 0 | 52.6% [39.3, 70.9] | 0.0% [0.0, 0.0] |
| 0.05 | G-CERT-M | 530 / 1105 / 0 | 43.8% [33.0, 60.6] | 0.0% [0.0, 0.0] |
| 0.05 | D-REL2 | 530 / 1105 / 0 | 49.8% [37.9, 68.6] | 0.3% [0.0, 0.6] |
| 0.05 | G-CERT|D-REL2 | 530 / 1105 / 0 | 56.8% [42.7, 76.4] | 0.3% [0.0, 0.6] |
| 0.05 | G-CERT-M|D-REL2 | 530 / 1105 / 0 | 49.8% [37.9, 68.6] | 0.3% [0.0, 0.6] |
| 0.1 | G-CERT | 361 / 1274 / 0 | 77.3% [59.4, 94.6] | 0.0% [0.0, 0.0] |
| 0.1 | G-CERT-M | 361 / 1274 / 0 | 64.3% [48.0, 86.8] | 0.0% [0.0, 0.0] |
| 0.1 | D-REL2 | 361 / 1274 / 0 | 70.9% [53.7, 93.3] | 0.9% [0.3, 1.6] |
| 0.1 | G-CERT|D-REL2 | 361 / 1274 / 0 | 81.2% [62.3, 98.7] | 0.9% [0.3, 1.6] |
| 0.1 | G-CERT-M|D-REL2 | 361 / 1274 / 0 | 70.9% [53.7, 93.3] | 0.9% [0.3, 1.6] |
| 0.2 | G-CERT | 278 / 1356 / 1 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| 0.2 | G-CERT-M | 278 / 1356 / 1 | 83.5% [67.3, 98.4] | 0.0% [0.0, 0.0] |
| 0.2 | D-REL2 | 278 / 1356 / 1 | 86.7% [71.6, 100.0] | 1.8% [0.9, 3.0] |
| 0.2 | G-CERT|D-REL2 | 278 / 1356 / 1 | 100.0% [100.0, 100.0] | 1.8% [0.9, 3.0] |
| 0.2 | G-CERT-M|D-REL2 | 278 / 1356 / 1 | 86.7% [71.6, 100.0] | 1.8% [0.9, 3.0] |

**End to end, absolute truth**, published operating points, all classes, all splits.

| delta | gate | costly / cheap / undecided | TPR [95% CI] | FPR [95% CI] |
|---|---|---|---|---|
| 0.05 | G-CERT | 9302 / 24261 / 3 | 42.6% [28.5, 63.8] | 0.0% [0.0, 0.0] |
| 0.05 | G-CERT-M | 9302 / 24261 / 3 | 31.6% [22.3, 48.6] | 0.0% [0.0, 0.0] |
| 0.05 | D-REL2 | 9302 / 24261 / 3 | 36.0% [25.7, 55.2] | 0.2% [0.0, 0.5] |
| 0.05 | G-CERT|D-REL2 | 9302 / 24261 / 3 | 45.6% [30.9, 68.0] | 0.2% [0.0, 0.5] |
| 0.05 | G-CERT-M|D-REL2 | 9302 / 24261 / 3 | 36.0% [25.7, 55.2] | 0.2% [0.0, 0.5] |
| 0.1 | G-CERT | 5575 / 27991 / 0 | 71.0% [48.6, 95.2] | 0.0% [0.0, 0.0] |
| 0.1 | G-CERT-M | 5575 / 27991 / 0 | 52.6% [35.5, 82.4] | 0.0% [0.0, 0.0] |
| 0.1 | D-REL2 | 5575 / 27991 / 0 | 58.0% [39.6, 88.6] | 0.6% [0.2, 1.1] |
| 0.1 | G-CERT|D-REL2 | 5575 / 27991 / 0 | 74.0% [50.9, 98.9] | 0.6% [0.2, 1.1] |
| 0.1 | G-CERT-M|D-REL2 | 5575 / 27991 / 0 | 58.0% [39.6, 88.6] | 0.6% [0.2, 1.1] |
| 0.2 | G-CERT | 3943 / 29607 / 16 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| 0.2 | G-CERT-M | 3943 / 29607 / 16 | 74.4% [54.0, 98.1] | 0.0% [0.0, 0.0] |
| 0.2 | D-REL2 | 3943 / 29607 / 16 | 77.3% [56.8, 100.0] | 1.1% [0.6, 1.7] |
| 0.2 | G-CERT|D-REL2 | 3943 / 29607 / 16 | 100.0% [100.0, 100.0] | 1.1% [0.6, 1.7] |
| 0.2 | G-CERT-M|D-REL2 | 3943 / 29607 / 16 | 77.3% [56.8, 100.0] | 1.1% [0.6, 1.7] |

**Direct benchmark, marginal truth**, published operating points, all classes, all splits.

| delta | gate | costly / cheap / undecided | TPR [95% CI] | FPR [95% CI] |
|---|---|---|---|---|
| 0.05 | G-CERT | 263 / 1372 / 0 | 91.6% [86.1, 96.2] | 2.8% [0.0, 7.2] |
| 0.05 | G-CERT-M | 263 / 1372 / 0 | 88.2% [81.9, 93.7] | 0.0% [0.0, 0.0] |
| 0.05 | D-REL2 | 263 / 1372 / 0 | 100.0% [100.0, 100.0] | 0.3% [0.1, 0.6] |
| 0.05 | G-CERT|D-REL2 | 263 / 1372 / 0 | 100.0% [100.0, 100.0] | 3.0% [0.1, 7.4] |
| 0.05 | G-CERT-M|D-REL2 | 263 / 1372 / 0 | 100.0% [100.0, 100.0] | 0.3% [0.1, 0.6] |
| 0.1 | G-CERT | 254 / 1381 / 0 | 94.9% [90.6, 98.3] | 2.8% [0.0, 7.1] |
| 0.1 | G-CERT-M | 254 / 1381 / 0 | 91.3% [85.9, 95.9] | 0.0% [0.0, 0.0] |
| 0.1 | D-REL2 | 254 / 1381 / 0 | 100.0% [100.0, 100.0] | 0.9% [0.3, 1.8] |
| 0.1 | G-CERT|D-REL2 | 254 / 1381 / 0 | 100.0% [100.0, 100.0] | 3.6% [0.6, 8.0] |
| 0.1 | G-CERT-M|D-REL2 | 254 / 1381 / 0 | 100.0% [100.0, 100.0] | 0.9% [0.3, 1.8] |
| 0.2 | G-CERT | 231 / 1403 / 1 | 100.0% [100.0, 100.0] | 3.3% [0.3, 7.9] |
| 0.2 | G-CERT-M | 231 / 1403 / 1 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| 0.2 | D-REL2 | 231 / 1403 / 1 | 100.0% [100.0, 100.0] | 2.5% [1.4, 3.7] |
| 0.2 | G-CERT|D-REL2 | 231 / 1403 / 1 | 100.0% [100.0, 100.0] | 5.1% [1.8, 9.6] |
| 0.2 | G-CERT-M|D-REL2 | 231 / 1403 / 1 | 100.0% [100.0, 100.0] | 2.5% [1.4, 3.7] |

**End to end, marginal truth**, published operating points, all classes, all splits.

| delta | gate | costly / cheap / undecided | TPR [95% CI] | FPR [95% CI] |
|---|---|---|---|---|
| 0.05 | G-CERT | 3330 / 30236 / 0 | 91.6% [86.9, 95.5] | 3.0% [0.0, 7.7] |
| 0.05 | G-CERT-M | 3330 / 30236 / 0 | 88.1% [82.8, 92.7] | 0.0% [0.0, 0.0] |
| 0.05 | D-REL2 | 3330 / 30236 / 0 | 100.0% [99.9, 100.0] | 0.3% [0.1, 0.5] |
| 0.05 | G-CERT|D-REL2 | 3330 / 30236 / 0 | 100.0% [99.9, 100.0] | 3.2% [0.1, 7.9] |
| 0.05 | G-CERT-M|D-REL2 | 3330 / 30236 / 0 | 100.0% [99.9, 100.0] | 0.3% [0.1, 0.5] |
| 0.1 | G-CERT | 3206 / 30360 / 0 | 95.1% [91.3, 98.2] | 3.0% [0.0, 7.7] |
| 0.1 | G-CERT-M | 3206 / 30360 / 0 | 91.5% [86.7, 95.6] | 0.0% [0.0, 0.0] |
| 0.1 | D-REL2 | 3206 / 30360 / 0 | 100.0% [100.0, 100.0] | 0.7% [0.3, 1.1] |
| 0.1 | G-CERT|D-REL2 | 3206 / 30360 / 0 | 100.0% [100.0, 100.0] | 3.6% [0.4, 8.3] |
| 0.1 | G-CERT-M|D-REL2 | 3206 / 30360 / 0 | 100.0% [100.0, 100.0] | 0.7% [0.3, 1.1] |
| 0.2 | G-CERT | 2931 / 30631 / 4 | 100.0% [100.0, 100.0] | 3.3% [0.2, 8.0] |
| 0.2 | G-CERT-M | 2931 / 30631 / 4 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| 0.2 | D-REL2 | 2931 / 30631 / 4 | 100.0% [100.0, 100.0] | 1.5% [1.0, 2.2] |
| 0.2 | G-CERT|D-REL2 | 2931 / 30631 / 4 | 100.0% [100.0, 100.0] | 4.5% [1.2, 9.1] |
| 0.2 | G-CERT-M|D-REL2 | 2931 / 30631 / 4 | 100.0% [100.0, 100.0] | 1.5% [1.0, 2.2] |

**Marginal truth, every gate at threshold = delta** (the published points compare a rule at theta = 0.02 with a certificate at tau = 0.20, so this is the like-for-like reading), all classes.

| dataset | split | delta | gate | costly / cheap | TPR [95% CI] | FPR [95% CI] |
|---|---|---|---|---|---|---|
| direct | all | 0.05 | G-CERT | 263 / 1372 | 100.0% [100.0, 100.0] | 19.5% [9.0, 30.9] |
| direct | all | 0.05 | G-CERT-M | 263 / 1372 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | all | 0.05 | D-REL2 | 263 / 1372 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | all | 0.05 | G-CERT-M|D-REL2 | 263 / 1372 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | all | 0.1 | G-CERT | 254 / 1381 | 100.0% [100.0, 100.0] | 7.7% [1.4, 16.3] |
| direct | all | 0.1 | G-CERT-M | 254 / 1381 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | all | 0.1 | D-REL2 | 254 / 1381 | 99.6% [98.7, 100.0] | 0.0% [0.0, 0.0] |
| direct | all | 0.1 | G-CERT-M|D-REL2 | 254 / 1381 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | all | 0.2 | G-CERT | 231 / 1403 | 100.0% [100.0, 100.0] | 3.3% [0.3, 7.9] |
| direct | all | 0.2 | G-CERT-M | 231 / 1403 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | all | 0.2 | D-REL2 | 231 / 1403 | 99.1% [97.8, 100.0] | 0.0% [0.0, 0.0] |
| direct | all | 0.2 | G-CERT-M|D-REL2 | 231 / 1403 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | sequencing_only | 0.05 | G-CERT | 218 / 617 | 100.0% [100.0, 100.0] | 18.8% [8.6, 30.0] |
| direct | sequencing_only | 0.05 | G-CERT-M | 218 / 617 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | sequencing_only | 0.05 | D-REL2 | 218 / 617 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | sequencing_only | 0.05 | G-CERT-M|D-REL2 | 218 / 617 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | sequencing_only | 0.1 | G-CERT | 209 / 626 | 100.0% [100.0, 100.0] | 7.7% [1.4, 16.0] |
| direct | sequencing_only | 0.1 | G-CERT-M | 209 / 626 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | sequencing_only | 0.1 | D-REL2 | 209 / 626 | 99.5% [98.4, 100.0] | 0.0% [0.0, 0.0] |
| direct | sequencing_only | 0.1 | G-CERT-M|D-REL2 | 209 / 626 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | sequencing_only | 0.2 | G-CERT | 188 / 647 | 100.0% [100.0, 100.0] | 4.0% [0.7, 8.7] |
| direct | sequencing_only | 0.2 | G-CERT-M | 188 / 647 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | sequencing_only | 0.2 | D-REL2 | 188 / 647 | 98.9% [97.3, 100.0] | 0.0% [0.0, 0.0] |
| direct | sequencing_only | 0.2 | G-CERT-M|D-REL2 | 188 / 647 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | field_changing | 0.05 | G-CERT | 45 / 500 | 100.0% [100.0, 100.0] | 19.6% [9.2, 30.8] |
| direct | field_changing | 0.05 | G-CERT-M | 45 / 500 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | field_changing | 0.05 | D-REL2 | 45 / 500 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | field_changing | 0.05 | G-CERT-M|D-REL2 | 45 / 500 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | field_changing | 0.1 | G-CERT | 45 / 500 | 100.0% [100.0, 100.0] | 7.8% [1.4, 16.1] |
| direct | field_changing | 0.1 | G-CERT-M | 45 / 500 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | field_changing | 0.1 | D-REL2 | 45 / 500 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | field_changing | 0.1 | G-CERT-M|D-REL2 | 45 / 500 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | field_changing | 0.2 | G-CERT | 43 / 501 | 100.0% [100.0, 100.0] | 2.8% [0.0, 7.2] |
| direct | field_changing | 0.2 | G-CERT-M | 43 / 501 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | field_changing | 0.2 | D-REL2 | 43 / 501 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| direct | field_changing | 0.2 | G-CERT-M|D-REL2 | 43 / 501 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | all | 0.05 | G-CERT | 3330 / 30236 | 100.0% [100.0, 100.0] | 19.8% [9.3, 31.2] |
| e2e | all | 0.05 | G-CERT-M | 3330 / 30236 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | all | 0.05 | D-REL2 | 3330 / 30236 | 100.0% [99.9, 100.0] | 0.0% [0.0, 0.0] |
| e2e | all | 0.05 | G-CERT-M|D-REL2 | 3330 / 30236 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | all | 0.1 | G-CERT | 3206 / 30360 | 100.0% [100.0, 100.0] | 7.8% [1.4, 16.4] |
| e2e | all | 0.1 | G-CERT-M | 3206 / 30360 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | all | 0.1 | D-REL2 | 3206 / 30360 | 99.8% [99.4, 100.0] | 0.0% [0.0, 0.0] |
| e2e | all | 0.1 | G-CERT-M|D-REL2 | 3206 / 30360 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | all | 0.2 | G-CERT | 2931 / 30631 | 100.0% [100.0, 100.0] | 3.3% [0.2, 8.0] |
| e2e | all | 0.2 | G-CERT-M | 2931 / 30631 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | all | 0.2 | D-REL2 | 2931 / 30631 | 100.0% [99.9, 100.0] | 0.0% [0.0, 0.0] |
| e2e | all | 0.2 | G-CERT-M|D-REL2 | 2931 / 30631 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | sequencing_only | 0.05 | G-CERT | 2709 / 11458 | 100.0% [100.0, 100.0] | 18.6% [8.5, 29.9] |
| e2e | sequencing_only | 0.05 | G-CERT-M | 2709 / 11458 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | sequencing_only | 0.05 | D-REL2 | 2709 / 11458 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | sequencing_only | 0.05 | G-CERT-M|D-REL2 | 2709 / 11458 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | sequencing_only | 0.1 | G-CERT | 2608 / 11559 | 100.0% [100.0, 100.0] | 7.2% [1.3, 15.5] |
| e2e | sequencing_only | 0.1 | G-CERT-M | 2608 / 11559 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | sequencing_only | 0.1 | D-REL2 | 2608 / 11559 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | sequencing_only | 0.1 | G-CERT-M|D-REL2 | 2608 / 11559 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | sequencing_only | 0.2 | G-CERT | 2362 / 11805 | 100.0% [100.0, 100.0] | 3.5% [0.5, 7.8] |
| e2e | sequencing_only | 0.2 | G-CERT-M | 2362 / 11805 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | sequencing_only | 0.2 | D-REL2 | 2362 / 11805 | 100.0% [99.9, 100.0] | 0.0% [0.0, 0.0] |
| e2e | sequencing_only | 0.2 | G-CERT-M|D-REL2 | 2362 / 11805 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | field_changing | 0.05 | G-CERT | 621 / 10109 | 100.0% [100.0, 100.0] | 20.5% [9.9, 31.8] |
| e2e | field_changing | 0.05 | G-CERT-M | 621 / 10109 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | field_changing | 0.05 | D-REL2 | 621 / 10109 | 99.8% [99.5, 100.0] | 0.0% [0.0, 0.0] |
| e2e | field_changing | 0.05 | G-CERT-M|D-REL2 | 621 / 10109 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | field_changing | 0.1 | G-CERT | 598 / 10132 | 100.0% [100.0, 100.0] | 8.1% [1.5, 16.7] |
| e2e | field_changing | 0.1 | G-CERT-M | 598 / 10132 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | field_changing | 0.1 | D-REL2 | 598 / 10132 | 99.0% [96.8, 100.0] | 0.0% [0.0, 0.0] |
| e2e | field_changing | 0.1 | G-CERT-M|D-REL2 | 598 / 10132 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | field_changing | 0.2 | G-CERT | 569 / 10157 | 100.0% [100.0, 100.0] | 3.2% [0.1, 7.8] |
| e2e | field_changing | 0.2 | G-CERT-M | 569 / 10157 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | field_changing | 0.2 | D-REL2 | 569 / 10157 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |
| e2e | field_changing | 0.2 | G-CERT-M|D-REL2 | 569 / 10157 | 100.0% [100.0, 100.0] | 0.0% [0.0, 0.0] |

**Marginal truth by split and class, delta = 0.10, published operating points.**

| dataset | split | class | gate | costly / cheap | TPR | FPR |
|---|---|---|---|---|---|---|
| direct | sequencing_only | benign | G-CERT | 0 / 485 | n/a | 2.5% |
| direct | sequencing_only | benign | G-CERT-M | 0 / 485 | n/a | 0.0% |
| direct | sequencing_only | benign | D-REL2 | 0 / 485 | n/a | 0.0% |
| direct | sequencing_only | benign | G-CERT-M|D-REL2 | 0 / 485 | n/a | 0.0% |
| direct | sequencing_only | V3 | G-CERT | 163 / 12 | 94.5% | 16.7% |
| direct | sequencing_only | V3 | G-CERT-M | 163 / 12 | 91.4% | 0.0% |
| direct | sequencing_only | V3 | D-REL2 | 163 / 12 | 100.0% | 75.0% |
| direct | sequencing_only | V3 | G-CERT-M|D-REL2 | 163 / 12 | 100.0% | 75.0% |
| direct | sequencing_only | V4qv | G-CERT | 46 / 4 | 91.3% | 0.0% |
| direct | sequencing_only | V4qv | G-CERT-M | 46 / 4 | 84.8% | 0.0% |
| direct | sequencing_only | V4qv | D-REL2 | 46 / 4 | 100.0% | 100.0% |
| direct | sequencing_only | V4qv | G-CERT-M|D-REL2 | 46 / 4 | 100.0% | 100.0% |
| direct | sequencing_only | all | G-CERT | 209 / 626 | 93.8% | 2.9% |
| direct | sequencing_only | all | G-CERT-M | 209 / 626 | 90.0% | 0.0% |
| direct | sequencing_only | all | D-REL2 | 209 / 626 | 100.0% | 2.1% |
| direct | sequencing_only | all | G-CERT-M|D-REL2 | 209 / 626 | 100.0% | 2.1% |
| direct | field_changing | benign | G-CERT | 0 / 315 | n/a | 2.9% |
| direct | field_changing | benign | G-CERT-M | 0 / 315 | n/a | 0.0% |
| direct | field_changing | benign | D-REL2 | 0 / 315 | n/a | 0.0% |
| direct | field_changing | benign | G-CERT-M|D-REL2 | 0 / 315 | n/a | 0.0% |
| direct | field_changing | V3 | G-CERT | 45 / 0 | 100.0% | n/a |
| direct | field_changing | V3 | G-CERT-M | 45 / 0 | 97.8% | n/a |
| direct | field_changing | V3 | D-REL2 | 45 / 0 | 100.0% | n/a |
| direct | field_changing | V3 | G-CERT-M|D-REL2 | 45 / 0 | 100.0% | n/a |
| direct | field_changing | V4qv | G-CERT | 0 / 5 | n/a | 40.0% |
| direct | field_changing | V4qv | G-CERT-M | 0 / 5 | n/a | 0.0% |
| direct | field_changing | V4qv | D-REL2 | 0 / 5 | n/a | 0.0% |
| direct | field_changing | V4qv | G-CERT-M|D-REL2 | 0 / 5 | n/a | 0.0% |
| direct | field_changing | all | G-CERT | 45 / 500 | 100.0% | 2.6% |
| direct | field_changing | all | G-CERT-M | 45 / 500 | 97.8% | 0.0% |
| direct | field_changing | all | D-REL2 | 45 / 500 | 100.0% | 0.0% |
| direct | field_changing | all | G-CERT-M|D-REL2 | 45 / 500 | 100.0% | 0.0% |
| e2e | sequencing_only | benign | G-CERT | 30 / 7709 | 93.3% | 2.5% |
| e2e | sequencing_only | benign | G-CERT-M | 30 / 7709 | 93.3% | 0.0% |
| e2e | sequencing_only | benign | D-REL2 | 30 / 7709 | 100.0% | 0.0% |
| e2e | sequencing_only | benign | G-CERT-M|D-REL2 | 30 / 7709 | 100.0% | 0.0% |
| e2e | sequencing_only | V3 | G-CERT | 2517 / 273 | 94.3% | 12.5% |
| e2e | sequencing_only | V3 | G-CERT-M | 2517 / 273 | 90.9% | 0.0% |
| e2e | sequencing_only | V3 | D-REL2 | 2517 / 273 | 100.0% | 55.7% |
| e2e | sequencing_only | V3 | G-CERT-M|D-REL2 | 2517 / 273 | 100.0% | 55.7% |
| e2e | sequencing_only | V4qv | G-CERT | 3 / 868 | 100.0% | 6.7% |
| e2e | sequencing_only | V4qv | G-CERT-M | 3 / 868 | 100.0% | 0.0% |
| e2e | sequencing_only | V4qv | D-REL2 | 3 / 868 | 100.0% | 0.0% |
| e2e | sequencing_only | V4qv | G-CERT-M|D-REL2 | 3 / 868 | 100.0% | 0.0% |
| e2e | sequencing_only | all | G-CERT | 2608 / 11559 | 94.1% | 2.8% |
| e2e | sequencing_only | all | G-CERT-M | 2608 / 11559 | 90.6% | 0.0% |
| e2e | sequencing_only | all | D-REL2 | 2608 / 11559 | 100.0% | 1.5% |
| e2e | sequencing_only | all | G-CERT-M|D-REL2 | 2608 / 11559 | 100.0% | 1.5% |
| e2e | field_changing | benign | G-CERT | 9 / 4841 | 100.0% | 2.9% |
| e2e | field_changing | benign | G-CERT-M | 9 / 4841 | 66.7% | 0.0% |
| e2e | field_changing | benign | D-REL2 | 9 / 4841 | 100.0% | 0.1% |
| e2e | field_changing | benign | G-CERT-M|D-REL2 | 9 / 4841 | 100.0% | 0.1% |
| e2e | field_changing | V3 | G-CERT | 576 / 133 | 100.0% | 0.8% |
| e2e | field_changing | V3 | G-CERT-M | 576 / 133 | 97.4% | 0.0% |
| e2e | field_changing | V3 | D-REL2 | 576 / 133 | 100.0% | 10.5% |
| e2e | field_changing | V3 | G-CERT-M|D-REL2 | 576 / 133 | 100.0% | 10.5% |
| e2e | field_changing | V4qv | G-CERT | 0 / 7 | n/a | 42.9% |
| e2e | field_changing | V4qv | G-CERT-M | 0 / 7 | n/a | 0.0% |
| e2e | field_changing | V4qv | D-REL2 | 0 / 7 | n/a | 0.0% |
| e2e | field_changing | V4qv | G-CERT-M|D-REL2 | 0 / 7 | n/a | 0.0% |
| e2e | field_changing | all | G-CERT | 598 / 10132 | 99.5% | 2.9% |
| e2e | field_changing | all | G-CERT-M | 598 / 10132 | 95.8% | 0.0% |
| e2e | field_changing | all | D-REL2 | 598 / 10132 | 100.0% | 0.3% |
| e2e | field_changing | all | G-CERT-M|D-REL2 | 598 / 10132 | 100.0% | 0.3% |

## 4. Where each gate wins (`N2_wins.csv`), D-REL2 against the certificate, published settings, all splits

**Direct benchmark, absolute truth**.

| delta | stratum | median reference gap | D-REL2 miss | G-CERT false referral | G-CERT-M miss | G-CERT-M false referral | union (G-CERT-M or D-REL2) miss | union false referral |
|---|---|---|---|---|---|---|---|---|
| 0.05 | all | 0.003 | 50.2% (266) | 0.0% (0) | 56.2% (298) | 0.0% (0) | 50.2% (266) | 0.3% (3) |
| 0.05 | c09_storm2_w80 | [0.040, 0.041] | 63.7% (244) | 0.0% (0) | 68.4% (262) | 0.0% (0) | 63.7% (244) | 0.0% (0) |
| 0.05 | c10_storm2_w80 | [0.001, 0.002] | 30.6% (22) | 0.0% (0) | 34.7% (25) | 0.0% (0) | 30.6% (22) | 0.4% (1) |
| 0.05 | c10_replay_400 | 0.000 | 0.0% (0) | 0.0% (0) | 14.7% (11) | 0.0% (0) | 0.0% (0) | 0.5% (2) |
| 0.1 | all | 0.003 | 29.1% (105) | 0.0% (0) | 35.7% (129) | 0.0% (0) | 29.1% (105) | 0.9% (11) |
| 0.1 | c09_storm2_w80 | [0.040, 0.041] | 43.3% (103) | 0.0% (0) | 49.2% (117) | 0.0% (0) | 43.3% (103) | 0.7% (4) |
| 0.1 | c10_storm2_w80 | [0.001, 0.002] | 3.9% (2) | 0.0% (0) | 7.8% (4) | 0.0% (0) | 3.9% (2) | 0.8% (2) |
| 0.1 | c10_replay_400 | 0.000 | 0.0% (0) | 0.0% (0) | 11.1% (8) | 0.0% (0) | 0.0% (0) | 1.2% (5) |
| 0.2 | all | 0.003 | 13.3% (37) | 0.0% (0) | 16.5% (46) | 0.0% (0) | 13.3% (37) | 1.8% (25) |
| 0.2 | c09_storm2_w80 | [0.040, 0.041] | 22.2% (37) | 0.0% (0) | 27.5% (46) | 0.0% (0) | 22.2% (37) | 1.2% (8) |
| 0.2 | c10_storm2_w80 | [0.001, 0.002] | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 1.5% (4) |
| 0.2 | c10_replay_400 | 0.000 | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 3.0% (13) |

**End to end, absolute truth**.

| delta | stratum | median reference gap | D-REL2 miss | G-CERT false referral | G-CERT-M miss | G-CERT-M false referral | union (G-CERT-M or D-REL2) miss | union false referral |
|---|---|---|---|---|---|---|---|---|
| 0.05 | all | 0.003 | 64.0% (5954) | 0.0% (0) | 68.4% (6367) | 0.0% (0) | 64.0% (5954) | 0.2% (57) |
| 0.05 | c09_storm2_w80 | [0.040, 0.041] | 75.4% (5443) | 0.0% (0) | 78.5% (5671) | 0.0% (0) | 75.4% (5443) | 0.0% (4) |
| 0.05 | c10_storm2_w80 | [0.001, 0.002] | 44.2% (511) | 0.0% (0) | 48.6% (562) | 0.0% (0) | 44.2% (511) | 0.3% (19) |
| 0.05 | c10_replay_400 | 0.000 | 0.0% (0) | 0.0% (0) | 14.5% (134) | 0.0% (0) | 0.0% (0) | 0.4% (34) |
| 0.1 | all | 0.003 | 42.0% (2344) | 0.0% (0) | 47.4% (2640) | 0.0% (0) | 42.0% (2344) | 0.6% (174) |
| 0.1 | c09_storm2_w80 | [0.040, 0.041] | 57.3% (2330) | 0.0% (0) | 61.8% (2512) | 0.0% (0) | 57.3% (2330) | 0.4% (50) |
| 0.1 | c10_storm2_w80 | [0.001, 0.002] | 2.2% (14) | 0.0% (0) | 5.1% (32) | 0.0% (0) | 2.2% (14) | 0.9% (52) |
| 0.1 | c10_replay_400 | 0.000 | 0.0% (0) | 0.0% (0) | 10.8% (96) | 0.0% (0) | 0.0% (0) | 0.8% (72) |
| 0.2 | all | 0.003 | 22.7% (894) | 0.0% (0) | 25.6% (1008) | 0.0% (0) | 22.7% (894) | 1.1% (340) |
| 0.2 | c09_storm2_w80 | [0.040, 0.041] | 34.9% (894) | 0.0% (0) | 39.4% (1008) | 0.0% (0) | 34.9% (894) | 0.7% (102) |
| 0.2 | c10_storm2_w80 | [0.001, 0.002] | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 1.2% (70) |
| 0.2 | c10_replay_400 | 0.000 | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 1.8% (168) |

**Direct benchmark, marginal truth**.

| delta | stratum | median reference gap | D-REL2 miss | G-CERT false referral | G-CERT-M miss | G-CERT-M false referral | union (G-CERT-M or D-REL2) miss | union false referral |
|---|---|---|---|---|---|---|---|---|
| 0.05 | all | 0.003 | 0.0% (0) | 2.8% (38) | 11.8% (31) | 0.0% (0) | 0.0% (0) | 0.3% (4) |
| 0.05 | c09_storm2_w80 | [0.040, 0.041] | 0.0% (0) | 5.5% (38) | 12.3% (17) | 0.0% (0) | 0.0% (0) | 0.1% (1) |
| 0.05 | c10_storm2_w80 | [0.001, 0.002] | 0.0% (0) | 0.0% (0) | 6.0% (3) | 0.0% (0) | 0.0% (0) | 0.4% (1) |
| 0.05 | c10_replay_400 | 0.000 | 0.0% (0) | 0.0% (0) | 14.7% (11) | 0.0% (0) | 0.0% (0) | 0.5% (2) |
| 0.1 | all | 0.003 | 0.0% (0) | 2.8% (38) | 8.7% (22) | 0.0% (0) | 0.0% (0) | 0.9% (13) |
| 0.1 | c09_storm2_w80 | [0.040, 0.041] | 0.0% (0) | 5.5% (38) | 9.7% (13) | 0.0% (0) | 0.0% (0) | 0.7% (5) |
| 0.1 | c10_storm2_w80 | [0.001, 0.002] | 0.0% (0) | 0.0% (0) | 4.1% (2) | 0.0% (0) | 0.0% (0) | 0.8% (2) |
| 0.1 | c10_replay_400 | 0.000 | 0.0% (0) | 0.0% (0) | 9.9% (7) | 0.0% (0) | 0.0% (0) | 1.4% (6) |
| 0.2 | all | 0.003 | 0.0% (0) | 3.3% (47) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 2.5% (35) |
| 0.2 | c09_storm2_w80 | [0.040, 0.041] | 0.0% (0) | 6.6% (47) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 2.5% (18) |
| 0.2 | c10_storm2_w80 | [0.001, 0.002] | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 1.5% (4) |
| 0.2 | c10_replay_400 | 0.000 | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 3.0% (13) |

**End to end, marginal truth**.

| delta | stratum | median reference gap | D-REL2 miss | G-CERT false referral | G-CERT-M miss | G-CERT-M false referral | union (G-CERT-M or D-REL2) miss | union false referral |
|---|---|---|---|---|---|---|---|---|
| 0.05 | all | 0.003 | 0.0% (1) | 3.0% (910) | 11.9% (395) | 0.0% (0) | 0.0% (1) | 0.3% (76) |
| 0.05 | c09_storm2_w80 | [0.040, 0.041] | 0.1% (1) | 6.0% (910) | 12.0% (212) | 0.0% (0) | 0.1% (1) | 0.1% (21) |
| 0.05 | c10_storm2_w80 | [0.001, 0.002] | 0.0% (0) | 0.0% (0) | 7.6% (49) | 0.0% (0) | 0.0% (0) | 0.4% (21) |
| 0.05 | c10_replay_400 | 0.000 | 0.0% (0) | 0.0% (0) | 14.5% (134) | 0.0% (0) | 0.0% (0) | 0.4% (34) |
| 0.1 | all | 0.003 | 0.0% (0) | 3.0% (910) | 8.5% (271) | 0.0% (0) | 0.0% (0) | 0.7% (199) |
| 0.1 | c09_storm2_w80 | [0.040, 0.041] | 0.0% (0) | 6.0% (910) | 9.2% (157) | 0.0% (0) | 0.0% (0) | 0.5% (75) |
| 0.1 | c10_storm2_w80 | [0.001, 0.002] | 0.0% (0) | 0.0% (0) | 2.9% (18) | 0.0% (0) | 0.0% (0) | 0.9% (52) |
| 0.1 | c10_replay_400 | 0.000 | 0.0% (0) | 0.0% (0) | 10.8% (96) | 0.0% (0) | 0.0% (0) | 0.8% (72) |
| 0.2 | all | 0.003 | 0.0% (0) | 3.3% (1024) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 1.5% (470) |
| 0.2 | c09_storm2_w80 | [0.040, 0.041] | 0.0% (0) | 6.6% (1024) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 1.5% (232) |
| 0.2 | c10_storm2_w80 | [0.001, 0.002] | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 1.2% (70) |
| 0.2 | c10_replay_400 | 0.000 | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 1.8% (168) |

## 5. Re-labelled quality class (`N2_relabel.csv`)

| group | proposal | delta | covered / items | absolute: costly / cheap / undecided (share) | marginal: costly / cheap / undecided (share) |
|---|---|---|---|---|---|
| V3 | gold_ops | 0.05 | 220 / 220 | 217 / 3 / 0 (98.6%) | 213 / 7 / 0 (96.8%) |
| V3 | gold_ops | 0.1 | 220 / 220 | 210 / 10 / 0 (95.5%) | 208 / 12 / 0 (94.5%) |
| V3 | gold_ops | 0.2 | 220 / 220 | 200 / 19 / 1 (91.3%) | 192 / 27 / 1 (87.7%) |
| benign_degrading | gold_ops | 0.05 | 8 / 8 | 3 / 5 / 0 (37.5%) | 0 / 8 / 0 (0.0%) |
| benign_degrading | gold_ops | 0.1 | 8 / 8 | 3 / 5 / 0 (37.5%) | 0 / 8 / 0 (0.0%) |
| benign_degrading | gold_ops | 0.2 | 8 / 8 | 0 / 8 / 0 (0.0%) | 0 / 8 / 0 (0.0%) |
| V4qv | trap_ops | 0.05 | 55 / 55 | 53 / 2 / 0 (96.4%) | 50 / 5 / 0 (90.9%) |
| V4qv | trap_ops | 0.1 | 55 / 55 | 50 / 5 / 0 (90.9%) | 46 / 9 / 0 (83.6%) |
| V4qv | trap_ops | 0.2 | 55 / 55 | 44 / 11 / 0 (80.0%) | 39 / 16 / 0 (70.9%) |
| V4qv | gold_ops | 0.05 | 55 / 55 | 13 / 42 / 0 (23.6%) | 0 / 55 / 0 (0.0%) |
| V4qv | gold_ops | 0.1 | 55 / 55 | 8 / 47 / 0 (14.5%) | 0 / 55 / 0 (0.0%) |
| V4qv | gold_ops | 0.2 | 55 / 55 | 4 / 51 / 0 (7.3%) | 0 / 55 / 0 (0.0%) |
| benign_all | gold_ops | 0.05 | 800 / 800 | 147 / 653 / 0 (18.4%) | 0 / 800 / 0 (0.0%) |
| benign_all | gold_ops | 0.1 | 800 / 800 | 60 / 740 / 0 (7.5%) | 0 / 800 / 0 (0.0%) |
| benign_all | gold_ops | 0.2 | 800 / 800 | 21 / 779 / 0 (2.6%) | 0 / 800 / 0 (0.0%) |

## Checks

94661 assertions passed. Dispatch: 0 new units in 0.0 s on 2 worker(s) pinned to cores 8,9; 19281 recomputed objectives equal the logged ones to 1e-6 bh. Total wall 40.5 s.

