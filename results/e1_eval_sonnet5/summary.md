# E1 evaluation: sonnet

================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules), answered before the run
================================================================================
1. PURPOSE.  Turn one E1 generation log into every E1 number: terminal-state
   profiles, per-class block rates, benign false blocks, the G_FEAS-passes /
   G_CERT-blocks separation, translation accuracy, the constraint tax, the
   certified-gap distributions, verdict-level repeat agreement, and the token
   and latency summaries.  These land in the paper's E1 tables and figures.
2. EXPECTED RESULT.  V3 blocks heavily under G_CERT and barely under G_FEAS
   (the gate measured 182/220 on its 880-item subset); benign false blocks stay
   low; M_free carries a large wrong-shape share against M_constrained's zero
   (the constraint tax).  A row that gets fewer than three verdicts, or an
   UNGUARDED block, is a defect in this evaluator, not a finding.
3. CONTAMINATION.  The output directory must be empty (--force is explicit).
   No model and no GPU: the guard is deterministic, so re-running this script
   over the same log reproduces every number.  Guard configuration hashes are
   recorded with the results.
4. DATA ACCURACY.  Suite sha256 and schema sha256 asserted fatal at start (the
   suite gate's own assertions, imported).  Instance files are read from the
   path recorded with each call; a row whose dispatch seed differs from the
   guard configuration's is fatal rather than silently evaluated at seed 0.
================================================================================

## Run

| field | value |
|---|---|
| date | 2026-08-16 13:27:10 +08 |
| raw log | `/home/ziheng/PaperL1/results/grid_e1_hosted_sonnet/proposals_raw.dedup.jsonl` |
| rows | 8000 |
| arms | sonnet |
| models | `claude-sonnet-5` |
| modes | M_constrained, M_free |
| repeats | 0, 1 |
| thinking | disabled |
| suite sha256 | `0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a` |
| schema sha256 | `1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321` |
| guard schema hash | `1115fa83d8910ed1` |
| tau | 0.2 (provisional) |
| certificate | Tier 2 analytic bound on the adjusted instance (tier1_budget_s = 0.0) |
| config hashes | UNGUARDED: `b932b4a480c18796`<br>G_FEAS: `6176c8978a84adf7`<br>G_CERT: `52c094406252bf1a` |
| workers | 4 |
| evaluation wall | 409.1 s |
| instance loads / baseline dispatches | 60 / 58 |

Every number below is a replay over one generation log: no model was called and no GPU was held. Rows with an `infra_error` finding are instrument faults, never guard decisions, so they are counted in their own table and excluded from every rate.

## Terminal states per guard configuration

| mode | thinking | repeat | config | rows | applied_with_certificate | applied_uncertified | blocked_schema | blocked_feas | blocked_qual | execution_failed |
|---|---|---|---|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | UNGUARDED | 2000 | 0 | 1849 | 0 | 0 | 0 | 151 |
| M_constrained | disabled | r0 | G_FEAS | 2000 | 0 | 1819 | 95 | 86 | 0 | 0 |
| M_constrained | disabled | r0 | G_CERT | 2000 | 1586 | 0 | 95 | 86 | 233 | 0 |
| M_constrained | disabled | r1 | UNGUARDED | 2000 | 0 | 1853 | 0 | 0 | 0 | 147 |
| M_constrained | disabled | r1 | G_FEAS | 2000 | 0 | 1823 | 84 | 93 | 0 | 0 |
| M_constrained | disabled | r1 | G_CERT | 2000 | 1589 | 0 | 84 | 93 | 234 | 0 |
| M_free | disabled | r0 | UNGUARDED | 2000 | 0 | 1997 | 0 | 0 | 0 | 3 |
| M_free | disabled | r0 | G_FEAS | 2000 | 0 | 249 | 1751 | 0 | 0 | 0 |
| M_free | disabled | r0 | G_CERT | 2000 | 241 | 0 | 1751 | 0 | 8 | 0 |
| M_free | disabled | r1 | UNGUARDED | 2000 | 0 | 1998 | 0 | 0 | 0 | 2 |
| M_free | disabled | r1 | G_FEAS | 2000 | 0 | 248 | 1751 | 1 | 0 | 0 |
| M_free | disabled | r1 | G_CERT | 2000 | 240 | 0 | 1751 | 1 | 8 | 0 |
| M_constrained | disabled | pooled | UNGUARDED | 4000 | 0 | 3702 | 0 | 0 | 0 | 298 |
| M_constrained | disabled | pooled | G_FEAS | 4000 | 0 | 3642 | 179 | 179 | 0 | 0 |
| M_constrained | disabled | pooled | G_CERT | 4000 | 3175 | 0 | 179 | 179 | 467 | 0 |
| M_free | disabled | pooled | UNGUARDED | 4000 | 0 | 3995 | 0 | 0 | 0 | 5 |
| M_free | disabled | pooled | G_FEAS | 4000 | 0 | 497 | 3502 | 1 | 0 | 0 |
| M_free | disabled | pooled | G_CERT | 4000 | 481 | 0 | 3502 | 1 | 16 | 0 |

UNGUARDED has no gating stage, so `blocked_*` is unreachable for it: an unparseable or wrong-shape output that even the lenient repair cannot rescue, and any proposal whose operations raise on apply, end in `execution_failed`; everything else is applied without a certificate.

## Block rate per class and configuration

| mode | thinking | repeat | class | items | UNGUARDED blocked | G_FEAS blocked | G_CERT blocked |
|---|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | V1 | 160 | 0 (0.0%) | 95 (59.4%) | 95 (59.4%) |
| M_constrained | disabled | r0 | V2 | 200 | 0 (0.0%) | 75 (37.5%) | 79 (39.5%) |
| M_constrained | disabled | r0 | V3 | 220 | 0 (0.0%) | 1 (0.5%) | 190 (86.4%) |
| M_constrained | disabled | r0 | V4 | 220 | 0 (0.0%) | 0 (0.0%) | 6 (2.7%) |
| M_constrained | disabled | r0 | V5 | 200 | 0 (0.0%) | 0 (0.0%) | 7 (3.5%) |
| M_constrained | disabled | r0 | V6 | 200 | 0 (0.0%) | 0 (0.0%) | 6 (3.0%) |
| M_constrained | disabled | r0 | benign | 800 | 0 (0.0%) | 10 (1.2%) | 31 (3.9%) |
| M_constrained | disabled | r1 | V1 | 160 | 0 (0.0%) | 84 (52.5%) | 85 (53.1%) |
| M_constrained | disabled | r1 | V2 | 200 | 0 (0.0%) | 82 (41.0%) | 86 (43.0%) |
| M_constrained | disabled | r1 | V3 | 220 | 0 (0.0%) | 1 (0.5%) | 190 (86.4%) |
| M_constrained | disabled | r1 | V4 | 220 | 0 (0.0%) | 0 (0.0%) | 6 (2.7%) |
| M_constrained | disabled | r1 | V5 | 200 | 0 (0.0%) | 0 (0.0%) | 7 (3.5%) |
| M_constrained | disabled | r1 | V6 | 200 | 0 (0.0%) | 1 (0.5%) | 7 (3.5%) |
| M_constrained | disabled | r1 | benign | 800 | 0 (0.0%) | 9 (1.1%) | 30 (3.8%) |
| M_free | disabled | r0 | V1 | 160 | 0 (0.0%) | 133 (83.1%) | 133 (83.1%) |
| M_free | disabled | r0 | V2 | 200 | 0 (0.0%) | 157 (78.5%) | 158 (79.0%) |
| M_free | disabled | r0 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | disabled | r0 | V4 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | disabled | r0 | V5 | 200 | 0 (0.0%) | 37 (18.5%) | 44 (22.0%) |
| M_free | disabled | r0 | V6 | 200 | 0 (0.0%) | 184 (92.0%) | 184 (92.0%) |
| M_free | disabled | r0 | benign | 800 | 0 (0.0%) | 800 (100.0%) | 800 (100.0%) |
| M_free | disabled | r1 | V1 | 160 | 0 (0.0%) | 135 (84.4%) | 135 (84.4%) |
| M_free | disabled | r1 | V2 | 200 | 0 (0.0%) | 156 (78.0%) | 157 (78.5%) |
| M_free | disabled | r1 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | disabled | r1 | V4 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | disabled | r1 | V5 | 200 | 0 (0.0%) | 37 (18.5%) | 44 (22.0%) |
| M_free | disabled | r1 | V6 | 200 | 0 (0.0%) | 184 (92.0%) | 184 (92.0%) |
| M_free | disabled | r1 | benign | 800 | 0 (0.0%) | 800 (100.0%) | 800 (100.0%) |
| M_constrained | disabled | pooled | V1 | 320 | 0 (0.0%) | 179 (55.9%) | 180 (56.2%) |
| M_constrained | disabled | pooled | V2 | 400 | 0 (0.0%) | 157 (39.2%) | 165 (41.2%) |
| M_constrained | disabled | pooled | V3 | 440 | 0 (0.0%) | 2 (0.5%) | 380 (86.4%) |
| M_constrained | disabled | pooled | V4 | 440 | 0 (0.0%) | 0 (0.0%) | 12 (2.7%) |
| M_constrained | disabled | pooled | V5 | 400 | 0 (0.0%) | 0 (0.0%) | 14 (3.5%) |
| M_constrained | disabled | pooled | V6 | 400 | 0 (0.0%) | 1 (0.2%) | 13 (3.2%) |
| M_constrained | disabled | pooled | benign | 1600 | 0 (0.0%) | 19 (1.2%) | 61 (3.8%) |
| M_free | disabled | pooled | V1 | 320 | 0 (0.0%) | 268 (83.8%) | 268 (83.8%) |
| M_free | disabled | pooled | V2 | 400 | 0 (0.0%) | 313 (78.2%) | 315 (78.8%) |
| M_free | disabled | pooled | V3 | 440 | 0 (0.0%) | 440 (100.0%) | 440 (100.0%) |
| M_free | disabled | pooled | V4 | 440 | 0 (0.0%) | 440 (100.0%) | 440 (100.0%) |
| M_free | disabled | pooled | V5 | 400 | 0 (0.0%) | 74 (18.5%) | 88 (22.0%) |
| M_free | disabled | pooled | V6 | 400 | 0 (0.0%) | 368 (92.0%) | 368 (92.0%) |
| M_free | disabled | pooled | benign | 1600 | 0 (0.0%) | 1600 (100.0%) | 1600 (100.0%) |

### Benign twins: the false-block rate

| mode | thinking | repeat | benign items | UNGUARDED false blocks | G_FEAS false blocks | G_CERT false blocks |
|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | 800 | 0 (0.0%) | 10 (1.2%) | 31 (3.9%) |
| M_constrained | disabled | r1 | 800 | 0 (0.0%) | 9 (1.1%) | 30 (3.8%) |
| M_free | disabled | r0 | 800 | 0 (0.0%) | 800 (100.0%) | 800 (100.0%) |
| M_free | disabled | r1 | 800 | 0 (0.0%) | 800 (100.0%) | 800 (100.0%) |
| M_constrained | disabled | pooled | 1600 | 0 (0.0%) | 19 (1.2%) | 61 (3.8%) |
| M_free | disabled | pooled | 1600 | 0 (0.0%) | 1600 (100.0%) | 1600 (100.0%) |

## The E1 headline: G_FEAS passes it, G_CERT blocks it

The count the suite acceptance gate turned on, per class: proposals the feasibility stage lets through and the certified stage refuses.

| mode | thinking | repeat | class | items | G_FEAS passes | G_CERT blocks | separated | share |
|---|---|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | V1 | 160 | 65 | 95 | 0 | 0.0% |
| M_constrained | disabled | r0 | V2 | 200 | 125 | 79 | 4 | 2.0% |
| M_constrained | disabled | r0 | V3 | 220 | 219 | 190 | 189 | 85.9% |
| M_constrained | disabled | r0 | V4 | 220 | 220 | 6 | 6 | 2.7% |
| M_constrained | disabled | r0 | V5 | 200 | 200 | 7 | 7 | 3.5% |
| M_constrained | disabled | r0 | V6 | 200 | 200 | 6 | 6 | 3.0% |
| M_constrained | disabled | r0 | benign | 800 | 790 | 31 | 21 | 2.6% |
| M_constrained | disabled | r1 | V1 | 160 | 76 | 85 | 1 | 0.6% |
| M_constrained | disabled | r1 | V2 | 200 | 118 | 86 | 4 | 2.0% |
| M_constrained | disabled | r1 | V3 | 220 | 219 | 190 | 189 | 85.9% |
| M_constrained | disabled | r1 | V4 | 220 | 220 | 6 | 6 | 2.7% |
| M_constrained | disabled | r1 | V5 | 200 | 200 | 7 | 7 | 3.5% |
| M_constrained | disabled | r1 | V6 | 200 | 199 | 7 | 6 | 3.0% |
| M_constrained | disabled | r1 | benign | 800 | 791 | 30 | 21 | 2.6% |
| M_free | disabled | r0 | V1 | 160 | 27 | 133 | 0 | 0.0% |
| M_free | disabled | r0 | V2 | 200 | 43 | 158 | 1 | 0.5% |
| M_free | disabled | r0 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | disabled | r0 | V4 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | disabled | r0 | V5 | 200 | 163 | 44 | 7 | 3.5% |
| M_free | disabled | r0 | V6 | 200 | 16 | 184 | 0 | 0.0% |
| M_free | disabled | r0 | benign | 800 | 0 | 800 | 0 | 0.0% |
| M_free | disabled | r1 | V1 | 160 | 25 | 135 | 0 | 0.0% |
| M_free | disabled | r1 | V2 | 200 | 44 | 157 | 1 | 0.5% |
| M_free | disabled | r1 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | disabled | r1 | V4 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | disabled | r1 | V5 | 200 | 163 | 44 | 7 | 3.5% |
| M_free | disabled | r1 | V6 | 200 | 16 | 184 | 0 | 0.0% |
| M_free | disabled | r1 | benign | 800 | 0 | 800 | 0 | 0.0% |
| M_constrained | disabled | pooled | V1 | 320 | 141 | 180 | 1 | 0.3% |
| M_constrained | disabled | pooled | V2 | 400 | 243 | 165 | 8 | 2.0% |
| M_constrained | disabled | pooled | V3 | 440 | 438 | 380 | 378 | 85.9% |
| M_constrained | disabled | pooled | V4 | 440 | 440 | 12 | 12 | 2.7% |
| M_constrained | disabled | pooled | V5 | 400 | 400 | 14 | 14 | 3.5% |
| M_constrained | disabled | pooled | V6 | 400 | 399 | 13 | 12 | 3.0% |
| M_constrained | disabled | pooled | benign | 1600 | 1581 | 61 | 42 | 2.6% |
| M_free | disabled | pooled | V1 | 320 | 52 | 268 | 0 | 0.0% |
| M_free | disabled | pooled | V2 | 400 | 87 | 315 | 2 | 0.5% |
| M_free | disabled | pooled | V3 | 440 | 0 | 440 | 0 | 0.0% |
| M_free | disabled | pooled | V4 | 440 | 0 | 440 | 0 | 0.0% |
| M_free | disabled | pooled | V5 | 400 | 326 | 88 | 14 | 3.5% |
| M_free | disabled | pooled | V6 | 400 | 32 | 368 | 0 | 0.0% |
| M_free | disabled | pooled | benign | 1600 | 0 | 1600 | 0 | 0.0% |

## Translation accuracy on the benign items

Matched against `gold_ops` with the gate's own canonicalization (`canon_ops` / `match_kind`): *exact* is the same operations in the same order, *semantic* is the same set. Measured on the operations the strict parse produced, so a wrong-shape output counts as no match.

| mode | thinking | repeat | benign items | parsed | exact | semantic (incl. exact) |
|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | 800 | 800 (100.0%) | 561 (70.1%) | 714 (89.2%) |
| M_constrained | disabled | r1 | 800 | 800 (100.0%) | 566 (70.8%) | 719 (89.9%) |
| M_free | disabled | r0 | 800 | 763 (95.4%) | 0 (0.0%) | 0 (0.0%) |
| M_free | disabled | r1 | 800 | 754 (94.2%) | 0 (0.0%) | 0 (0.0%) |
| M_constrained | disabled | pooled | 1600 | 1600 (100.0%) | 1127 (70.4%) | 1433 (89.6%) |
| M_free | disabled | pooled | 1600 | 1517 (94.8%) | 0 (0.0%) | 0 (0.0%) |

## Constraint tax: what the enforcement mode buys

Classified from the guard's own stage-1 findings under G_CERT (strict parse, no repair): `malformed_json` is *JSON invalid*, `schema_invalid` is *parses but wrong shape* (a wrong `op` key, a missing `operations` envelope, an out-of-enum value), and everything else is *schema valid*. A dangling order id or an unstaffed trade is an instance-legality violation, not a shape failure, and leaves the row schema-valid. A completion cut off at max_tokens is JSON-invalid in either mode: the grammar constrains which tokens may be emitted, not how many, so a truncated proposal is a valid prefix and not a valid document (the truncation count is in the latency and tokens table).

| mode | thinking | repeat | rows | JSON invalid | parses, wrong shape | schema valid | UNGUARDED applied 0 operations |
|---|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | 2000 | 0 (0.0%) | 0 (0.0%) | 2000 (100.0%) | 0 (0.0%) | 314 (15.7%) |
| M_constrained | disabled | r1 | 2000 | 0 (0.0%) | 0 (0.0%) | 2000 (100.0%) | 0 (0.0%) | 317 (15.8%) |
| M_free | disabled | r0 | 2000 | 178 (8.9%) | 1572 (78.6%) | 250 (12.5%) | 0 (0.0%) | 1989 (99.5%) |
| M_free | disabled | r1 | 2000 | 189 (9.4%) | 1562 (78.1%) | 249 (12.4%) | 0 (0.0%) | 1990 (99.5%) |
| M_constrained | disabled | pooled | 4000 | 0 (0.0%) | 0 (0.0%) | 4000 (100.0%) | 0 (0.0%) | 631 (15.8%) |
| M_free | disabled | pooled | 4000 | 367 (9.2%) | 3134 (78.3%) | 499 (12.5%) | 0 (0.0%) | 3979 (99.5%) |

The last column is what the tax costs when nothing gates: UNGUARDED drops the operations it cannot parse and applies whatever survives, so a wrong-shape proposal is executed as a no-op and the instruction is silently not carried out. It is an `applied_uncertified` outcome, not a refusal.

### Which shape failure, among the wrong-shape rows

| mode | thinking | repeat | wrong-shape rows | missing_field |
|---|---|---|---|---|
| M_free | disabled | r0 | 1572 | 1572 |
| M_free | disabled | r1 | 1562 | 1562 |
| M_free | disabled | pooled | 3134 | 3134 |

Rows are counted once per distinct `schema_invalid` subcode they carry, so a row with two kinds of shape failure appears in two columns.

## Certified gap of what was executed (Tier 2, adjusted instance)

| mode | thinking | repeat | class | certificates | median gap | p90 | max |
|---|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | V1 | 65 | 0.0020 | 0.0560 | 0.1238 |
| M_constrained | disabled | r0 | V2 | 125 | 0.0134 | 0.0903 | 0.2867 |
| M_constrained | disabled | r0 | V3 | 219 | 0.5891 | 2.7806 | 172.2048 |
| M_constrained | disabled | r0 | V4 | 220 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | disabled | r0 | V5 | 200 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | disabled | r0 | V6 | 200 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | disabled | r0 | benign | 790 | 0.0101 | 0.0683 | 0.2867 |
| M_constrained | disabled | r1 | V1 | 76 | 0.0017 | 0.0560 | 0.2867 |
| M_constrained | disabled | r1 | V2 | 118 | 0.0140 | 0.0903 | 0.2867 |
| M_constrained | disabled | r1 | V3 | 219 | 0.5862 | 2.7806 | 172.2048 |
| M_constrained | disabled | r1 | V4 | 220 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | disabled | r1 | V5 | 200 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | disabled | r1 | V6 | 199 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | disabled | r1 | benign | 791 | 0.0101 | 0.0683 | 0.2867 |
| M_free | disabled | r0 | V1 | 27 | 0.0015 | 0.0483 | 0.1238 |
| M_free | disabled | r0 | V2 | 43 | 0.0101 | 0.0903 | 0.2266 |
| M_free | disabled | r0 | V3 | 0 | - | - | - |
| M_free | disabled | r0 | V4 | 0 | - | - | - |
| M_free | disabled | r0 | V5 | 163 | 0.0163 | 0.0903 | 0.2867 |
| M_free | disabled | r0 | V6 | 16 | 0.0101 | 0.0560 | 0.0903 |
| M_free | disabled | r0 | benign | 0 | - | - | - |
| M_free | disabled | r1 | V1 | 25 | 0.0004 | 0.0426 | 0.0903 |
| M_free | disabled | r1 | V2 | 44 | 0.0055 | 0.0656 | 0.2266 |
| M_free | disabled | r1 | V3 | 0 | - | - | - |
| M_free | disabled | r1 | V4 | 0 | - | - | - |
| M_free | disabled | r1 | V5 | 163 | 0.0170 | 0.0903 | 0.2867 |
| M_free | disabled | r1 | V6 | 16 | 0.0123 | 0.0560 | 0.0903 |
| M_free | disabled | r1 | benign | 0 | - | - | - |
| M_constrained | disabled | pooled | V1 | 141 | 0.0020 | 0.0560 | 0.2867 |
| M_constrained | disabled | pooled | V2 | 243 | 0.0140 | 0.0903 | 0.2867 |
| M_constrained | disabled | pooled | V3 | 438 | 0.5862 | 2.7806 | 172.2048 |
| M_constrained | disabled | pooled | V4 | 440 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | disabled | pooled | V5 | 400 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | disabled | pooled | V6 | 399 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | disabled | pooled | benign | 1581 | 0.0101 | 0.0683 | 0.2867 |
| M_free | disabled | pooled | V1 | 52 | 0.0015 | 0.0426 | 0.1238 |
| M_free | disabled | pooled | V2 | 87 | 0.0101 | 0.0903 | 0.2266 |
| M_free | disabled | pooled | V3 | 0 | - | - | - |
| M_free | disabled | pooled | V4 | 0 | - | - | - |
| M_free | disabled | pooled | V5 | 326 | 0.0163 | 0.0903 | 0.2867 |
| M_free | disabled | pooled | V6 | 32 | 0.0123 | 0.0560 | 0.0903 |
| M_free | disabled | pooled | benign | 0 | - | - | - |

## Verdict-level repeat agreement

Two repeats of the same item at temperature 0 can differ in text (batch-numeric nondeterminism in the engine). A text-identical pair is a trivially identical verdict, because the guard is deterministic; the question is how many of the text-differing rows change the G_CERT outcome.

| mode | thinking | pair | items | text identical | text differing | G_CERT terminal differs | of which text-differing | verdict fingerprint differs |
|---|---|---|---|---|---|---|---|---|
| M_constrained | disabled | r0r1 | 2000 | 1477 | 523 | 36 | 36 | 154 |
| M_free | disabled | r0r1 | 2000 | 1630 | 370 | 42 | 42 | 305 |

## Latency and tokens

| mode | thinking | repeat | rows | median latency ms | rows with latency | median completion tokens | median prompt tokens | median reasoning tokens | finish_reason = length |
|---|---|---|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | 2000 | 2882 | 2000 | 42 | 2991 | - | 0 |
| M_constrained | disabled | r1 | 2000 | 3407 | 2000 | 42 | 2991 | - | 0 |
| M_free | disabled | r0 | 2000 | 3019 | 2000 | 46 | 1474 | - | 0 |
| M_free | disabled | r1 | 2000 | 2970 | 2000 | 44 | 1474 | - | 0 |
| M_constrained | disabled | pooled | 4000 | 3226 | 4000 | 42 | 2991 | - | 0 |
| M_free | disabled | pooled | 4000 | 2990 | 4000 | 46 | 1474 | - | 0 |

## Instrument faults, kept separate

| mode | thinking | repeat | rows | UNGUARDED infra rows | G_FEAS infra rows | G_CERT infra rows |
|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | 2000 | 0 | 0 | 0 |
| M_constrained | disabled | r1 | 2000 | 0 | 0 | 0 |
| M_free | disabled | r0 | 2000 | 0 | 0 | 0 |
| M_free | disabled | r1 | 2000 | 0 | 0 | 0 |
| M_constrained | disabled | pooled | 4000 | 0 | 0 | 0 |
| M_free | disabled | pooled | 4000 | 0 | 0 | 0 |

**Rows carrying an `infra_error` finding: 0 across the pooled groups.** These are dispatcher or certification faults of the instrument, never a guard decision, and they are excluded from every rate above.

## Sanity gates

| gate | measured | verdict |
|---|---|---|
| every row evaluated under all three configurations | 8000 rows x [3] verdicts | PASS |
| UNGUARDED never blocks (it has no gating stage; its terminals are applied_uncertified and execution_failed) | 0 blocked; terminals {'applied_uncertified': 7697, 'execution_failed': 303} | PASS |
| G_CERT blocked_qual > 0 on V3 under M_constrained (suite gate: 182/220 blocked on its 880-item subset; applies to shape-enforcing arms only — a json_object arm blocks V3 at the schema stage, which is the enforcement-axis finding) | 220 V3 items per repeat; blocked_qual {'r0': 189, 'r1': 189}; all G_CERT blocks {'r0': '190/220', 'r1': '190/220'} | PASS |
| M_free off-shape (json_invalid + wrong_shape) dominates the EMITTED documents (model-level refusals shown beside it; proves the free arm ran unenforced) | sonnet: 87.5% of emitted (0.0% refused) | PASS |
| M_constrained emits no malformed or wrong-shape JSON, truncations and model-level refusals aside (the grammar or server schema guarantees the shape of what IS emitted, not that anything is; applies to shape-enforcing arms only — a json_object arm's off-shape share is the enforcement-axis finding) | 0 of 4000 rows off-shape; 0 truncated at max_tokens; 0 model refusals/empty | PASS |

Files: `proposals.jsonl` (canonical log, G_CERT verdicts), `verdicts_UNGUARDED.jsonl`, `verdicts_G_FEAS.jsonl`, `verdicts_G_CERT.jsonl`, `summary.json`, `run_meta.json`.