### Issuability at the late instant

### Issuability by class (published suite, closed rule; strict rule as subset)

| class | items | issuable | not issuable | not-issuable share | not issuable (strict) | median t_d (bh) | median |K| |
|---|---|---|---|---|---|---|---|
| benign | 800 | 623 | 177 | 22.1% | 341 | 16.8 | 908 |
| V1 | 160 | 160 | 0 | 0.0% | 9 | 0.0 | 1332 |
| V2 | 200 | 185 | 15 | 7.5% | 39 | 8.0 | 1412 |
| V3 | 220 | 154 | 66 | 30.0% | 173 | 31.4 | 838 |
| V4 | 220 | 201 | 19 | 8.6% | 95 | 31.7 | 831 |
| V5 | 200 | 200 | 0 | 0.0% | 25 | 0.0 | 1821 |
| V6 | 200 | 200 | 0 | 0.0% | 49 | 10.4 | 1342 |
| all | 2000 | 1723 | 277 | 13.9% | 731 | 9.2 | 1088 |

### Not issuable by stratum

| stratum | benign | V3 | V4 | all |
|---|---|---|---|---|
| Primary | 82 of 394 | 26 of 114 | 1 of 102 | 119 of 1009 |
| Confirmation | 36 of 153 | 13 of 41 | 1 of 40 | 51 of 386 |
| Buildings | 59 of 253 | 27 of 65 | 17 of 78 | 107 of 605 |

### Subclasses with excluded items (closed and strict rule)

| class | subclass | items | not issuable | not issuable (strict) |
|---|---|---|---|---|
| V1 | enum_invalid_trade | 10 | 0 | 4 |
| V1 | out_of_range_shift | 30 | 0 | 3 |
| V1 | unknown_op | 20 | 0 | 2 |
| V2 | frozen_order_edit | 40 | 0 | 17 |
| V2 | not_frozen | 25 | 0 | 1 |
| V2 | reorder_cycle | 60 | 15 | 21 |
| V3 | reorder_behind_batch_member | 15 | 10 | 15 |
| V3 | reorder_block_tight | 70 | 5 | 50 |
| V3 | reorder_cross_trade | 45 | 5 | 30 |
| V3 | reorder_two_successors | 45 | 44 | 45 |
| V3 | window_blocked_predecessor | 45 | 2 | 33 |
| V4 | objective_shifting | 40 | 0 | 19 |
| V4 | priority_instead_of_window | 25 | 0 | 1 |
| V4 | reorder_direction_flipped | 50 | 4 | 33 |
| V4 | sign_flipped_shift | 40 | 0 | 17 |
| V4 | wrong_building_same_trade | 15 | 5 | 11 |
| V4 | wrong_order_same_building | 25 | 10 | 14 |
| V5 | conflicting_directives | 40 | 0 | 25 |
| V6 | embedded_injection | 45 | 0 | 1 |
| V6 | instruction_override | 55 | 0 | 27 |
| V6 | role_confusion | 40 | 0 | 4 |
| V6 | schema_subversion | 25 | 0 | 17 |
| benign | dangling_building_id | 20 | 3 | 8 |
| benign | dangling_order_id | 60 | 0 | 34 |
| benign | enum_invalid_trade | 10 | 0 | 4 |
| benign | frozen_order_edit | 40 | 0 | 3 |
| benign | not_frozen | 25 | 0 | 12 |
| benign | objective_shifting | 40 | 0 | 19 |
| benign | out_of_range_shift | 30 | 0 | 3 |
| benign | priority_instead_of_window | 25 | 0 | 1 |
| benign | reorder_behind_batch_member | 15 | 3 | 8 |
| benign | reorder_block_tight | 70 | 62 | 64 |
| benign | reorder_cross_trade | 45 | 32 | 33 |
| benign | reorder_cycle | 60 | 18 | 24 |
| benign | reorder_direction_flipped | 50 | 4 | 33 |
| benign | reorder_two_successors | 45 | 45 | 45 |
| benign | sign_flipped_shift | 40 | 0 | 17 |
| benign | unknown_op | 20 | 0 | 2 |
| benign | unstaffed_trade | 20 | 3 | 5 |
| benign | window_blocked_predecessor | 45 | 2 | 3 |
| benign | wrong_building_same_trade | 15 | 5 | 11 |
| benign | wrong_order_same_building | 25 | 0 | 12 |

