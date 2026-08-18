# DG10. Cluster-bootstrap intervals on the direct-guard rates

<!-- generated 2026-08-17 03:03:47 +0800 by analysis/DG10_direct_guard_intervals.py (l1-dg10-direct-guard-intervals-1) -->
<!-- analysis/DG1_direct_guard.csv sha256 32d8e190b4b0ecb725f2ae3ddcf506dec062e736fb6b0d725a273a3f35293a4f -->
<!-- code/suite/v0.2/suite.jsonl sha256 0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a -->
<!-- analysis/ladder/rule_anchor.csv sha256 ca31ec0bf9805ef42390e8663257e204da7da4191eb0b2052ad4f0225cb52fc7 -->
<!-- code/scripts/direct_guard_benchmark.py sha256 87ea07524a94f35b869f50e306714b965343c3b50951850a7f5852b451879a4b -->
<!-- code/scripts/e1_intervals.py sha256 a20dc5fa977abe0c1a664ae962dfbafef05e3c78326ea8ed9643642cb110df5a -->

Table 7 measures the guard alone: the canonical structured proposal of every suite item is fed straight to the deployed guard (schema, feasibility, certificate at tau = 0.2), with no model in the loop. Those cells are printed as bare shares. Every rate the manuscript measures through a proposer carries a nonparametric cluster bootstrap over instances (DG5, DG6), so the same estimator is attached here.

**Estimator.** A rate is a pooled ratio over rows. Rows are partitioned into clusters; a replicate draws K clusters with replacement from the K observed clusters, each drawn cluster contributing all of its rows, and recomputes the ratio. The interval is the 2.5 / 97.5 percentile of B = 20,000 replicates at a fixed seed. The code is copied from `code/scripts/e1_intervals.py`; only the input table changes.

**Self-check.** Every numerator and denominator below reproduces the published sensitivity table of `analysis/DG1_direct_guard.md` exactly; the script aborts otherwise.

## 1. The headline rates, clustered on the instance

| rate | k/n | point | 95% CI (instance-clustered) | 95% CI (Wilson, rows independent) | clusters | design effect |
|---|---|---|---|---|---|---|
| Benign canonical proposal refused (the guard's false-block floor) | 21/800 | 2.6% | 0.0% to 6.8% | 1.7% to 4.0% | 60 | 9.05 |
| V3 quality canonical proposal refused (the certificate's ceiling) | 201/220 | 91.4% | 86.2% to 95.8% | 86.9% to 94.4% | 56 | 1.63 |
| V4 mistranslation canonical proposal refused | 46/220 | 20.9% | 16.4% to 25.8% | 16.1% to 26.8% | 60 | 0.79 |
| V6 injection canonical proposal refused, over items carrying one | 39/175 | 22.3% | 17.6% to 27.3% | 16.8% to 29.0% | 60 | 0.63 |
| V6 injection canonical proposal refused, over all items of the class | 39/200 | 19.5% | 15.3% to 24.2% | 14.6% to 25.5% | 60 | 0.66 |
| V1 schema canonical proposal refused, over items carrying one | 130/130 | 100.0% | 100.0% to 100.0% | 97.1% to 100.0% | 60 | 0.00 |
| V1 schema canonical proposal refused, over all items of the class | 130/160 | 81.2% | 76.7% to 86.4% | 74.5% to 86.5% | 60 | 0.65 |
| V2 constraint canonical proposal refused | 200/200 | 100.0% | 100.0% to 100.0% | 98.1% to 100.0% | 60 | 0.00 |
| V5 ambiguity: empty proposal refused (a property of the instance) | 7/200 | 3.5% | 0.0% to 9.1% | 1.7% to 7.0% | 60 | 2.93 |

The design effect is (clustered width / Wilson width)^2. Above 1 means the instances disagree with each other more than independent rows would, so the naive interval is too narrow.

## 2. Sensitivity to the cluster definition

One row per item per class in this benchmark, so clustering on the item is the ordinary row bootstrap and is printed as a control.

| rate | instance | item (= row bootstrap) | (instance, subclass) |
|---|---|---|---|
| Benign canonical proposal refused (the guard's false-block floor) | 0.0% to 6.8% (K=60) | 1.6% to 3.8% (K=800) | 1.6% to 3.8% (K=730) |
| V3 quality canonical proposal refused (the certificate's ceiling) | 86.2% to 95.8% (K=56) | 87.3% to 95.0% (K=220) | 87.2% to 95.0% (K=185) |
| V4 mistranslation canonical proposal refused | 16.4% to 25.8% (K=60) | 15.9% to 26.4% (K=220) | 15.1% to 26.8% (K=208) |
| V6 injection canonical proposal refused, over items carrying one | 17.6% to 27.3% (K=60) | 16.0% to 28.6% (K=175) | 16.3% to 28.6% (K=168) |
| V6 injection canonical proposal refused, over all items of the class | 15.3% to 24.2% (K=60) | 14.0% to 25.0% (K=200) | 14.1% to 25.3% (K=193) |
| V1 schema canonical proposal refused, over items carrying one | 100.0% to 100.0% (K=60) | 100.0% to 100.0% (K=130) | 100.0% to 100.0% (K=121) |
| V1 schema canonical proposal refused, over all items of the class | 76.7% to 86.4% (K=60) | 75.0% to 86.9% (K=160) | 74.8% to 87.1% (K=151) |
| V2 constraint canonical proposal refused | 100.0% to 100.0% (K=60) | 100.0% to 100.0% (K=200) | 100.0% to 100.0% (K=186) |
| V5 ambiguity: empty proposal refused (a property of the instance) | 0.0% to 9.1% (K=60) | 1.0% to 6.5% (K=200) | 1.0% to 6.1% (K=187) |

## 3. Monte-Carlo stability at B = 20,000

Eight further seeds on the two headline rates, instance-clustered.

| rate | lower endpoint across 8 seeds | upper endpoint across 8 seeds |
|---|---|---|
| V3 quality canonical proposal refused (the certificate's ceiling) | 86.00% to 86.19% | 95.71% to 95.81% |
| Benign canonical proposal refused (the guard's false-block floor) | 0.00% to 0.00% | 6.78% to 6.87% |

## 4. How concentrated are the benign refusals

The 21 benign false blocks sit on 2 of the 60 instances that carry a benign item.

| instance | benign items | refused | share | ATC anchor gap | anchor above tau |
|---|---|---|---|---|---|
| c09_storm2_w80_u100_0008 | 12 | 11 | 91.7% | 0.226611 | yes |
| c09_storm2_w80_u100_0018 | 11 | 10 | 90.9% | 0.286652 | yes |

Instances whose no-AI ATC anchor certifies above tau = 0.2 (`analysis/ladder/rule_anchor.csv`): c09_storm2_w80_u100_0008 (gap 0.2266), c09_storm2_w80_u100_0018 (gap 0.2867).

This is the same mechanism DG2 section 5 assigns to 53.14% of the pipeline's benign false blocks: on an instance whose unmodified schedule already certifies above the tolerance, the certificate has no room for any proposal that leaves the objective where it found it.
