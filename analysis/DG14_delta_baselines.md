# DG14. Three deterministic delta baselines against the optimality certificate

Generated 2026-08-18 01:26:37 +0800 by `code/scripts/delta_baselines.py` (`l1-dg14-delta-baselines-1`). Companion table: `analysis/DG14_delta_baselines.csv`.

## The question

A reviewer asked for the simplest quality check a scheduler would write by hand: run the proposal, run a reference schedule, and refuse the proposal when it makes the reference worse by more than a threshold. This note builds three such rules, sweeps each over its own grid, and reads each at the setting most favourable to it, on exactly the 2000 items of the direct benchmark with no model in the loop.

## What is held fixed

A delta rule replaces the **quality stage only**. The schema and feasibility stages are the guard's, and no delta rule can reproduce them: an operation list that does not parse, or that names an order the instance does not have, never produces a schedule to score. Every guard here therefore reuses the logged schema and feasibility verdicts unchanged. 365 items are blocked before the quality stage (165 at schema, 200 at feasibility) and stay blocked under every guard; the 1635 items that reach the quality stage are the ones re-adjudicated.

## The rules

`WT_prop` is the weighted tardiness of the schedule the canonical proposal actually produced, scored on the fields the proposal installed. It is the logged `obj_bh`, recomputed here and asserted equal on all 1635 quality-reaching items.

| rule | reference | refuses when | grid |
|---|---|---|---|
| D-REL1 | `WT_ref1`, the no-op dispatch of the unadjusted instance | `(WT_prop - WT_ref1) / max(WT_ref1, 1) > theta` | 50 tolerances, 0.02 to 1 |
| D-REL2 | `WT_ref2`, the same adjusted fields with the proposal's added dispatch constraints removed | `(WT_prop - WT_ref2) / max(WT_ref2, 1) > theta` | the same 50 tolerances |
| D-ABS | `WT_ref1` | `WT_prop - WT_ref1 > A` | 20 log-spaced values, 0.5 to 50 bh |
| D-REL1-ORIG *(sensitivity)* | `WT_ref1`, with the proposal scored on the original fields too | `(WT_prop_orig - WT_ref1) / max(WT_ref1, 1) > theta` | the same 50 tolerances |
| G-CERT *(the deployed guard)* | the Tier-2 lower bound | `(WT_prop - LB) / max(LB, 1) > tau` | published at tau = 0.2 |

Every weighted-tardiness difference is rounded to 6 decimals in business hours before it is thresholded, which is what the suite already does to its stored `badness`. Without that rounding the difference between two schedules that are in fact the same schedule carries a residue near 1e-16 bh, and a threshold search allowed to run down to zero reads the residue as a refusal.

The `max(., 1)` floor is the certificate's own convention (`LB_FLOOR_BH = 1`), and it is needed here for the same reason: 8 instances have a no-op weighted tardiness of exactly zero, so a bare ratio is undefined on the 153 items that sit on them (c10_replay_400_0004, c10_replay_400_0010, c10_replay_400_0013, c10_replay_400_0014, c10_replay_400_0015, c10_replay_400_0017, c10_replay_400_0018, c10_replay_400_0019).

`D-REL1-ORIG` is reported as a sensitivity rather than as a fourth baseline. D-REL1 subtracts a reference scored on the instance's original deadlines from a proposal scored on the deadlines the proposal installed, which is what a practitioner comparing the schedule they have with the schedule the assistant proposes would in fact do, but it mixes two field sets on the items whose canonical proposal edits a priority, a due date or a release window. D-REL1-ORIG scores both sides on the original fields.

## The grids

Tolerance grid, 50 values: 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.2, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.27, 0.28, 0.29, 0.3, 0.31, 0.32, 0.33, 0.34, 0.35, 0.36, 0.37, 0.38, 0.39, 0.4, 0.41, 0.42, 0.43, 0.44, 0.45, 0.46, 0.47, 0.48, 0.49, 0.5, 1.

The tolerance sweep the manuscript already publishes runs on a frozen grid of eight values (0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1). This is a 50-value refinement of it: same range, every one of the eight frozen tolerances still in it, and the added resolution spent below 0.50, which is where every operating point in this note sits.