Subclasses with no decision-time reading (every item excluded): reorder_two_successors.

Twin-complete pairs (both members issuable): V3 69 of 220, V4 201 of 220. Held-out: 162 of 220 V3 items and 73 of 220 benign twins are issuable.

Items whose standing frozen set holds a planned order released after t_d and already on the calendar at t_d: 31 items, 31 of them issuable. Stage 2 freezes these orders on K (the frozen set is the running work plus every seed order K holds); N8's `known_frozen`, which keeps only queued and running seed orders, is used for the continuity assertion A6 only.

### Table 10 twin (late reading)

Stopped counts at t_d among issuable items; the right two columns give the published (t = 0) reading on the same issuable items and on all items.

| class | items | issuable | with a proposal | stopped at t_d | schema | feas. | quality | t=0 on issuable | t=0 all items |
|---|---|---|---|---|---|---|---|---|---|
| benign | 800 | 623 | 623 | 0 (0.0%) | 0 | 0 | 0 | 17 (2.7%) | 21 (2.6%) |
| V1 | 160 | 160 | 130 | 130 (81.2%) | 130 | 0 | 0 | 130 (81.2%) | 130 (81.2%) |
| V2 | 200 | 185 | 185 | 185 (100.0%) | 0 | 185 | 0 | 185 (100.0%) | 200 (100.0%) |
| V3 | 220 | 154 | 154 | 141 (91.6%) | 0 | 0 | 141 | 140 (90.9%) | 201 (91.4%) |
| V4 | 220 | 201 | 201 | 42 (20.9%) | 1 | 0 | 41 | 43 (21.4%) | 46 (20.9%) |
| V5 | 200 | 200 | 0 | 0 (0.0%) | 0 | 0 | 0 | 7 (3.5%) | 7 (3.5%) |
| V6 | 200 | 200 | 175 | 79 (39.5%) | 77 | 2 | 0 | 39 (19.5%) | 39 (19.5%) |

Benign stops at t_d by blocking code: none.

Terminal changes between t = 0 and t_d on issuable items, with the cause (an item counts under 'seed holds a planned order scheduled at t_d' when its standing frozen set holds a planned order released after t_d; under the Stage 2 frozen set that order is frozen on K):

| class | t = 0 terminal | t_d terminal | cause | items |
|---|---|---|---|---|
| V3 | applied_with_certificate | blocked_qual | other | 3 |
| V3 | blocked_qual | applied_with_certificate | other | 2 |
| V4 | applied_with_certificate | blocked_qual | other | 3 |
| V4 | applied_with_certificate | blocked_schema | other | 1 |
| V4 | blocked_qual | applied_with_certificate | other | 5 |
| V5 | blocked_qual | applied_with_certificate | other | 7 |
| V6 | applied_with_certificate | blocked_feas | other | 2 |
| V6 | applied_with_certificate | blocked_schema | other | 40 |
| V6 | blocked_qual | applied_with_certificate | other | 2 |
| V6 | blocked_qual | blocked_schema | other | 2 |
| benign | blocked_qual | applied_with_certificate | other | 17 |

V3 stopped share at t_d 91.6% (95% cluster bootstrap 85.2% to 96.8%, n = 154).

### Table 14 twin (late reading)


### Absolute reading (error = price - decision-time oracle cost on K)

| gate | n priced | median error | under | over | t=0 all (median / under / over) | t=0 issuable (median / under / over) |
|---|---|---|---|---|---|---|
| G-CERT | 1328 | 0.000 | 0.0% | 0.0% | 0.000 / 0.0% / 0.0% | 0.000 / 0.0% / 0.0% |
| G-CERT-M | 1328 | 0.000 | 0.2% | 0.0% | -0.010 / 19.5% / 0.0% | -0.011 / 20.6% / 0.0% |
| D-REL1 | 1328 | 0.000 | 2.0% | 3.5% | -0.010 / 21.7% / 1.5% | -0.011 / 22.7% / 1.7% |
| D-REL2 | 1328 | 0.000 | 0.2% | 0.0% | -0.011 / 21.2% / 0.0% | -0.012 / 22.2% / 0.0% |
| D-ABS | 1328 | 0.000 | 2.0% | 3.5% | -0.010 / 19.8% / 1.4% | -0.011 / 21.0% / 1.7% |

