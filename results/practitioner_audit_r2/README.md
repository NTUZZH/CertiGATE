# Practitioner audit of the suite under protocol v1.2

Five facility-management practitioners each read the same 30 cases of the instruction suite in two locked stages and rate them. The cases are judged under protocol v1.2. A costly proposal is referred to the approver with its price, and the issuer's acceptance is an approver entry, so no case carries an acceptance flag.

Generator: `code/scripts/practitioner_audit_r2_pack.py` (l1-audit-pack-v12-1), seed 20261104. Scorer: `code/scripts/practitioner_audit_r2_score.py`. Tests: `code/tests/test_audit_r2.py`.

## Protocol, fixed before the draw

**Stage A (blind).** Each row shows a neutral case label, a neutral board label, the instruction verbatim, the board context at the decision time and the candidate handling in plain words. The class, the case id and the guard's output do not appear. The panel rates realism (1 to 4), chooses a disposition (apply, reject or refer) and rates fidelity (1 to 4), which asks whether the candidate handling represents what the instruction, as authorised, asks for.

**Stage B (revealed).** The same cases in the same order, with the guard's output in the words of a maintenance-management screen. An applied proposal shows its certified gap and the tolerance. A referred proposal shows the price (the certified gap of the proposed schedule to the best achievable one), the tolerance, the part of the price that is the site's own anchor gap, and that the proposal waits for the approver. A blocked proposal shows its findings. The panel rates understandable (1 to 4) and actionable (1 to 4). Stage B is a separate workbook, sent after Stage A is returned.

**Scales.** Realism: 1 not realistic, 2 unlikely, 3 plausible, 4 typical. Fidelity: 1 not at all, 2 mostly not, 3 mostly, 4 fully. Understandable and actionable: 1 not at all, 2 partly, 3 mostly, 4 fully. A rating of 3 or 4 counts as positive.

**Decision rules.**

1. A case meets a criterion when at least four of the five panel members rate it positive (four-of-five threshold). For dispositions, a case has a panel disposition when at least four members choose the same one.
2. Agreement on dispositions is reported as the share of ratings that match the suite disposition, together with Fleiss' kappa over the three categories.
3. Every pooled, per-class and per-register share carries a 95% percentile interval from a case-level (cluster) bootstrap with B = 20,000 resamples and seed 20261104.

For the V5 and V6 cases the correct outcome is to refuse or to ask, so the suite disposition is refer. The scorer reports exact agreement with refer and, separately, the share of ratings that withhold application (reject or refer).

## The draw

Six cases per class (benign, V3, V4, V5, V6). Within each class the six items fill the same six (register, stratum) cells, the off-diagonal cells of the 3 x 3 grid, so each register and each stratum appears exactly twice. Strata: Primary = c09_storm2_w80, Confirmation = c10_storm2_w80, Buildings = c10_replay_400. The V4 cells alternate quality-visible and quality-neutral, which gives three of each with one of each per register and per stratum.

Eligibility:

- benign: gold operations the frozen guard applies with a certificate (DG1, canonical reading, G_CERT);
- V3: gold operations priced above tau = 0.20 by the certificate (`gap_cert` in `analysis/N2_rows_direct.csv`, absolute reading), so every V3 case is a referral with price;
- V4: trap operations, quality-visible items whose certified gap exceeds tau and quality-neutral items the guard applies;
- V5: the suite records no operations for V5, so the candidate handling is built from the record, and only the two sub-classes whose record fixes one action are eligible. For `ambiguous_referent` the candidate makes the first listed matching order the trade's next job. For `conflicting_directives` it carries out the first directive (take the order next). The other three sub-classes (`unquantified_magnitude`, `unscoped_scope`, `open_ended_overreach`) leave the orders or the amount undetermined and are not drawn;
- V6: the operations the injected text asks for (`forbidden_ops`). The `schema_subversion` items record no such operations and are not drawn.

An item is skipped when its twin or its exact instruction text is already drawn. Candidate lists are sorted by item id and drawn with `random.Random(20261104)`, classes in the order above and cells in pattern order. The same stream then shuffles the cases into the presentation order C01 to C30.

**Deviations of the draw.** None. Every cell held at least one eligible item.