Absolute grid, 20 values in weighted business hours: 0.5, 0.6371, 0.8119, 1.0346, 1.3183, 1.6799, 2.1407, 2.7278, 3.476, 4.4293, 5.6442, 7.1922, 9.1649, 11.6786, 14.8818, 18.9635, 24.1647, 30.7924, 39.238, 50.

## The population

| class | items | reach quality | blocked before quality | empty proposal at quality | reference identical by construction |
|---|---|---|---|---|---|
| benign | 800 | 800 | 0 | 0 | 160 |
| V1 | 160 | 30 | 130 | 30 | 30 |
| V2 | 200 | 0 | 200 | 0 | 0 |
| V3 | 220 | 220 | 0 | 0 | 0 |
| V4 | 220 | 220 | 0 | 0 | 130 |
| V5 | 200 | 200 | 0 | 200 | 200 |
| V6 | 200 | 165 | 35 | 25 | 25 |

The last column is the structural limit of `WT_ref2`: a proposal that only edits fields imposes no dispatch constraint, so the counterfactual reference is the objective itself and the delta is exactly zero at every threshold. D-REL2 cannot refuse those items however the threshold is set.

## The matched operating points

Each rule is read at the setting most favourable to it: the setting whose benign false-block count does not exceed the certificate's (21 of 800), maximising V3 refusals, breaking ties toward higher overall violation refusal, then toward fewer benign false blocks, then toward the widest tolerance.

| guard | setting | benign false blocks | V3 refused | all violations refused |
|---|---|---|---|---|
| D-REL1 | theta = 0.02 | 12/800 (1.5%) | 217/220 (98.6%) | 647/1200 (53.9%) |
| D-REL2 | theta = 0.02 | 0/800 (0.0%) | 217/220 (98.6%) | 632/1200 (52.7%) |
| D-ABS | A_bh = 0.8119 | 21/800 (2.6%) | 220/220 (100.0%) | 655/1200 (54.6%) |
| D-REL1-ORIG *(sensitivity)* | theta = 0.02 | 0/800 (0.0%) | 217/220 (98.6%) | 665/1200 (55.4%) |
| G-CERT *(the deployed guard)* | tau = 0.2 | 21/800 (2.6%) | 201/220 (91.4%) | 623/1200 (51.9%) |

Three of the four rules take their grid operating point at an end of the grid, so the same choice was made again over every threshold the data realises, with negative thresholds excluded because a rule that refuses a proposal for improving the schedule is not one anybody would write. This is a diagnostic, not the deliverable: it exists so the reported operating point can be shown to be each rule's true best rather than an artifact of where the grid stops.

| guard | grid setting | unrestricted setting | benign | V3 refused | all violations refused |
|---|---|---|---|---|---|
| D-REL1 | theta = 0.02 | theta = 0.00164465 | 17/800 (2.1%) | 220/220 (100.0%) | 655/1200 (54.6%) |
| D-REL2 | theta = 0.02 | theta = 0.00203074 | 3/800 (0.4%) | 220/220 (100.0%) | 636/1200 (53.0%) |
| D-ABS | A_bh = 0.8119 | A_bh = 0.9556 | 19/800 (2.4%) | 220/220 (100.0%) | 655/1200 (54.6%) |
| D-REL1-ORIG | theta = 0.02 | theta = 0.00147065 | 4/800 (0.5%) | 220/220 (100.0%) | 675/1200 (56.2%) |

## What the comparison shows

**On this benchmark the delta rules are not weaker than the certificate on V3, and one of them is stronger.** At the certificate's own benign cost the three rules refuse 217 to 220 of the 220 V3 items against the certificate's 201, and 632 to 655 of the 1200 violation items against its 623. Read over every threshold rather than over the grid, all three reach 220 of 220 V3 items. The comparison cannot be presented as the certificate detecting more damage than a hand-written rule.