### Marginal reading (error = price - decision-time oracle cost on K)

| gate | n priced | median error | under | over | t=0 all (median / under / over) | t=0 issuable (median / under / over) |
|---|---|---|---|---|---|---|
| G-CERT | 1328 | 0.000 | 0.0% | 0.2% | 0.010 / 0.0% / 19.5% | 0.011 / 0.0% / 20.7% |
| G-CERT-M | 1328 | 0.000 | 0.0% | 0.0% | 0.000 / 0.0% / 0.0% | 0.000 / 0.0% / 0.0% |
| D-REL1 | 1328 | 0.000 | 1.9% | 3.5% | 0.000 / 2.4% / 1.7% | 0.000 / 2.2% / 2.0% |
| D-REL2 | 1328 | 0.000 | 0.0% | 0.1% | 0.000 / 1.5% / 0.1% | 0.000 / 1.2% / 0.1% |
| D-ABS | 1328 | 0.000 | 2.0% | 3.5% | 0.000 / 0.9% / 1.6% | 0.000 / 1.1% / 1.9% |

### Marginal under share by operation type

| gate | sequencing only | field changing | empty |
|---|---|---|---|
| G-CERT | 0.0% (n=542) | 0.0% (n=531) | 0.0% (n=255) |
| G-CERT-M | 0.0% (n=542) | 0.0% (n=531) | 0.0% (n=255) |
| D-REL1 | 0.0% (n=542) | 4.7% (n=531) | 0.0% (n=255) |
| D-REL2 | 0.0% (n=542) | 0.0% (n=531) | 0.0% (n=255) |
| D-ABS | 0.0% (n=542) | 4.9% (n=531) | 0.0% (n=255) |

Floor regime: 417 of 1328 priced rows (31.4%) have LB_K < 1 bh, so their certified gap is obj - LB in bh; 417 (31.4%) have an oracle lower end below 1 bh. bh-scale reading: median obj_K - LB_K 0.000 bh (p95 353.774), median obj_K - OPT_K 0.000 bh (p95 353.774), median D-ABS error 0.000 bh.

### Table 15 twin (late reading)

Anchor gap on K at t_d = (anchor dispatch of K - OPT_K)/max(OPT_K, 1), one value per issuable item (its (instance, t_d) board).

| stratum | items | anchor gap median | max | items with gap 0 | D-REL2 median error (abs) | D-REL2 median error (marg) |
|---|---|---|---|---|---|---|
| Pooled | 1723 | 0.000 | 0.206 | 1700 | 0.000 | 0.000 |
| Primary | 890 | 0.000 | 0.206 | 871 | 0.000 | 0.000 |
| Confirmation | 335 | 0.000 | 0.014 | 333 | 0.000 | 0.000 |
| Buildings | 498 | 0.000 | 0.023 | 496 | 0.000 | 0.000 |

Certificate referrals at tau = 0.20 that the marginal certificate removes (t_d):

| class | G-CERT referred | G-CERT-M referred | removed | added | explained by anchor gap |
|---|---|---|---|---|---|
| benign | 0 | 0 | 0 | 0 | 0 |
| V3 | 141 | 141 | 0 | 0 | 0 |
| all | 182 | 182 | 0 | 0 | 0 |

### Table 16 twin (late reading)


### Panel: pricing (decision-time oracle on K)

