# N8. Decision-time (causal) certificate

Generated 2026-11-03T18:24:57+0800 by `code/scripts/n8_causal.py` (l1-n8-causal-1). 13253 assertions passed; wall time 911.3 s on cores 8-9 (2 workers); deterministic, no time budget.

## What was computed

- Items: every suite item with a non-empty canonical proposal (benign `gold_ops`, V1 and V2 `literal_ops`, V3 `gold_ops`, V4 `trap_ops`, V6 `forbidden_ops`; V5 has none), 1745 items on 60 instances.
- Decision instant t_d: the largest release time over the orders the operations name (`order_id`, `ref_order_id`; for `batch` the members of the named building-and-trade group). Identifiers absent from the instance contribute nothing; a proposal naming no order has t_d = 0.
- Site state at t_d from the published baseline trajectory (ATC, seed 0, the item's frozen set pinned): completed (end <= t_d), in progress (start < t_d < end), queued (released by t_d, not started), unknown (released after t_d). Known set K = queued + in progress.
- Causal price: the guard's schema and feasibility stages on K, with the in-progress orders added to the standing frozen set; dispatch of K from t_d (unfrozen releases raised to t_d for the dispatcher only); g_c = (obj_K - LB_K) / max(LB_K, 1), where LB_K is the in-progress orders' fixed weighted tardiness plus LB2 at t = t_d on the other orders with each technician available when its running job ends. Anchor g_anchor_K: the same with no operations; marginal price m_c = g_c - g_anchor_K.
- Stale: an operation names an order that is completed at t_d. On K that identifier no longer exists, so the guard's schema stage refuses it as a dangling id.
- Planned-known reading (sensitivity): planned-maintenance orders (`is_pm`) are on the site's calendar from t = 0, so a named planned order does not delay t_d, and a planned order released after t_d stays in K with its own release.
- Lenient reading (sensitivity): in-progress orders stay pinned to their slot but are not protected by the guard's frozen-edit rule; a precedence edge into a running order is then recorded and has no effect.
- Realised cost: the full instance with every order started before t_d pinned to its baseline slot, the proposal applied at t_d (batch groups restricted to the members known at t_d), later orders released as they come. Absolute realised cost (W_with - OPT) / max(OPT, 1) with OPT the oracle bracket's lower end of the adjusted instance (midpoint when the bracket is a point, as in N2); marginal realised cost = that minus the same quantity for the no-proposal run on the baseline bracket.
- Dispositions at tau = 0.20: applied (price <= tau), referred (price > tau), refused at the schema or feasibility stage. Full-information dispositions: DG1 G_CERT canonical certified gap (absolute) and that gap minus the published anchor gap of `analysis/ladder/rule_anchor.json` (marginal).
- Intervals: 95% instance-cluster bootstrap, B = 2000, over the instances that carry items of the cell.

## Assertions

- Suite SHA-256 0a0b471f4d04ba03 ; all 60 instance files verified against the instances_v10 manifest by `suite_gate.instance_path`.
- Baseline trajectory with each item's frozen set places every order at the plain Y1 ATC dispatch's start and end on all 116 (instance, frozen set) groups; on 1 of them some orders sit on a different, identical technician of the same trade, and running work is pinned to the trajectory's technician.
- Omniscient reading of the causal code (full instance, t_d = 0) reproduces DG1's G_CERT terminal on all 1745 items and its certified gap on all 1380 priced items (tolerance 1e-6).
- No-proposal realised run (prefix pinned, continuation from t_d) equals the published anchor objective on every item (1e-6 bh).
- LB_K <= obj_K on every causal certificate and every causal anchor.

## Table 1. Disposition agreement, causal vs full information (tau = 0.20)

| Class | Stratum | n | stale | names running work | agree abs | agree marg | agree abs, both priced (n) | agree marg, both priced | agree abs lenient | agree marg lenient |
|---|---|---|---|---|---|---|---|---|---|---|
| all | all | 1745 | 16.2% | 24.6% | 63.0% [59.6%, 66.3%] | 64.1% [61.2%, 67.2%] | 97.5% (788) | 100.0% | 73.6% | 75.5% |
| all | c09_storm2_w80 | 867 | 21.7% | 23.1% | 61.0% [55.7%, 65.6%] | 63.3% [59.6%, 66.9%] | 94.9% (392) | 100.0% | 68.5% | 72.4% |
| all | c10_storm2_w80 | 335 | 13.7% | 31.0% | 63.6% [57.6%, 69.6%] | 63.6% [57.6%, 69.5%] | 100.0% (148) | 100.0% | 73.1% | 73.1% |
| all | c10_replay_400 | 543 | 8.8% | 23.2% | 65.7% [59.3%, 73.2%] | 65.7% [59.1%, 72.8%] | 100.0% (248) | 100.0% | 82.0% | 82.0% |
| benign | all | 800 | 20.1% | 21.9% | 59.2% [55.3%, 63.1%] | 60.8% [57.4%, 64.1%] | 97.5% (486) | 100.0% | 77.9% | 79.8% |
| V1 | all | 130 | 0.0% | 0.0% | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | -- (0) | -- | 100.0% | 100.0% |
| V2 | all | 200 | 17.0% | 6.0% | 83.0% [78.9%, 87.1%] | 83.0% [79.2%, 86.8%] | -- (0) | -- | 83.0% | 83.0% |
| V3 | all | 220 | 34.1% | 77.7% | 0.0% [0.0%, 0.0%] | 0.0% [0.0%, 0.0%] | -- (0) | -- | 9.1% | 12.7% |
| V4 | all | 220 | 5.5% | 17.3% | 71.8% [66.5%, 76.6%] | 73.6% [69.5%, 77.8%] | 97.5% (162) | 100.0% | 79.1% | 82.3% |
| V6 | all | 175 | 0.0% | 19.4% | 97.7% [94.3%, 100.0%] | 100.0% [100.0%, 100.0%] | 97.1% (140) | 100.0% | 97.7% | 100.0% |

## Table 1b. Sensitivity readings

Live: items that are not stale (every named order still open at t_d). Planned known: planned-maintenance orders are on the calendar from t = 0, so they neither delay t_d nor leave K.

| Class | n | agree abs, live (n) | agree marg, live | stale, planned known | agree abs, planned known | agree marg, planned known | referred abs, planned known | refused, planned known | median t_d, planned known |
|---|---|---|---|---|---|---|---|---|---|
| all | 1745 | 75.1% (1463) | 76.5% | 6.5% | 79.7% [76.8%, 82.3%] | 80.6% [78.5%, 82.6%] | 10.5% | 36.1% | 0.9 |
| benign | 800 | 74.2% (639) | 76.1% | 10.0% | 74.9% [71.0%, 78.1%] | 77.0% [74.6%, 79.4%] | 0.0% | 23.0% | 1.7 |
| V1 | 130 | 100.0% (130) | 100.0% | 0.0% | 100.0% [100.0%, 100.0%] | 100.0% [100.0%, 100.0%] | 0.0% | 100.0% | 0.0 |
| V2 | 200 | 100.0% (166) | 100.0% | 6.5% | 82.0% [77.7%, 86.4%] | 82.0% [77.5%, 86.6%] | 0.0% | 88.5% | 0.0 |
| V3 | 220 | 0.0% (145) | 0.0% | 9.1% | 67.7% [60.5%, 74.1%] | 65.9% [58.8%, 72.0%] | 64.1% | 30.0% | 32.4 |
| V4 | 220 | 76.0% (208) | 77.9% | 0.5% | 93.6% [89.5%, 97.2%] | 94.5% [91.1%, 97.7%] | 19.1% | 3.2% | 9.3 |
| V6 | 175 | 97.7% (175) | 100.0% | 0.0% | 81.1% [77.0%, 85.4%] | 82.3% [78.9%, 86.2%] | 0.0% | 37.7% | 0.0 |

## Table 2. Dispositions by reading

| Class | Stratum | n | referred full abs | referred causal abs | referred causal abs lenient | referred full marg | referred causal marg | applied full abs | applied causal abs | refused causal (schema or feas) |
|---|---|---|---|---|---|---|---|---|---|---|
| all | all | 1745 | 15.6% | 0.0% | 0.2% | 13.3% | 0.0% | 63.5% | 45.2% | 54.8% |
| benign | all | 800 | 2.6% | 0.0% | 0.0% | 0.0% | 0.0% | 97.4% | 60.8% | 39.2% |
| V1 | all | 130 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% |
| V2 | all | 200 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% |
| V3 | all | 220 | 91.4% | 0.0% | 1.4% | 87.7% | 0.0% | 8.6% | 0.0% | 100.0% |
| V4 | all | 220 | 20.9% | 0.0% | 0.0% | 17.7% | 0.0% | 79.1% | 73.6% | 26.4% |
| V6 | all | 175 | 2.3% | 0.0% | 0.0% | 0.0% | 0.0% | 77.7% | 80.0% | 20.0% |
| benign | c09_storm2_w80 | 394 | 5.3% | 0.0% | 0.0% | 0.0% | 0.0% | 94.7% | 61.2% | 38.8% |
| benign | c10_storm2_w80 | 153 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 58.8% | 41.2% |
| benign | c10_replay_400 | 253 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 100.0% | 61.3% | 38.7% |
| V3 | c09_storm2_w80 | 114 | 94.7% | 0.0% | 0.0% | 87.7% | 0.0% | 5.3% | 0.0% | 100.0% |
| V3 | c10_storm2_w80 | 41 | 92.7% | 0.0% | 0.0% | 92.7% | 0.0% | 7.3% | 0.0% | 100.0% |
| V3 | c10_replay_400 | 65 | 84.6% | 0.0% | 4.6% | 84.6% | 0.0% | 15.4% | 0.0% | 100.0% |

## Table 3. Causal price against the realised cost

Error = price minus realised cost, on items the causal guard prices and the oracle covers. The full-information rows compare the published certificate with the cost of its own (full-information) schedule.

| Class | Stratum | n priced | abs p05 | abs median | abs p95 | marg p05 | marg median | marg p95 | marg under -5 pts | n priced, planned known | marg median, planned known | marg p95, planned known | full-info abs median | full-info marg median | full-info marg p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | all | 772 | -14.8% | -1.1% | 0.0% | -0.5% | 0.0% | 0.1% | 2.8% | 1083 | 0.0% | 63.6% | 0.0% | 0.0% | 0.0% |
| benign | all | 475 | -22.4% | -1.2% | 0.0% | -1.6% | 0.0% | 0.0% | 4.2% | 610 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| V1 | all | 0 | -- | -- | -- | -- | -- | -- | -- | 0 | -- | -- | -- | -- | -- |
| V2 | all | 0 | -- | -- | -- | -- | -- | -- | -- | 0 | -- | -- | -- | -- | -- |
| V3 | all | 0 | -- | -- | -- | -- | -- | -- | -- | 154 | 20.3% | 190.1% | 0.0% | 0.0% | 0.0% |
| V4 | all | 157 | -10.4% | -0.8% | 0.0% | -0.4% | 0.0% | 0.3% | 0.6% | 210 | 0.0% | 70.0% | 0.0% | 0.0% | 0.0% |
| V6 | all | 140 | -12.4% | -1.1% | 0.0% | -0.0% | 0.0% | 0.2% | 0.7% | 109 | 0.0% | 0.6% | 0.0% | -0.0% | 0.0% |
| all | c09_storm2_w80 | 392 | -22.7% | -4.3% | -0.9% | -1.4% | 0.0% | 0.6% | 4.1% | 547 | 0.0% | 110.2% | 0.0% | 0.0% | 0.0% |
| all | c10_storm2_w80 | 148 | -9.0% | -0.2% | 0.0% | -0.1% | 0.0% | 0.0% | 2.7% | 199 | 0.0% | 33.5% | 0.0% | -0.0% | 0.0% |
| all | c10_replay_400 | 232 | -1.6% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.9% | 337 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

## Table 4. Information at the decision instant

| Class | Stratum | n | median t_d (bh) | median known set | median queue | median share unknown |
|---|---|---|---|---|---|---|
| all | all | 1745 | 18.1 | 181 | 98 | 39.8% |
| benign | all | 800 | 25.8 | 192 | 112 | 38.8% |
| V1 | all | 130 | 0.0 | 25 | 14 | 94.8% |
| V2 | all | 200 | 10.3 | 154 | 60 | 66.0% |
| V3 | all | 220 | 78.9 | 346 | 267 | 1.0% |
| V4 | all | 220 | 35.6 | 210 | 120 | 25.5% |
| V6 | all | 175 | 0.3 | 39 | 21 | 91.8% |
| all | c09_storm2_w80 | 867 | 48.5 | 207 | 123 | 39.7% |
| all | c10_storm2_w80 | 335 | 34.0 | 549 | 437 | 57.0% |
| all | c10_replay_400 | 543 | 2.6 | 76 | 28 | 34.0% |

## Table 5. Causal refusal codes (primary reading)

| Class | code | items |
|---|---|---|
| benign | dangling_order_id | 161 |
| benign | frozen_order_edit | 153 |
| benign | dangling_building_id | 2 |
| benign | frozen_window_conflict | 1 |
| V1 | dangling_order_id | 60 |
| V1 | release_shift_out_of_range | 30 |
| V1 | dangling_building_id | 28 |
| V1 | unknown_trade | 20 |
| V2 | frozen_window_conflict | 90 |
| V2 | frozen_order_edit | 52 |
| V2 | dangling_order_id | 34 |
| V2 | precedence_cycle | 26 |
| V2 | not_frozen | 25 |
| V2 | trade_mismatch | 25 |
| V3 | frozen_order_edit | 145 |
| V3 | dangling_order_id | 75 |
| V3 | dangling_building_id | 3 |
| V3 | frozen_precedence_conflict | 2 |
| V4 | frozen_order_edit | 46 |
| V4 | dangling_order_id | 12 |
| V6 | dangling_order_id | 35 |

## Table 6. Transitions, full-information to causal (absolute reading)

| Class | full information | causal | items |
|---|---|---|---|
| benign | applied | applied | 474 |
| benign | applied | refused_schema | 155 |
| benign | applied | refused_feas | 150 |
| benign | referred | applied | 12 |
| benign | referred | refused_schema | 6 |
| benign | referred | refused_feas | 3 |
| V1 | refused_schema | refused_schema | 130 |
| V2 | refused_feas | refused_feas | 166 |
| V2 | refused_feas | refused_schema | 34 |
| V3 | referred | refused_feas | 128 |
| V3 | referred | refused_schema | 73 |
| V3 | applied | refused_feas | 17 |
| V3 | applied | refused_schema | 2 |
| V4 | applied | applied | 158 |
| V4 | referred | refused_feas | 30 |
| V4 | applied | refused_feas | 16 |
| V4 | referred | refused_schema | 12 |
| V4 | referred | applied | 4 |
| V6 | applied | applied | 136 |
| V6 | refused_schema | refused_schema | 35 |
| V6 | referred | applied | 4 |

## Table 7. Added damage in weighted business hours

Predicted added damage = obj_K(proposal) - obj_K(no proposal) at t_d; realised added damage = W_full(proposal at t_d) - W_full(baseline). Error = predicted - realised, on items the causal guard prices. Under 2 bh / 10 bh: share with the prediction below the realised damage by more than 2 bh / 10 bh. Spearman: rank correlation of predicted and realised added damage.

| Class | reading | n | median (bh) | p05 (bh) | p95 (bh) | under 2 bh | under 10 bh | Spearman |
|---|---|---|---|---|---|---|---|---|
| all | primary | 772 | 0.00 | -0.00 | 0.00 | 0.9% | 0.1% | 0.85 |
| all | planned known | 1083 | 0.00 | -23.47 | 0.00 | 10.0% | 7.9% | 0.96 |
| benign | primary | 475 | 0.00 | -0.00 | 0.00 | 0.6% | 0.2% | 0.87 |
| benign | planned known | 610 | 0.00 | 0.00 | 0.00 | 0.5% | 0.2% | 0.84 |
| V1 | primary | 0 | -- | -- | -- | -- | -- | -- |
| V1 | planned known | 0 | -- | -- | -- | -- | -- | -- |
| V2 | primary | 0 | -- | -- | -- | -- | -- | -- |
| V2 | planned known | 0 | -- | -- | -- | -- | -- | -- |
| V3 | primary | 0 | -- | -- | -- | -- | -- | -- |
| V3 | planned known | 154 | -1.68 | -95.25 | 2.30 | 48.1% | 39.0% | 0.99 |
| V4 | primary | 157 | 0.00 | -0.00 | 0.24 | 1.3% | 0.0% | 0.76 |
| V4 | planned known | 210 | 0.00 | -58.62 | 0.92 | 14.3% | 11.9% | 0.94 |
| V6 | primary | 140 | 0.00 | -0.00 | 0.00 | 1.4% | 0.0% | 0.93 |
| V6 | planned known | 109 | 0.00 | 0.00 | 0.00 | 0.9% | 0.0% | 1.00 |

## Table 8. Planned-known reading: dispositions and the damage of applied items

| Class | n | applied | referred | refused | refusal codes | applied with realised damage (n) | median damage (bh) | max damage (bh) | applied above 2 bh |
|---|---|---|---|---|---|---|---|---|---|
| V3 | 220 | 13 | 141 | 66 | frozen_order_edit 46, dangling_order_id 20, dangling_building_id 3, frozen_precedence_conflict 1 | 13 | 23.76 | 144.43 | 13 |
| benign | 800 | 616 | 0 | 184 | frozen_order_edit 91, dangling_order_id 80, not_frozen 13 | 610 | 0.00 | 320.00 | 35 |
| V4 | 220 | 171 | 42 | 7 | frozen_order_edit 6, dangling_order_id 1 | 168 | 0.00 | 313.26 | 6 |

V3 under the planned-known reading: 5 of 220 items (2.3%) have t_d = 0 (every named order is planned maintenance); the median t_d of the other 215 is 35.9 bh.