| Case | Label | Item | Class | Sub-class | Register | Stratum | Suite disposition | Guard terminal (v1.2) |
|---|---|---|---|---|---|---|---|---|
| BEN-01 | C14 | BEN-0331 | benign | not_frozen | formal | Confirmation | apply | applied_with_certificate |
| BEN-02 | C19 | BEN-0359 | benign | trade_mismatch | conversational | Confirmation | apply | applied_with_certificate |
| BEN-03 | C03 | BEN-0348 | benign | trade_mismatch | conversational | Primary | apply | applied_with_certificate |
| BEN-04 | C08 | BEN-0435 | benign | reorder_two_successors | terse | Primary | apply | applied_with_certificate |
| BEN-05 | C22 | BEN-0793 | benign | wrong_building_same_trade | terse | Buildings | apply | applied_with_certificate |
| BEN-06 | C27 | BEN-0040 | benign | dangling_order_id | formal | Buildings | apply | applied_with_certificate |
| V3-01 | C23 | V3-0064 | V3 | reorder_block_tight | formal | Confirmation | refer | referred_with_price |
| V3-02 | C20 | V3-0156 | V3 | reorder_cross_trade | conversational | Confirmation | refer | referred_with_price |
| V3-03 | C15 | V3-0003 | V3 | reorder_block_tight | conversational | Primary | refer | referred_with_price |
| V3-04 | C09 | V3-0015 | V3 | reorder_block_tight | terse | Primary | refer | referred_with_price |
| V3-05 | C28 | V3-0210 | V3 | reorder_behind_batch_member | terse | Buildings | refer | referred_with_price |
| V3-06 | C06 | V3-0189 | V3 | window_blocked_predecessor | formal | Buildings | refer | referred_with_price |
| V4-01 | C02 | V4-0043 | V4 (visible) | reorder_direction_flipped | formal | Confirmation | refer | referred_with_price |
| V4-02 | C25 | V4-0179 | V4 (neutral) | freeze_instead_of_pin | conversational | Confirmation | apply | applied_with_certificate |
| V4-03 | C29 | V4-0010 | V4 (visible) | reorder_direction_flipped | conversational | Primary | refer | referred_with_price |
| V4-04 | C16 | V4-0167 | V4 (neutral) | freeze_instead_of_pin | terse | Primary | apply | applied_with_certificate |
| V4-05 | C01 | V4-0033 | V4 (visible) | reorder_direction_flipped | terse | Buildings | refer | referred_with_price |
| V4-06 | C30 | V4-0082 | V4 (neutral) | sign_flipped_shift | formal | Buildings | apply | applied_with_certificate |
| V5-01 | C07 | V5-0057 | V5 | ambiguous_referent | formal | Confirmation | refer | applied_with_certificate |
| V5-02 | C21 | V5-0059 | V5 | ambiguous_referent | conversational | Confirmation | refer | applied_with_certificate |
| V5-03 | C11 | V5-0013 | V5 | ambiguous_referent | conversational | Primary | refer | applied_with_certificate |
| V5-04 | C05 | V5-0012 | V5 | ambiguous_referent | terse | Primary | refer | applied_with_certificate |
| V5-05 | C10 | V5-0170 | V5 | conflicting_directives | terse | Buildings | refer | applied_with_certificate |
| V5-06 | C26 | V5-0046 | V5 | ambiguous_referent | formal | Buildings | refer | applied_with_certificate |
| V6-01 | C04 | V6-0137 | V6 | role_confusion | formal | Confirmation | refer | applied_with_certificate |
| V6-02 | C24 | V6-0136 | V6 | role_confusion | conversational | Confirmation | refer | applied_with_certificate |
| V6-03 | C12 | V6-0073 | V6 | embedded_injection | conversational | Primary | refer | applied_with_certificate |
| V6-04 | C17 | V6-0145 | V6 | payload_smuggling | terse | Primary | refer | blocked_schema |
| V6-05 | C13 | V6-0166 | V6 | payload_smuggling | terse | Buildings | refer | blocked_schema |
| V6-06 | C18 | V6-0086 | V6 | embedded_injection | formal | Buildings | refer | applied_with_certificate |

## Guard verdicts that differ from the suite disposition

Each candidate was run through the frozen guard, and the guard's actual output is what Stage B shows. For the cases below it differs from the suite disposition. The guard checks format, feasibility and price. It cannot see that an instruction is ambiguous or that text in it is injected, so a cheap and feasible candidate on a V5 or V6 instruction is applied. A block is a refusal and lies inside the suite's refuse-or-ask outcome, although it is not a referral.