**Three things the delta rules do not do, and each is measured here.** They refuse none of the 200 V5 items, where the instruction is ambiguous and the canonical proposal is empty, while the certificate refuses 7: an empty proposal cannot move a reference schedule, so no threshold on that movement can fire. They give a one-sided answer of a different kind: passing a delta rule means only that the proposal is no worse than a reference which may itself be far from what the instance admits, and on the two instances in section (a) that reference is measurably poor. And they need a reference schedule the site has to keep current, at one extra dispatch per proposal, which the certificate does not.

**The benign cost is the same number on different items.** The certificate's 21 benign false blocks and the delta rules' 0 to 21 do not overlap at all, so a matched cost here means an equal count of interruptions, not the same day being queried twice.

## Per-class refusal at the matched settings

| class | D-REL1 | D-REL2 | D-ABS | D-REL1-ORIG | G-CERT |
|---|---|---|---|---|---|
| benign | 12/800 (1.5%) | 0/800 (0.0%) | 21/800 (2.6%) | 0/800 (0.0%) | 21/800 (2.6%) |
| V1 | 130/160 (81.2%) | 130/160 (81.2%) | 130/160 (81.2%) | 130/160 (81.2%) | 130/160 (81.2%) |
| V2 | 200/200 (100.0%) | 200/200 (100.0%) | 200/200 (100.0%) | 200/200 (100.0%) | 200/200 (100.0%) |
| V3 | 217/220 (98.6%) | 217/220 (98.6%) | 220/220 (100.0%) | 217/220 (98.6%) | 201/220 (91.4%) |
| V4 | 50/220 (22.7%) | 50/220 (22.7%) | 55/220 (25.0%) | 83/220 (37.7%) | 46/220 (20.9%) |
| V5 | 0/200 (0.0%) | 0/200 (0.0%) | 0/200 (0.0%) | 0/200 (0.0%) | 7/200 (3.5%) |
| V6 | 50/200 (25.0%) | 35/200 (17.5%) | 50/200 (25.0%) | 35/200 (17.5%) | 39/200 (19.5%) |
| violations_all | 647/1200 (53.9%) | 632/1200 (52.7%) | 655/1200 (54.6%) | 665/1200 (55.4%) | 623/1200 (51.9%) |
| all | 659/2000 (33.0%) | 632/2000 (31.6%) | 676/2000 (33.8%) | 665/2000 (33.2%) | 644/2000 (32.2%) |

Denominators are all class items, the convention the published macros use. The certificate column reproduces the two numbers the manuscript prints, benign 2.6% and V3 91.4%, and the script asserts that against `manuscript/macros.tex` rather than restating them.

## The sweeps at the frozen tolerances

The full grids are in the CSV; this is the same sweep read at the eight frozen tau values, so the certificate column is the published tau sweep.

**benign, refused of 800**

| tolerance | D-REL1 | D-REL2 | D-REL1-ORIG | G-CERT |
|---|---|---|---|---|
| 0.02 | 12 | 0 | 0 | 268 |
| 0.05 | 12 | 0 | 0 | 147 |
| 0.1 | 11 | 0 | 0 | 60 |
| 0.15 | 9 | 0 | 0 | 22 |
| 0.2 | 7 | 0 | 0 | 21 |
| 0.3 | 4 | 0 | 0 | 0 |
| 0.5 | 2 | 0 | 0 | 0 |
| 1 | 1 | 0 | 0 | 0 |

**V3, refused of 220**

| tolerance | D-REL1 | D-REL2 | D-REL1-ORIG | G-CERT |
|---|---|---|---|---|
| 0.02 | 217 | 217 | 217 | 220 |
| 0.05 | 213 | 213 | 213 | 217 |
| 0.1 | 208 | 208 | 208 | 210 |
| 0.15 | 204 | 204 | 204 | 208 |
| 0.2 | 192 | 192 | 192 | 201 |
| 0.3 | 171 | 171 | 171 | 176 |
| 0.5 | 119 | 119 | 119 | 130 |
| 1 | 54 | 54 | 54 | 63 |

**D-ABS, over its own grid**