| stratum | delta | D-REL2 miss (abs) | G-CERT miss (abs) | G-CERT-M miss (abs) | G-CERT false ref. (marg) | G-CERT-M miss (marg) | Union false ref. (marg) |
|---|---|---|---|---|---|---|---|
| Pooled | 0.1 | 0.0% (0/192) | 5.2% (10/192) | 5.2% (10/192) | 0.0% (0/1136) | 5.2% (10/192) | 0.7% (8/1136) |
| Pooled | 0.2 | 0.0% (0/182) | 0.0% (0/182) | 0.0% (0/182) | 0.0% (0/1146) | 0.0% (0/182) | 1.6% (18/1146) |
| Primary | 0.1 | 0.0% (0/110) | 4.5% (5/110) | 4.5% (5/110) | 0.0% (0/585) | 4.5% (5/110) | 0.9% (5/585) |
| Primary | 0.2 | 0.0% (0/105) | 0.0% (0/105) | 0.0% (0/105) | 0.0% (0/590) | 0.0% (0/105) | 1.7% (10/590) |
| Confirmation | 0.1 | 0.0% (0/36) | 5.6% (2/36) | 5.6% (2/36) | 0.0% (0/218) | 5.6% (2/36) | 0.5% (1/218) |
| Confirmation | 0.2 | 0.0% (0/34) | 0.0% (0/34) | 0.0% (0/34) | 0.0% (0/220) | 0.0% (0/34) | 1.4% (3/220) |
| Buildings | 0.1 | 0.0% (0/46) | 6.5% (3/46) | 6.5% (3/46) | 0.0% (0/333) | 6.5% (3/46) | 0.6% (2/333) |
| Buildings | 0.2 | 0.0% (0/43) | 0.0% (0/43) | 0.0% (0/43) | 0.0% (0/336) | 0.0% (0/43) | 1.5% (5/336) |

### Panel: consequence (realised marginal cost, full window)

| stratum | delta | D-REL2 miss (abs) | G-CERT miss (abs) | G-CERT-M miss (abs) | G-CERT false ref. (marg) | G-CERT-M miss (marg) | Union false ref. (marg) |
|---|---|---|---|---|---|---|---|
| Pooled | 0.1 | 35.6% (105/295) | 38.3% (113/295) | 38.3% (113/295) | 0.0% (0/1124) | 10.3% (21/203) | 1.2% (13/1124) |
| Pooled | 0.2 | 20.5% (46/224) | 21.9% (49/224) | 21.9% (49/224) | 1.2% (14/1144) | 8.2% (15/182) | 2.8% (32/1144) |
| Primary | 0.1 | 47.6% (99/208) | 49.5% (103/208) | 49.5% (103/208) | 0.0% (0/577) | 11.0% (13/118) | 1.4% (8/577) |
| Primary | 0.2 | 28.3% (41/145) | 30.3% (44/145) | 30.3% (44/145) | 1.9% (11/591) | 9.7% (10/103) | 3.6% (21/591) |
| Confirmation | 0.1 | 10.3% (4/39) | 12.8% (5/39) | 12.8% (5/39) | 0.0% (0/216) | 10.5% (4/38) | 0.9% (2/216) |
| Confirmation | 0.2 | 8.1% (3/37) | 8.1% (3/37) | 8.1% (3/37) | 0.0% (0/217) | 8.1% (3/37) | 1.4% (3/217) |
| Buildings | 0.1 | 4.2% (2/48) | 10.4% (5/48) | 10.4% (5/48) | 0.0% (0/331) | 8.5% (4/47) | 0.9% (3/331) |
| Buildings | 0.2 | 4.8% (2/42) | 4.8% (2/42) | 4.8% (2/42) | 0.9% (3/336) | 4.8% (2/42) | 2.4% (8/336) |

### Delta sweep: each gate at threshold = delta (marginal reading, pricing truth)

| gate | delta 0.05 | delta 0.10 | delta 0.20 |
|---|---|---|---|
| G-CERT | TPR 100.0% (n=197), FPR 0.2% (n=1131) | TPR 100.0% (n=192), FPR 0.0% (n=1136) | TPR 100.0% (n=182), FPR 0.0% (n=1146) |
| G-CERT-M | TPR 100.0% (n=197), FPR 0.0% (n=1131) | TPR 100.0% (n=192), FPR 0.0% (n=1136) | TPR 100.0% (n=182), FPR 0.0% (n=1146) |
| D-REL2 | TPR 100.0% (n=197), FPR 0.0% (n=1131) | TPR 100.0% (n=192), FPR 0.0% (n=1136) | TPR 100.0% (n=182), FPR 0.0% (n=1146) |
| D-REL1 | TPR 100.0% (n=197), FPR 4.1% (n=1131) | TPR 100.0% (n=192), FPR 4.0% (n=1136) | TPR 100.0% (n=182), FPR 3.8% (n=1146) |

### Dispositions at the frozen settings (absolute pricing truth, all classes)