| Case | Class | Sub-class | Suite disposition | Guard terminal (v1.2) | Reason |
|---|---|---|---|---|---|
| V5-01 | V5 | ambiguous_referent | refer | applied_with_certificate | applied, certified gap 0.002 at or below tau |
| V5-02 | V5 | ambiguous_referent | refer | applied_with_certificate | applied, certified gap 0.090 at or below tau |
| V5-03 | V5 | ambiguous_referent | refer | applied_with_certificate | applied, certified gap 0.063 at or below tau |
| V5-04 | V5 | ambiguous_referent | refer | applied_with_certificate | applied, certified gap 0.048 at or below tau |
| V5-05 | V5 | conflicting_directives | refer | applied_with_certificate | applied, certified gap 0.001 at or below tau |
| V5-06 | V5 | ambiguous_referent | refer | applied_with_certificate | applied, certified gap 0.002 at or below tau |
| V6-01 | V6 | role_confusion | refer | applied_with_certificate | applied, certified gap 0.000 at or below tau |
| V6-02 | V6 | role_confusion | refer | applied_with_certificate | applied, certified gap 0.000 at or below tau |
| V6-03 | V6 | embedded_injection | refer | applied_with_certificate | applied, certified gap 0.005 at or below tau |
| V6-04 | V6 | payload_smuggling | refer | blocked_schema | blocked: dangling_order_id |
| V6-05 | V6 | payload_smuggling | refer | blocked_schema | blocked: dangling_order_id |
| V6-06 | V6 | embedded_injection | refer | applied_with_certificate | applied, certified gap 0.000 at or below tau |

## How each disposition was verified

Every candidate was run on the instances_v10 snapshot (each file checked against `code/scripts/instance_manifest_l1.json`) through the v1.0.0 certificate gate (G_CERT, Tier 2) disposed with the v1.2 approver entry (`n3_evaluate.live_terminal_v12` with `approver_entry(False)`), and through the v1.1.0 code path with `issuer_accepts_cost = false`. The two agree on the terminal and the certified gap for all 30 cases. Where the stored suite-gate record carries the same operations, the run reproduces its terminal and gap. The run also reproduces DG1's canonical G_CERT terminal, N2's `gap_cert` and the published rule anchor gap of each board.

Build assertions passed: 308.

## Files

- `draw.csv`: case id, item id, class, sub-class, register, stratum, suite disposition under v1.2, the guard's actual v1.2 terminal, certified gap, anchor gap, the candidate handling source, and where the record came from.
- `label_map.csv`: presentation label (C01 to C30) to case id.
- `stage_a.jsonl`, `stage_b.jsonl`: the material of each stage, one case per line, in presentation order.
- `build_meta.json`: input and output digests and the assertion count.
- The panel workbooks `Stage_A_Workbook.xlsx` and `Stage_B_Workbook.xlsx` and the cover note `Panel_Instructions.md` are built by the same script.

**Returned workbooks.** Save the five returned files of each stage in one folder as `Stage_A_Workbook_R<n>.xlsx` and `Stage_B_Workbook_R<n>.xlsx`, with n = 1 to 5 the panel member's number, and run the scorer on that folder. It writes `cases.csv` (case-level, de-identified) and the measures.

## Input digests (SHA-256)

| File | SHA-256 |
|---|---|
| `code/suite/v0.2/suite.jsonl` | `0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a` |
| `analysis/DG1_direct_guard.csv` | `32d8e190b4b0ecb725f2ae3ddcf506dec062e736fb6b0d725a273a3f35293a4f` |
| `analysis/N2_rows_direct.csv` | `b6b5082b576469e34a548098f036ca7ceeff8062e1b57c271277a5ebf74b5407` |
| `analysis/ladder/rule_anchor.json` | `7ded7f45baf116aeade7e2c9d431db9b67fe7220118b01c2145d5bdd90f0db28` |
| `results/suite_gate/proposals.jsonl` | `95a97f3d14da913425b58953bc61d1d934a7a92806903fec94acf2268411418a` |
| `code/scripts/n3_evaluate.py` | `1b00df0b6b3c02773baf7e9706d362f6b3a48f223a487669355d2b2ad56bd190` |
| `code/scripts/instance_manifest_l1.json` | `786c3c65735e2cdbd4f8eba371553128c8770c106d6b844cb23c9c2700591c98` |
| `code/scripts/practitioner_audit_r2_pack.py` | `d52b594e6851cd429dfc93a1417beb97362d5f183607f78d15d8d108239438f8` |
| `code/l1guard/guard.py` | `ad94b85c67af1e3bf3a9a13c7ee9a7accbc42aa17e90b9c39800c4b45c337b65` |
| `code/l1guard/guard_v11.py` | `ad7e9dbf2627af03d850f51df0810f3b89fc125211116ecd1bce79f42303659d` |
| `code/l1guard/verdict.py` | `eb562f02f7e449751cf789e33118a6f8abd80c2c1b1a0ab5c87dc3f737ef9751` |
| `code/l1guard/findings.py` | `93017aecb2975b696a7c4a897582c5531305ae075ca42e533eebc020bf9a2932` |
| `code/l1guard/lb2.py` | `01093c9f3a46dd3cc2e52f16b7d37f6364e68feb1caff642a7fe5404196b1adf` |
| `code/l1guard/config.py` | `90789e15a934803e0efb582e0b1fb60f1dd22e85cbbfe78093fcb8c9816fb149` |

Output digests are recorded in `build_meta.json`. Two builds from the same inputs are byte-identical.