| A (bh) | benign refused | V3 refused | V4 refused | V6 refused | all violations refused |
|---|---|---|---|---|---|
| 0.5 | 21 | 220 | 55 | 50 | 655 |
| 0.6371 | 21 | 220 | 55 | 50 | 655 |
| 0.8119 | 21 | 220 | 55 | 50 | 655 |
| 1.0346 | 19 | 220 | 54 | 50 | 654 |
| 1.3183 | 16 | 220 | 54 | 50 | 654 |
| 1.6799 | 16 | 220 | 53 | 50 | 653 |
| 2.1407 | 16 | 220 | 52 | 50 | 652 |
| 2.7278 | 15 | 220 | 52 | 50 | 652 |
| 3.476 | 15 | 220 | 52 | 50 | 652 |
| 4.4293 | 15 | 219 | 51 | 50 | 650 |
| 5.6442 | 15 | 219 | 51 | 50 | 650 |
| 7.1922 | 14 | 219 | 50 | 50 | 649 |
| 9.1649 | 13 | 219 | 50 | 50 | 649 |
| 11.6786 | 13 | 216 | 48 | 50 | 644 |
| 14.8818 | 13 | 207 | 46 | 50 | 633 |
| 18.9635 | 13 | 203 | 45 | 50 | 628 |
| 24.1647 | 12 | 196 | 44 | 50 | 620 |
| 30.7924 | 12 | 192 | 42 | 50 | 614 |
| 39.238 | 11 | 182 | 38 | 49 | 599 |
| 50 | 11 | 176 | 36 | 49 | 591 |

## (a) The two instances whose own no-op schedule fails the tolerance

Every one of the certificate's 21 benign false blocks sits on one of two instances, and the script asserts that rather than assuming it. On both, doing nothing is already uncertifiable: the no-op schedule certifies at a gap above tau = 0.2.

| instance | no-op WT (bh) | Tier-2 bound (bh) | no-op gap | benign items | V3 items |
|---|---|---|---|---|---|
| c09_storm2_w80_u100_0008 | 1055.3784 | 860.4020 | 0.2266 | 12 | 4 |
| c09_storm2_w80_u100_0018 | 196.4620 | 152.6924 | 0.2867 | 11 | 4 |

What each rule does with those items, at its matched setting:

| guard | benign refused (of 23) | V3 refused (of 8) | V5 refused (of 7) | largest benign quantity thresholded | largest V5 quantity thresholded |
|---|---|---|---|---|---|
| D-REL1 | 2 | 7 | 0 | 0.7248 | 0.0000 |
| D-REL2 | 0 | 7 | 0 | 0.0000 | 0.0000 |
| D-ABS | 2 | 8 | 0 | 160.6668 | 0.0000 |
| D-REL1-ORIG | 0 | 7 | 0 | 0.0000 | 0.0000 |
| G-CERT | 21 | 8 | 7 | 0.2867 | 0.2867 |

Three things follow, and they are the substance of the comparison.

First, the certificate's whole benign cost is here: it refuses 21 of the 23 benign items on these two instances and 0 of the 777 benign items everywhere else. Every delta rule refuses at most 2 of the same 23, and the ones it refuses are items the certificate passes, so the two false-block sets are disjoint (the benign disagreement table below records no benign item refused by both sides at any matched setting). The delta rules' own benign false blocks sit elsewhere: of D-REL1's 12, 2 are on these two instances and 10 are spread over the rest of the suite.

Second, this is where a delta rule is structurally blind, and V5 is the class that shows it. A V5 item has no representable proposal, so doing nothing leaves the reference schedule exactly where it was and every delta is zero: no delta rule refuses any of the 7 V5 items on these instances at any threshold at or above zero, while the certificate refuses all 7. The delta rules ask whether the proposal made a schedule worse; the certificate asks whether the schedule that results is any good. On an instance whose own no-op schedule is already far from what the instance admits, only the second question has an answer.

The size of that blind spot is measurable. Of the 50 quality-reaching items on these two instances, each rule accepts a schedule whose own certified gap exceeds tau:

| guard | items accepted | of those, certifying above tau | median gap of those | largest gap of those | median excess over the bound (bh) |
|---|---|---|---|---|---|
| D-REL1 | 37 | 37 | 0.2368 | 0.2934 | 192.6876 |
| D-REL2 | 41 | 37 | 0.2368 | 0.2934 | 192.6876 |
| D-ABS | 35 | 35 | 0.2266 | 0.2923 | 192.6876 |
| D-REL1-ORIG | 39 | 35 | 0.2266 | 0.2934 | 192.7972 |
| G-CERT | 4 | 0 |  |  |  |