| gate | delta 0.10 | delta 0.20 |
|---|---|---|
| G-CERT | miss 5.2% of 192 costly, false ref. 0.0% of 1136 cheap | miss 0.0% of 182 costly, false ref. 0.0% of 1146 cheap |
| G-CERT-M | miss 5.2% of 192 costly, false ref. 0.0% of 1136 cheap | miss 0.0% of 182 costly, false ref. 0.0% of 1146 cheap |
| D-REL1 | miss 0.0% of 192 costly, false ref. 4.8% of 1136 cheap | miss 0.0% of 182 costly, false ref. 5.7% of 1146 cheap |
| D-REL2 | miss 0.0% of 192 costly, false ref. 0.7% of 1136 cheap | miss 0.0% of 182 costly, false ref. 1.6% of 1146 cheap |
| D-ABS | miss 0.0% of 192 costly, false ref. 4.9% of 1136 cheap | miss 0.0% of 182 costly, false ref. 5.8% of 1146 cheap |
| G-CERT-M|D-REL2 | miss 0.0% of 192 costly, false ref. 0.7% of 1136 cheap | miss 0.0% of 182 costly, false ref. 1.6% of 1146 cheap |

### Table S10 twin (late reading, direct)

Direct benchmark, issuable items. Applied = priced on K with G-CERT <= tau. Damage = realised original-field tardiness from t_d minus the published anchor (bh). g_orig on K = (original-field obj_K - LB_K of the unadjusted K)/max(., 1). The last column is the published (t = 0) reading on the same items: quality-reaching / applied / damage > 10 bh / g_orig above tau.

| class | split | items | priced on K | applied | damage > 2 bh | damage > 10 bh | max damage (bh) | g_orig_K > tau | t = 0 reading |
|---|---|---|---|---|---|---|---|---|---|
| benign | field_changing | 313 | 313 | 313 | 0 | 0 | 1.26 | 0 | 313 / 304 / 0 / 2 |
| benign | sequencing_only | 310 | 310 | 310 | 0 | 0 | 0.34 |  | 310 / 302 / 1 / - |
| V3 | field_changing | 43 | 43 | 0 | 0 | 0 | n/a | 0 | 43 / 0 / 0 / 0 |
| V3 | sequencing_only | 111 | 111 | 13 | 13 | 13 | 144.43 |  | 111 / 14 / 14 / - |
| V4 | field_changing | 120 | 120 | 120 | 36 | 34 | 320.00 | 24 | 120 / 116 / 32 / 19 |
| V4 | sequencing_only | 81 | 80 | 39 | 5 | 5 | 313.26 |  | 81 / 42 / 7 / - |
| other | field_changing | 270 | 55 | 55 | 0 | 0 | 0.00 | 1 | 55 / 55 / 0 / 2 |
| other | sequencing_only | 220 | 41 | 41 | 0 | 0 | 0.00 |  | 85 / 81 / 0 / - |

### Section 5.1 twin (late reading, direct)

Mean realised damage per issuable instruction (bh, original fields, 95% cluster bootstrap over instances); a referred or refused proposal adds 0. D-REL2 at its DG14 setting on the G-FEAS base; t = 0 reading on the same items in parentheses (D-REL2 there uses the N2 price).

| class | items | G-FEAS | G-CERT | G-CERT-M | D-REL2 (0.02) | G-CERT-M or D-REL2 |
|---|---|---|---|---|---|---|
| V3 | 154 | 326.08 [256.33, 399.43] (t=0: 326.08) | 3.60 [0.94, 7.62] (t=0: 5.09) | 3.60 [0.94, 7.62] (t=0: 12.11) | 0.00 [0.00, 0.00] (t=0: 0.40) | 0.00 [0.00, 0.00] (t=0: 0.40) |
| benign | 623 | -0.02 [-0.06, 0.00] (t=0: -1.86) | -0.02 [-0.06, 0.00] (t=0: -1.85) | -0.02 [-0.06, 0.00] (t=0: -1.86) | -0.02 [-0.06, 0.00] (t=0: -1.86) | -0.02 [-0.06, 0.00] (t=0: -1.86) |
| V4 | 201 | 90.26 [69.36, 111.41] (t=0: 90.26) | 25.35 [16.92, 34.53] (t=0: 26.50) | 25.35 [16.92, 34.53] (t=0: 29.60) | 22.91 [14.77, 31.60] (t=0: 22.92) | 22.91 [14.77, 31.60] (t=0: 22.92) |
| all | 1723 | 39.67 [31.07, 48.96] (t=0: 38.98) | 3.27 [2.22, 4.43] (t=0: 2.86) | 3.27 [2.22, 4.43] (t=0: 3.85) | 2.66 [1.70, 3.69] (t=0: 2.02) | 2.66 [1.70, 3.69] (t=0: 2.02) |

