# N6. Sensitivity of the anchor gap and of D-REL2's pricing to the dispatching rule

Generated 2026-10-26T08:18:53+08:00 by `code/scripts/n6_rule_sensitivity.py` (l1-n6-rule-sensitivity-1). 47802 assertions passed; dispatch wall time 882.0 s on cores 8-11 (4 workers, one numerical thread each); deterministic, no time budget.

## What was computed

- Rules (the environment's own `fmwos.pdrs` pick functions, seed 0): `atc` (ATC, k = 2 (published)); `edd` (Earliest due date); `wspt` (Weighted shortest processing time); `pfifo` (Priority class, then first in first out); `wmdd` (Weighted modified due date); `atc_k1` (ATC, k = 1); `atc_k3` (ATC, k = 3).
- Anchor gap of rule R on each of the 60 replayed instances: (WT_R(untouched) - OPT_base) / max(OPT_base, 1 bh), with OPT_base the baseline oracle bracket. Intervals follow N2 (midpoint when the bracket's relative width is below 1e-3); the CSV also carries the value at the bracket's lower end.
- D-REL2 price of the 1,635 direct-benchmark proposals with R as the reference dispatcher, in two readings. *Site rule*: the site dispatches everything with R (baseline slots for freezes, the executed schedule, and the reference). *Reference only*: the published ATC episode and executed objective are kept, and only the reference is dispatched by R on the same adjusted instance.
- Under-priced: price minus truth below -0.05. Absolute truth g_true = (obj - OPT_adj) / max(OPT_adj, 1); marginal truth m_true = g_true minus R's own anchor gap.

## Assertions

- Suite SHA-256 and all 60 instance files verified against the instances_v10 manifest.
- 1635 proposals re-applied through the adapter; executed ATC objective equal to DG1's and N2's logged objective (1e-6 bh) and to the oracle item file (1e-4 bh); field fingerprint equal to the oracle's under the published episode and under every rule where the proposal executes (11445 rule-row checks); 0 rows needed the lenient parse, as in N2.
- ATC reference equal to N2's WT_ref2 on all 3270 row-readings; ATC pricing counts and error percentiles equal N2_pricing_direct.csv in all 64 D-REL2 cells (2 readings x 2 truths x 4 splits x 4 groups).
- ATC anchor gaps reproduce N2's macros: \nTwoRefGapAllMedian = 0.3%, \nTwoRefGapAllMax = [26.9, 28.7]%, \nTwoRefGapCNineStormMedian = [4.0, 4.1]%, \nTwoRefGapCNineStormMax = [26.9, 28.7]%, \nTwoRefGapCTenStormMedian = [0.1, 0.2]%, \nTwoRefGapCTenStormMax = 9.0%, \nTwoRefGapCTenReplayMedian = 0.0%, \nTwoRefGapCTenReplayMax = 1.6%.
- Every rule's plain Y1 dispatch equals the adapter's no-op dispatch on every instance and frozen set. Frozen-set anchors that differ from the plain anchor (site rule): none.
- Rules that give the same objective on every instance and every proposal: edd and pfifo; each such pair makes the same pick at every dispatch decision on these instances, so their rows are identical.
- The certificate's price stays sound under every site rule (minimum margin over the optimistic end of the bracket: atc 0.00e+00, edd 0.00e+00, wspt 0.00e+00, pfifo 0.00e+00, wmdd 0.00e+00, atc_k1 0.00e+00, atc_k3 0.00e+00).

## Table 1. Anchor gap by rule and stratum (60 instances)

Primary = c09_storm2_w80, Confirmation = c10_storm2_w80, Buildings = c10_replay_400. Above 0.20: instances whose whole anchor-gap interval exceeds tau = 0.20. Zero gap: instances on which the rule is optimal.

| Rule | Stratum | n | median | 90th pct | max | above 0.20 | zero gap |
|---|---|---|---|---|---|---|---|
| atc | Pooled | 60 | 0.3% | [6.4, 6.6]% | [26.9, 28.7]% | 2 | 21 |
| atc | Primary | 24 | [4.0, 4.1]% | 11.8% | [26.9, 28.7]% | 2 | 0 |
| atc | Confirmation | 12 | [0.1, 0.2]% | 1.6% | 9.0% | 0 | 1 |
| atc | Buildings | 24 | 0.0% | 0.1% | 1.6% | 0 | 20 |
| edd | Pooled | 60 | 0.2% | [5.9, 6.1]% | 23.6% | 2 | 21 |
| edd | Primary | 24 | [3.2, 3.3]% | 12.7% | 23.6% | 2 | 0 |
| edd | Confirmation | 12 | 0.1% | 0.7% | 10.7% | 0 | 1 |
| edd | Buildings | 24 | 0.0% | 0.1% | 1.9% | 0 | 20 |
| wspt | Pooled | 60 | 9.5% | 45.6% | 82.1% | 15 | 20 |
| wspt | Primary | 24 | 17.7% | [48.5, 48.7]% | 65.6% | 9 | 0 |
| wspt | Confirmation | 12 | 22.9% | [70.4, 70.7]% | 82.1% | 6 | 0 |
| wspt | Buildings | 24 | 0.0% | 5.3% | 8.8% | 0 | 20 |
| pfifo | Pooled | 60 | 0.2% | [5.9, 6.1]% | 23.6% | 2 | 21 |
| pfifo | Primary | 24 | [3.2, 3.3]% | 12.7% | 23.6% | 2 | 0 |
| pfifo | Confirmation | 12 | 0.1% | 0.7% | 10.7% | 0 | 1 |
| pfifo | Buildings | 24 | 0.0% | 0.1% | 1.9% | 0 | 20 |
| wmdd | Pooled | 60 | 0.2% | [6.0, 6.2]% | [22.4, 22.9]% | 2 | 21 |
| wmdd | Primary | 24 | 4.3% | 13.0% | [22.4, 22.9]% | 2 | 0 |
| wmdd | Confirmation | 12 | 0.1% | 0.7% | 9.0% | 0 | 1 |
| wmdd | Buildings | 24 | 0.0% | 0.1% | 1.9% | 0 | 20 |
| atc_k1 | Pooled | 60 | 0.2% | [5.3, 5.4]% | [23.1, 24.8]% | 2 | 22 |
| atc_k1 | Primary | 24 | 2.6% | [7.5, 7.6]% | [23.1, 24.8]% | 2 | 0 |
| atc_k1 | Confirmation | 12 | [0.1, 0.2]% | 0.7% | 9.0% | 0 | 2 |
| atc_k1 | Buildings | 24 | 0.0% | 0.1% | 4.3% | 0 | 20 |
| atc_k3 | Pooled | 60 | 0.2% | [8.1, 8.4]% | [25.9, 27.7]% | 2 | 21 |
| atc_k3 | Primary | 24 | 4.6% | [11.5, 11.6]% | [25.9, 27.7]% | 2 | 0 |
| atc_k3 | Confirmation | 12 | [0.1, 0.2]% | 2.5% | 9.0% | 0 | 1 |
| atc_k3 | Buildings | 24 | 0.0% | 0.1% | 1.6% | 0 | 20 |

What it shows: on the Primary stratum the median anchor gap is [4.0, 4.1]% under ATC and ranges from 2.6% (atc_k1) to 17.7% (wspt) under the alternative rules, while on Buildings no rule is more than 8.8% above the optimum.

## Table 2. D-REL2 share under-priced by more than 0.05 (1,635 proposals)

Absolute: against g_true. Marginal: against g_true minus the rule's own anchor gap. Undecided rows (oracle interval straddles the threshold) are out of the share.

### Reading: site rule

| Rule | Stratum | priced | absolute | marginal | marginal over-priced | median e (absolute) | median e (marginal) |
|---|---|---|---|---|---|---|---|
| atc | Pooled | 1635 | 21.2% | 1.5% (2 undecided) | 0.1% | -0.011 | 0.000 |
| atc | Primary | 829 | 39.0% | 2.8% (2 undecided) | 0.2% | [-0.043, -0.042] | 0.000 |
| atc | Confirmation | 313 | 7.7% | 0.6% | 0.0% | [-0.002, -0.000] | 0.000 |
| atc | Buildings | 493 | 0.0% | 0.0% | 0.0% | 0.000 | 0.000 |
| edd | Pooled | 1635 | 17.5% (18 undecided) | 1.3% | 0.2% | -0.005 | 0.000 |
| edd | Primary | 829 | 31.9% (18 undecided) | 2.4% | 0.4% | [-0.033, -0.032] | 0.000 |
| edd | Confirmation | 313 | 7.7% | 0.6% | 0.0% | -0.001 | 0.000 |
| edd | Buildings | 493 | 0.0% | 0.0% | 0.0% | 0.000 | 0.000 |
| wspt | Pooled | 1635 | 74.3% | 7.4% | 0.9% | [-0.128, -0.126] | 0.000 |
| wspt | Primary | 829 | 99.5% | 9.9% | 1.4% | -0.180 | 0.000 |
| wspt | Confirmation | 313 | 100.0% | 11.5% | 0.6% | -0.293 | 0.000 |
| wspt | Buildings | 493 | 15.4% | 0.6% | 0.0% | 0.000 | 0.000 |
| pfifo | Pooled | 1635 | 17.5% (18 undecided) | 1.3% | 0.2% | -0.005 | 0.000 |
| pfifo | Primary | 829 | 31.9% (18 undecided) | 2.4% | 0.4% | [-0.033, -0.032] | 0.000 |
| pfifo | Confirmation | 313 | 7.7% | 0.6% | 0.0% | -0.001 | 0.000 |
| pfifo | Buildings | 493 | 0.0% | 0.0% | 0.0% | 0.000 | 0.000 |
| wmdd | Pooled | 1635 | 22.2% (17 undecided) | 1.4% | 0.1% | -0.007 | 0.000 |
| wmdd | Primary | 829 | 41.4% (17 undecided) | 2.5% | 0.2% | [-0.041, -0.040] | 0.000 |
| wmdd | Confirmation | 313 | 7.7% | 0.6% | 0.0% | -0.001 | 0.000 |
| wmdd | Buildings | 493 | 0.0% | 0.0% | 0.0% | 0.000 | 0.000 |
| atc_k1 | Pooled | 1635 | 14.8% (3 undecided) | 0.9% | 0.1% | -0.008 | 0.000 |
| atc_k1 | Primary | 829 | 26.3% (3 undecided) | 1.4% | 0.2% | -0.028 | 0.000 |
| atc_k1 | Confirmation | 313 | 7.7% | 0.6% | 0.0% | [-0.001, -0.000] | 0.000 |
| atc_k1 | Buildings | 493 | 0.2% | 0.0% | 0.0% | 0.000 | 0.000 |
| atc_k3 | Pooled | 1635 | 21.6% | 1.4% (1 undecided) | 0.1% | -0.006 | 0.000 |
| atc_k3 | Primary | 829 | 39.7% | 2.7% (1 undecided) | 0.2% | -0.046 | 0.000 |
| atc_k3 | Confirmation | 313 | 7.7% | 0.3% | 0.0% | [-0.002, -0.001] | 0.000 |
| atc_k3 | Buildings | 493 | 0.0% | 0.0% | 0.0% | 0.000 | 0.000 |

### Reading: reference only

| Rule | Stratum | priced | absolute | marginal | marginal over-priced | median e (absolute) | median e (marginal) |
|---|---|---|---|---|---|---|---|
| atc | Pooled | 1635 | 21.2% | 1.5% (2 undecided) | 0.1% | -0.011 | 0.000 |
| atc | Primary | 829 | 39.0% | 2.8% (2 undecided) | 0.2% | [-0.043, -0.042] | 0.000 |
| atc | Confirmation | 313 | 7.7% | 0.6% | 0.0% | [-0.002, -0.000] | 0.000 |
| atc | Buildings | 493 | 0.0% | 0.0% | 0.0% | 0.000 | 0.000 |
| edd | Pooled | 1635 | 18.3% (3 undecided) | 1.2% | 0.2% | -0.005 | [-0.000, 0.000] |
| edd | Primary | 829 | 33.3% (3 undecided) | 2.2% | 0.4% | [-0.033, -0.032] | -0.000 |
| edd | Confirmation | 313 | 7.7% | 0.6% | 0.0% | -0.001 | -0.000 |
| edd | Buildings | 493 | 0.0% | 0.0% | 0.0% | 0.000 | 0.000 |
| wspt | Pooled | 1635 | 74.3% | 5.6% (3 undecided) | 23.1% | [-0.118, -0.116] | 0.006 |
| wspt | Primary | 829 | 99.5% | 9.8% (3 undecided) | 27.1% | [-0.165, -0.160] | [0.017, 0.020] |
| wspt | Confirmation | 313 | 100.0% | 2.9% | 48.9% | -0.227 | 0.023 |
| wspt | Buildings | 493 | 15.4% | 0.4% | 0.0% | 0.000 | 0.000 |
| pfifo | Pooled | 1635 | 18.3% (3 undecided) | 1.2% | 0.2% | -0.005 | [-0.000, 0.000] |
| pfifo | Primary | 829 | 33.3% (3 undecided) | 2.2% | 0.4% | [-0.033, -0.032] | -0.000 |
| pfifo | Confirmation | 313 | 7.7% | 0.6% | 0.0% | -0.001 | -0.000 |
| pfifo | Buildings | 493 | 0.0% | 0.0% | 0.0% | 0.000 | 0.000 |
| wmdd | Pooled | 1635 | 22.9% (2 undecided) | 1.3% | 0.1% | -0.007 | [-0.000, 0.000] |
| wmdd | Primary | 829 | 42.3% (2 undecided) | 2.4% | 0.2% | [-0.040, -0.038] | -0.000 |
| wmdd | Confirmation | 313 | 7.7% | 0.6% | 0.0% | -0.001 | -0.000 |
| wmdd | Buildings | 493 | 0.0% | 0.0% | 0.0% | 0.000 | 0.000 |
| atc_k1 | Pooled | 1635 | 14.8% (17 undecided) | 0.8% | 0.1% | -0.008 | [-0.000, 0.000] |
| atc_k1 | Primary | 829 | 26.5% (17 undecided) | 1.3% | 0.2% | -0.029 | -0.000 |
| atc_k1 | Confirmation | 313 | 7.7% | 0.6% | 0.0% | [-0.001, -0.000] | -0.000 |
| atc_k1 | Buildings | 493 | 0.2% | 0.0% | 0.0% | 0.000 | 0.000 |
| atc_k3 | Pooled | 1635 | 21.5% | 1.7% (1 undecided) | 0.1% | -0.006 | 0.000 |
| atc_k3 | Primary | 829 | 39.6% | 3.0% (1 undecided) | 0.2% | -0.046 | -0.000 |
| atc_k3 | Confirmation | 313 | 7.7% | 0.6% | 0.0% | [-0.002, -0.001] | [-0.000, 0.000] |
| atc_k3 | Buildings | 493 | 0.0% | 0.0% | 0.0% | 0.000 | 0.000 |

What it shows: with the site's own rule as the reference, the pooled share of proposals under-priced against the optimum follows the rule's anchor gap, from 14.8% (atc_k1) to 74.3% (wspt); after the rule's own anchor gap is subtracted the share falls to 0.9% to 1.5% for atc, edd, pfifo, wmdd, atc_k1, atc_k3 and to 7.4% for wspt. When only the reference changes and the site keeps ATC, the marginal under-pricing share is 0.8% to 5.6%, and wspt over-prices 23.1% of proposals because its own gap is larger than the one ATC loses.

## Split by operation type (pooled, site rule)

| Rule | split | priced | absolute | marginal |
|---|---|---|---|---|
| atc | empty | 255 | 20.8% | 0.0% |
| atc | sequencing_only | 835 | 21.4% | 2.3% (1 undecided) |
| atc | field_changing | 545 | 21.1% | 1.1% (1 undecided) |
| edd | empty | 255 | 16.3% (3 undecided) | 0.0% |
| edd | sequencing_only | 835 | 18.6% (7 undecided) | 2.3% |
| edd | field_changing | 545 | 16.4% (8 undecided) | 0.6% |
| wspt | empty | 255 | 80.0% | 0.0% |
| wspt | sequencing_only | 835 | 73.9% | 11.0% |
| wspt | field_changing | 545 | 72.1% | 5.3% |
| pfifo | empty | 255 | 16.3% (3 undecided) | 0.0% |
| pfifo | sequencing_only | 835 | 18.6% (7 undecided) | 2.3% |
| pfifo | field_changing | 545 | 16.4% (8 undecided) | 0.6% |
| wmdd | empty | 255 | 22.2% (3 undecided) | 0.0% |
| wmdd | sequencing_only | 835 | 22.8% (7 undecided) | 2.4% |
| wmdd | field_changing | 545 | 21.4% (7 undecided) | 0.6% |
| atc_k1 | empty | 255 | 14.1% | 0.0% |
| atc_k1 | sequencing_only | 835 | 15.2% | 1.4% |
| atc_k1 | field_changing | 545 | 14.6% (3 undecided) | 0.4% |
| atc_k3 | empty | 255 | 22.0% | 0.0% |
| atc_k3 | sequencing_only | 835 | 21.7% | 2.0% |
| atc_k3 | field_changing | 545 | 21.3% | 1.1% (1 undecided) |

What it shows: the marginal under-pricing that remains is 0.0% at most on proposals with no operation under every rule, and it sits mainly in sequencing-only proposals, where the reference and the executed schedule are both dispatched by the rule (largest share 11.0%, under wspt).