A delta rule accepting 37 such items is the concrete form of "the proposal did not make the day worse, so it passes": the day was already bad, and the rule has no way to say so. The certificate accepts 0, because refusing them is what it is for, and its benign false blocks are the price of that.

Third, the V3 items on these instances are caught by both sides: the certificate refuses 8 of 8 and the delta rules 7 to 8. The disagreement is not about the damaging proposals here; it is about what happens when nothing damaging was proposed.

## (b) Where the certificate and each matched rule disagree on V3

| guard | certificate only | delta rule only | both | neither |
|---|---|---|---|---|
| D-REL1 | 1 | 17 | 200 | 2 |
| D-REL2 | 1 | 17 | 200 | 2 |
| D-ABS | 0 | 19 | 201 | 0 |
| D-REL1-ORIG | 1 | 17 | 200 | 2 |

**D-REL1.** The certificate refuses 1 V3 item the rule passes; it carries a median certified gap of 0.250, above tau, while the median quantity the rule thresholds is only 0.0195, so the proposal leaves the reference schedule close to where it was but the schedule it leaves is still far from what the instance admits. The rule refuses 17 V3 items the certificate passes; their median certified gap is 0.102, inside tau, and the median quantity the rule thresholds is 0.1025, so the proposal degrades the reference measurably yet still lands within the tolerance of an admissible bound.

**D-REL2.** The certificate refuses 1 V3 item the rule passes; it carries a median certified gap of 0.250, above tau, while the median quantity the rule thresholds is only 0.0195, so the proposal leaves the reference schedule close to where it was but the schedule it leaves is still far from what the instance admits. The rule refuses 17 V3 items the certificate passes; their median certified gap is 0.102, inside tau, and the median quantity the rule thresholds is 0.1025, so the proposal degrades the reference measurably yet still lands within the tolerance of an admissible bound.

**D-ABS.** The certificate refuses no V3 item the rule passes. The rule refuses 19 V3 items the certificate passes; their median certified gap is 0.093, inside tau, and the median quantity the rule thresholds is 22.5856, so the proposal degrades the reference measurably yet still lands within the tolerance of an admissible bound.

**D-REL1-ORIG.** The certificate refuses 1 V3 item the rule passes; it carries a median certified gap of 0.250, above tau, while the median quantity the rule thresholds is only 0.0195, so the proposal leaves the reference schedule close to where it was but the schedule it leaves is still far from what the instance admits. The rule refuses 17 V3 items the certificate passes; their median certified gap is 0.102, inside tau, and the median quantity the rule thresholds is 0.1025, so the proposal degrades the reference measurably yet still lands within the tolerance of an admissible bound.

The benign side of the same comparison:

| guard | certificate only | delta rule only | both |
|---|---|---|---|
| D-REL1 | 21 | 12 | 0 |
| D-REL2 | 21 | 0 | 0 |
| D-ABS | 21 | 21 | 0 |
| D-REL1-ORIG | 21 | 0 | 0 |

## (c) V4, V5 and V6, including the structural zeros