### Oracle coverage (late reading)

| stratum | boards needed | bracketed | proved | width median | width p95 | width max |
|---|---|---|---|---|---|---|
| Pooled | 1337 | 1337 | 1337 | 0.00% | 0.00% | 0.22% |
| Primary | 706 | 706 | 706 | 0.00% | 0.00% | 0.22% |
| Confirmation | 260 | 260 | 260 | 0.00% | 0.00% | 0.02% |
| Buildings | 371 | 371 | 371 | 0.00% | 0.00% | 0.00% |

relaxed trade solves: 59 rows, statuses {'OPTIMAL': 59}; solved 59 in 44 s (median 0.0 s, p95 3.3 s, max 3.9 s); cpu_share median 0.36, solve_cpu_share median 0.39 (min 0.20), foreign_share median 0.000 (max 0.533). Wall by size: <=150 n=41 median 0.0s max 2.2s, <=400 n=15 median 1.8s max 3.9s, <=700 n=1 median 2.6s max 2.6s, <=1500 n=2 median 2.2s max 2.2s.

constrained (c) solves: 449 rows, statuses {'OPTIMAL': 289, 'CLOSED': 137, 'UNKNOWN': 11, 'FEASIBLE': 12}; solved 312 in 2481 s (median 2.0 s, p95 61.0 s, max 62.3 s); cpu_share median 0.46, solve_cpu_share median 0.50 (min 0.21), foreign_share median 0.002 (max 0.657). Wall by size: <=150 n=98 median 0.2s max 4.0s, <=400 n=113 median 2.0s max 5.5s, <=700 n=50 median 2.6s max 10.8s, <=1500 n=21 median 28.2s max 61.0s, >1500 n=30 median 57.6s max 62.3s.
Budget-limited rows (not proved): 23, smallest 922 orders, foreign_share max 0.012; 11 of them used about one of the four workers for the whole budget (solve_cpu_share about 0.25, CP-SAT still in its single-threaded presolve), so their brackets are the relaxed lower bound against the ATC upper bound.

cpu_share is not the contention test for CP-SAT: its search workers idle in presolve and on small or nearly closed models, so an uncontended budget-limited solve reads 0.4 to 0.7 (oracle_v1 median solve_cpu_share 0.68 on proved rows; N9 0.41 to 0.43). The test is foreign_share, the busy CPU other processes took on cores 8-11 during the solve; a budget-limited row above 0.10 is invalid and solved again (at most twice).

### What changed against the published reading (late)

Each headline number of the twins: the published reading (t = 0, all items), the same reading on the issuable items, and the decision-time reading. 'sign' marks a signed quantity whose sign changes.

| quantity | t = 0, all | t = 0, issuable | t_d | t_d - t = 0 | flag |
|---|---|---|---|---|---|
| Items not issuable (closed rule) | n/a | n/a | 277 |  |  |
| Table 10: benign stopped share | 2.6% | 2.7% | 0.0% | -2.6% |  |
| Table 10: V1 stopped share | 81.2% | 81.2% | 81.2% | 0.0% |  |
| Table 10: V2 stopped share | 100.0% | 100.0% | 100.0% | 0.0% |  |
| Table 10: V3 referral share (stopped) | 91.4% | 90.9% | 91.6% | 0.2% |  |
| Table 10: V4 stopped share | 20.9% | 21.4% | 20.9% | -0.0% |  |
| Table 10: V6 stopped share | 19.5% | 19.5% | 39.5% | 20.0% |  |
| Table 14 absolute: G-CERT under share | 0.0% | 0.0% | 0.0% | 0.0% |  |
| Table 14 absolute: G-CERT median error | 0.000 | 0.000 | 0.000 | 0.000 |  |
| Table 14 absolute: G-CERT-M under share | 19.5% | 20.6% | 0.2% | -19.4% |  |
| Table 14 absolute: G-CERT-M median error | -0.010 | -0.011 | 0.000 | 0.010 | sign |
| Table 14 absolute: D-REL1 under share | 21.7% | 22.7% | 2.0% | -19.7% |  |
| Table 14 absolute: D-REL1 median error | -0.010 | -0.011 | 0.000 | 0.010 | sign |
| Table 14 absolute: D-REL2 under share | 21.2% | 22.2% | 0.2% | -21.1% |  |
| Table 14 absolute: D-REL2 median error | -0.011 | -0.012 | 0.000 | 0.011 | sign |
| Table 14 absolute: D-ABS under share | 19.8% | 21.0% | 2.0% | -17.8% |  |
| Table 14 absolute: D-ABS median error | -0.010 | -0.011 | 0.000 | 0.010 | sign |
| Table 14 marginal: G-CERT under share | 0.0% | 0.0% | 0.0% | 0.0% |  |
| Table 14 marginal: G-CERT median error | 0.010 | 0.011 | 0.000 | -0.010 | sign |
| Table 14 marginal: G-CERT-M under share | 0.0% | 0.0% | 0.0% | 0.0% |  |
| Table 14 marginal: G-CERT-M median error | 0.000 | 0.000 | 0.000 | 0.000 |  |
| Table 14 marginal: D-REL1 under share | 2.4% | 2.2% | 1.9% | -0.5% |  |
| Table 14 marginal: D-REL1 median error | 0.000 | 0.000 | 0.000 | 0.000 |  |
| Table 14 marginal: D-REL2 under share | 1.5% | 1.2% | 0.0% | -1.5% |  |
| Table 14 marginal: D-REL2 median error | 0.000 | 0.000 | 0.000 | 0.000 |  |
| Table 14 marginal: D-ABS under share | 0.9% | 1.1% | 2.0% | 1.0% |  |
| Table 14 marginal: D-ABS median error | 0.000 | 0.000 | 0.000 | 0.000 |  |
| Table 15: benign G-CERT referrals | n/a | n/a | 0 |  |  |
| Table 15: pooled anchor-gap median | n/a | n/a | 0.0% |  |  |
| Table 16 pooled delta 0.10: D-REL2 miss, pricing truth | 29.1% | n/a | 0.0% | -29.1% |  |
| Table 16 pooled delta 0.10: D-REL2 miss, consequence truth | 29.1% | n/a | 35.6% | 6.5% |  |
| Table 16 pooled delta 0.10: G-CERT miss, pricing truth | 22.7% | n/a | 5.2% | -17.5% |  |
| Table 16 pooled delta 0.10: G-CERT miss, consequence truth | 22.7% | n/a | 38.3% | 15.6% |  |
| Table 16 pooled delta 0.10: G-CERT-M miss, pricing truth | 35.7% | n/a | 5.2% | -30.5% |  |
| Table 16 pooled delta 0.10: G-CERT-M miss, consequence truth | 35.7% | n/a | 38.3% | 2.6% |  |
| Table 16 pooled delta 0.10: G-CERT false referral (marg), pricing truth | 2.8% | n/a | 0.0% | -2.8% |  |
| Table 16 pooled delta 0.10: G-CERT false referral (marg), consequence truth | 2.8% | n/a | 0.0% | -2.8% |  |
| 5.1 direct V3 mean damage under G-FEAS (bh) | n/a | 326.083 | 326.083 | 0.000 |  |
| 5.1 direct V3 mean damage under G-CERT (bh) | n/a | 5.086 | 3.598 | -1.488 |  |

- Table 14 absolute under-share order of the gates changes from G-CERT (0.0%) < G-CERT-M (19.5%) < D-ABS (19.8%) < D-REL2 (21.2%) < D-REL1 (21.7%) (t = 0) to G-CERT (0.0%) < D-REL2 (0.2%) < G-CERT-M (0.2%) < D-REL1 (2.0%) < D-ABS (2.0%) (t_d).
- Table 14 marginal under-share order of the gates changes from G-CERT (0.0%) < G-CERT-M (0.0%) < D-ABS (0.9%) < D-REL2 (1.5%) < D-REL1 (2.4%) (t = 0) to D-REL2 (0.0%) < G-CERT (0.0%) < G-CERT-M (0.0%) < D-REL1 (1.9%) < D-ABS (2.0%) (t_d).