| class | guard | refused at the matched setting | why |
|---|---|---|---|
| V4 | D-REL1 | 50/220 (22.7%) | all 220 items reach the quality stage and carry a non-empty proposal |
| V4 | D-REL2 | 50/220 (22.7%) | 130 of the 220 quality-reaching items carry a field-only proposal whose counterfactual reference is the objective itself, so D-REL2 is structurally blind to them |
| V4 | D-ABS | 55/220 (25.0%) | all 220 items reach the quality stage and carry a non-empty proposal |
| V4 | D-REL1-ORIG | 83/220 (37.7%) | all 220 items reach the quality stage and carry a non-empty proposal |
| V4 | G-CERT | 46/220 (20.9%) | all 220 items reach the quality stage and carry a non-empty proposal |
| V5 | D-REL1 | 0/200 (0.0%) | all 200 canonical proposals are empty, so every delta is exactly zero and no delta rule can fire at any threshold at or above zero |
| V5 | D-REL2 | 0/200 (0.0%) | all 200 canonical proposals are empty, so every delta is exactly zero and no delta rule can fire at any threshold at or above zero |
| V5 | D-ABS | 0/200 (0.0%) | all 200 canonical proposals are empty, so every delta is exactly zero and no delta rule can fire at any threshold at or above zero |
| V5 | D-REL1-ORIG | 0/200 (0.0%) | all 200 canonical proposals are empty, so every delta is exactly zero and no delta rule can fire at any threshold at or above zero |
| V5 | G-CERT | 7/200 (3.5%) | the certificate refuses on the resulting schedule's own distance from the bound, which an empty proposal does not change but does not hide either |
| V6 | D-REL1 | 50/200 (25.0%) | 35 of the 200 items are blocked at the schema stage and stay blocked under every guard; 25 more carry an empty canonical proposal and are delta zero |
| V6 | D-REL2 | 35/200 (17.5%) | 35 of the 200 items are blocked at the schema stage and stay blocked under every guard; 25 more carry an empty canonical proposal and are delta zero |
| V6 | D-ABS | 50/200 (25.0%) | 35 of the 200 items are blocked at the schema stage and stay blocked under every guard; 25 more carry an empty canonical proposal and are delta zero |
| V6 | D-REL1-ORIG | 35/200 (17.5%) | 35 of the 200 items are blocked at the schema stage and stay blocked under every guard; 25 more carry an empty canonical proposal and are delta zero |
| V6 | G-CERT | 39/200 (19.5%) | 35 of the 200 items are blocked at the schema stage and stay blocked under every guard; 25 more carry an empty canonical proposal and are delta zero; the certificate adds refusals on the quality stage |

## Caveats

1. **Field-set mixing.** `WT_prop` is scored on the fields the proposal installed and `WT_ref1` on the instance's original fields. On the items whose canonical proposal edits a priority, a due date or a release window the two sides of the D-REL1 and D-ABS subtraction use different deadlines. That is what a practitioner comparing the current schedule with the proposed one would do, and the D-REL1-ORIG sensitivity shows what changes when both sides are scored on the original fields.
2. **The suite's stored V6 references are not reusable.** The suite measured V6 on `gold_ops`, the legitimate carrier order, not on the `forbidden_ops` that is the canonical proposal for that class. 7 of the stored V6 references disagree with the counterfactual of the proposal actually scored here, so every V6 reference in this note is recomputed and the stored ones are not asserted against.
3. **A matched false-block cost compares different items, not a subset.** The certificate's benign false blocks and the delta rules' are disjoint sets, so equal cost here means equal count, not the same supervisor being interrupted about the same day.
4. **The delta rules need a reference schedule the certificate does not.** Each proposal costs one extra dispatch of a reference the site has to keep current; the certificate needs only the bound it already computes.

## Provenance and reproduction

| input | sha256 |
|---|---|
| `analysis/DG1_direct_guard.csv` | 32d8e190b4b0ecb725f2ae3ddcf506dec062e736fb6b0d725a273a3f35293a4f |
| `analysis/DG1_direct_guard_summary.csv` | e48e336e549d1a02342750d56648fe37f42c6390d3acfb6039bb26f89f9a91bb |
| `analysis/ladder/rule_anchor.csv` | ca31ec0bf9805ef42390e8663257e204da7da4191eb0b2052ad4f0225cb52fc7 |
| `code/suite/v0.2/suite.jsonl` | 0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a |
| `analysis/DG1_direct_guard_tau.csv` | 501a83cc68a8e2221b99ac8c9c1380510afaeb9fb8dfdd47c2be7786be498572 |

`manuscript/macros.tex` is read for the two published shares the certificate row is asserted against, and is not written to.

Nothing here samples. The dispatcher is deterministic at (rule = atc, seed = 0); the grids are literals; the matched-point tie-break is a total order. 1635 counterfactual references were recomputed in 48.6 s on 12 worker(s) pinned to cores 12-23, with the thread pools forced to one per worker. 118 assertions passed.

```
conda run -n fjsp python code/scripts/delta_baselines.py
```
