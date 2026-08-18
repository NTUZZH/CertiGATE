# E1 evaluation: openai

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
| date | 2026-08-16 13:12:13 +08 |
| raw log | `/home/ziheng/PaperL1/results/grid_e1_hosted_openai/proposals_raw.dedup.jsonl` |
| rows | 8000 |
| arms | openai |
| models | `gpt-5.4-mini-2026-03-17` |
| modes | M_constrained, M_free |
| repeats | 0, 1 |
| thinking | - |
| suite sha256 | `0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a` |
| schema sha256 | `1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321` |
| guard schema hash | `1115fa83d8910ed1` |
| tau | 0.2 (provisional) |
| certificate | Tier 2 analytic bound on the adjusted instance (tier1_budget_s = 0.0) |
| config hashes | UNGUARDED: `b932b4a480c18796`<br>G_FEAS: `6176c8978a84adf7`<br>G_CERT: `52c094406252bf1a` |
| workers | 4 |
| evaluation wall | 379.3 s |
| instance loads / baseline dispatches | 60 / 58 |

Every number below is a replay over one generation log: no model was called and no GPU was held. Rows with an `infra_error` finding are instrument faults, never guard decisions, so they are counted in their own table and excluded from every rate.

## Terminal states per guard configuration

| mode | thinking | repeat | config | rows | applied_with_certificate | applied_uncertified | blocked_schema | blocked_feas | blocked_qual | execution_failed |
|---|---|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | UNGUARDED | 2000 | 0 | 1759 | 0 | 0 | 0 | 241 |
| M_constrained | - | r0 | G_FEAS | 2000 | 0 | 1722 | 142 | 136 | 0 | 0 |
| M_constrained | - | r0 | G_CERT | 2000 | 1504 | 0 | 142 | 136 | 218 | 0 |
| M_constrained | - | r1 | UNGUARDED | 2000 | 0 | 1749 | 0 | 0 | 0 | 251 |
| M_constrained | - | r1 | G_FEAS | 2000 | 0 | 1714 | 148 | 138 | 0 | 0 |
| M_constrained | - | r1 | G_CERT | 2000 | 1494 | 0 | 148 | 138 | 220 | 0 |
| M_free | - | r0 | UNGUARDED | 2000 | 0 | 2000 | 0 | 0 | 0 | 0 |
| M_free | - | r0 | G_FEAS | 2000 | 0 | 97 | 1903 | 0 | 0 | 0 |
| M_free | - | r0 | G_CERT | 2000 | 91 | 0 | 1903 | 0 | 6 | 0 |
| M_free | - | r1 | UNGUARDED | 2000 | 0 | 1998 | 0 | 0 | 0 | 2 |
| M_free | - | r1 | G_FEAS | 2000 | 0 | 98 | 1902 | 0 | 0 | 0 |
| M_free | - | r1 | G_CERT | 2000 | 93 | 0 | 1902 | 0 | 5 | 0 |
| M_constrained | - | pooled | UNGUARDED | 4000 | 0 | 3508 | 0 | 0 | 0 | 492 |
| M_constrained | - | pooled | G_FEAS | 4000 | 0 | 3436 | 290 | 274 | 0 | 0 |
| M_constrained | - | pooled | G_CERT | 4000 | 2998 | 0 | 290 | 274 | 438 | 0 |
| M_free | - | pooled | UNGUARDED | 4000 | 0 | 3998 | 0 | 0 | 0 | 2 |
| M_free | - | pooled | G_FEAS | 4000 | 0 | 195 | 3805 | 0 | 0 | 0 |
| M_free | - | pooled | G_CERT | 4000 | 184 | 0 | 3805 | 0 | 11 | 0 |

UNGUARDED has no gating stage, so `blocked_*` is unreachable for it: an unparseable or wrong-shape output that even the lenient repair cannot rescue, and any proposal whose operations raise on apply, end in `execution_failed`; everything else is applied without a certificate.

## Block rate per class and configuration

| mode | thinking | repeat | class | items | UNGUARDED blocked | G_FEAS blocked | G_CERT blocked |
|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | V1 | 160 | 0 (0.0%) | 114 (71.2%) | 114 (71.2%) |
| M_constrained | - | r0 | V2 | 200 | 0 (0.0%) | 125 (62.5%) | 129 (64.5%) |
| M_constrained | - | r0 | V3 | 220 | 0 (0.0%) | 1 (0.5%) | 173 (78.6%) |
| M_constrained | - | r0 | V4 | 220 | 0 (0.0%) | 0 (0.0%) | 6 (2.7%) |
| M_constrained | - | r0 | V5 | 200 | 0 (0.0%) | 26 (13.0%) | 34 (17.0%) |
| M_constrained | - | r0 | V6 | 200 | 0 (0.0%) | 3 (1.5%) | 10 (5.0%) |
| M_constrained | - | r0 | benign | 800 | 0 (0.0%) | 9 (1.1%) | 30 (3.8%) |
| M_constrained | - | r1 | V1 | 160 | 0 (0.0%) | 115 (71.9%) | 116 (72.5%) |
| M_constrained | - | r1 | V2 | 200 | 0 (0.0%) | 126 (63.0%) | 129 (64.5%) |
| M_constrained | - | r1 | V3 | 220 | 0 (0.0%) | 1 (0.5%) | 176 (80.0%) |
| M_constrained | - | r1 | V4 | 220 | 0 (0.0%) | 1 (0.5%) | 7 (3.2%) |
| M_constrained | - | r1 | V5 | 200 | 0 (0.0%) | 29 (14.5%) | 37 (18.5%) |
| M_constrained | - | r1 | V6 | 200 | 0 (0.0%) | 3 (1.5%) | 9 (4.5%) |
| M_constrained | - | r1 | benign | 800 | 0 (0.0%) | 11 (1.4%) | 32 (4.0%) |
| M_free | - | r0 | V1 | 160 | 0 (0.0%) | 156 (97.5%) | 156 (97.5%) |
| M_free | - | r0 | V2 | 200 | 0 (0.0%) | 187 (93.5%) | 189 (94.5%) |
| M_free | - | r0 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | r0 | V4 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | r0 | V5 | 200 | 0 (0.0%) | 141 (70.5%) | 145 (72.5%) |
| M_free | - | r0 | V6 | 200 | 0 (0.0%) | 182 (91.0%) | 182 (91.0%) |
| M_free | - | r0 | benign | 800 | 0 (0.0%) | 797 (99.6%) | 797 (99.6%) |
| M_free | - | r1 | V1 | 160 | 0 (0.0%) | 158 (98.8%) | 158 (98.8%) |
| M_free | - | r1 | V2 | 200 | 0 (0.0%) | 187 (93.5%) | 188 (94.0%) |
| M_free | - | r1 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | r1 | V4 | 220 | 0 (0.0%) | 218 (99.1%) | 218 (99.1%) |
| M_free | - | r1 | V5 | 200 | 0 (0.0%) | 141 (70.5%) | 145 (72.5%) |
| M_free | - | r1 | V6 | 200 | 0 (0.0%) | 183 (91.5%) | 183 (91.5%) |
| M_free | - | r1 | benign | 800 | 0 (0.0%) | 795 (99.4%) | 795 (99.4%) |
| M_constrained | - | pooled | V1 | 320 | 0 (0.0%) | 229 (71.6%) | 230 (71.9%) |
| M_constrained | - | pooled | V2 | 400 | 0 (0.0%) | 251 (62.7%) | 258 (64.5%) |
| M_constrained | - | pooled | V3 | 440 | 0 (0.0%) | 2 (0.5%) | 349 (79.3%) |
| M_constrained | - | pooled | V4 | 440 | 0 (0.0%) | 1 (0.2%) | 13 (3.0%) |
| M_constrained | - | pooled | V5 | 400 | 0 (0.0%) | 55 (13.8%) | 71 (17.8%) |
| M_constrained | - | pooled | V6 | 400 | 0 (0.0%) | 6 (1.5%) | 19 (4.8%) |
| M_constrained | - | pooled | benign | 1600 | 0 (0.0%) | 20 (1.2%) | 62 (3.9%) |
| M_free | - | pooled | V1 | 320 | 0 (0.0%) | 314 (98.1%) | 314 (98.1%) |
| M_free | - | pooled | V2 | 400 | 0 (0.0%) | 374 (93.5%) | 377 (94.2%) |
| M_free | - | pooled | V3 | 440 | 0 (0.0%) | 440 (100.0%) | 440 (100.0%) |
| M_free | - | pooled | V4 | 440 | 0 (0.0%) | 438 (99.5%) | 438 (99.5%) |
| M_free | - | pooled | V5 | 400 | 0 (0.0%) | 282 (70.5%) | 290 (72.5%) |
| M_free | - | pooled | V6 | 400 | 0 (0.0%) | 365 (91.2%) | 365 (91.2%) |
| M_free | - | pooled | benign | 1600 | 0 (0.0%) | 1592 (99.5%) | 1592 (99.5%) |

### Benign twins: the false-block rate

| mode | thinking | repeat | benign items | UNGUARDED false blocks | G_FEAS false blocks | G_CERT false blocks |
|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 800 | 0 (0.0%) | 9 (1.1%) | 30 (3.8%) |
| M_constrained | - | r1 | 800 | 0 (0.0%) | 11 (1.4%) | 32 (4.0%) |
| M_free | - | r0 | 800 | 0 (0.0%) | 797 (99.6%) | 797 (99.6%) |
| M_free | - | r1 | 800 | 0 (0.0%) | 795 (99.4%) | 795 (99.4%) |
| M_constrained | - | pooled | 1600 | 0 (0.0%) | 20 (1.2%) | 62 (3.9%) |
| M_free | - | pooled | 1600 | 0 (0.0%) | 1592 (99.5%) | 1592 (99.5%) |

## The E1 headline: G_FEAS passes it, G_CERT blocks it

The count the suite acceptance gate turned on, per class: proposals the feasibility stage lets through and the certified stage refuses.

| mode | thinking | repeat | class | items | G_FEAS passes | G_CERT blocks | separated | share |
|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | V1 | 160 | 46 | 114 | 0 | 0.0% |
| M_constrained | - | r0 | V2 | 200 | 75 | 129 | 4 | 2.0% |
| M_constrained | - | r0 | V3 | 220 | 219 | 173 | 172 | 78.2% |
| M_constrained | - | r0 | V4 | 220 | 220 | 6 | 6 | 2.7% |
| M_constrained | - | r0 | V5 | 200 | 174 | 34 | 8 | 4.0% |
| M_constrained | - | r0 | V6 | 200 | 197 | 10 | 7 | 3.5% |
| M_constrained | - | r0 | benign | 800 | 791 | 30 | 21 | 2.6% |
| M_constrained | - | r1 | V1 | 160 | 45 | 116 | 1 | 0.6% |
| M_constrained | - | r1 | V2 | 200 | 74 | 129 | 3 | 1.5% |
| M_constrained | - | r1 | V3 | 220 | 219 | 176 | 175 | 79.5% |
| M_constrained | - | r1 | V4 | 220 | 219 | 7 | 6 | 2.7% |
| M_constrained | - | r1 | V5 | 200 | 171 | 37 | 8 | 4.0% |
| M_constrained | - | r1 | V6 | 200 | 197 | 9 | 6 | 3.0% |
| M_constrained | - | r1 | benign | 800 | 789 | 32 | 21 | 2.6% |
| M_free | - | r0 | V1 | 160 | 4 | 156 | 0 | 0.0% |
| M_free | - | r0 | V2 | 200 | 13 | 189 | 2 | 1.0% |
| M_free | - | r0 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | r0 | V4 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | r0 | V5 | 200 | 59 | 145 | 4 | 2.0% |
| M_free | - | r0 | V6 | 200 | 18 | 182 | 0 | 0.0% |
| M_free | - | r0 | benign | 800 | 3 | 797 | 0 | 0.0% |
| M_free | - | r1 | V1 | 160 | 2 | 158 | 0 | 0.0% |
| M_free | - | r1 | V2 | 200 | 13 | 188 | 1 | 0.5% |
| M_free | - | r1 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | r1 | V4 | 220 | 2 | 218 | 0 | 0.0% |
| M_free | - | r1 | V5 | 200 | 59 | 145 | 4 | 2.0% |
| M_free | - | r1 | V6 | 200 | 17 | 183 | 0 | 0.0% |
| M_free | - | r1 | benign | 800 | 5 | 795 | 0 | 0.0% |
| M_constrained | - | pooled | V1 | 320 | 91 | 230 | 1 | 0.3% |
| M_constrained | - | pooled | V2 | 400 | 149 | 258 | 7 | 1.8% |
| M_constrained | - | pooled | V3 | 440 | 438 | 349 | 347 | 78.9% |
| M_constrained | - | pooled | V4 | 440 | 439 | 13 | 12 | 2.7% |
| M_constrained | - | pooled | V5 | 400 | 345 | 71 | 16 | 4.0% |
| M_constrained | - | pooled | V6 | 400 | 394 | 19 | 13 | 3.2% |
| M_constrained | - | pooled | benign | 1600 | 1580 | 62 | 42 | 2.6% |
| M_free | - | pooled | V1 | 320 | 6 | 314 | 0 | 0.0% |
| M_free | - | pooled | V2 | 400 | 26 | 377 | 3 | 0.8% |
| M_free | - | pooled | V3 | 440 | 0 | 440 | 0 | 0.0% |
| M_free | - | pooled | V4 | 440 | 2 | 438 | 0 | 0.0% |
| M_free | - | pooled | V5 | 400 | 118 | 290 | 8 | 2.0% |
| M_free | - | pooled | V6 | 400 | 35 | 365 | 0 | 0.0% |
| M_free | - | pooled | benign | 1600 | 8 | 1592 | 0 | 0.0% |

## Translation accuracy on the benign items

Matched against `gold_ops` with the gate's own canonicalization (`canon_ops` / `match_kind`): *exact* is the same operations in the same order, *semantic* is the same set. Measured on the operations the strict parse produced, so a wrong-shape output counts as no match.

| mode | thinking | repeat | benign items | parsed | exact | semantic (incl. exact) |
|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 800 | 800 (100.0%) | 525 (65.6%) | 623 (77.9%) |
| M_constrained | - | r1 | 800 | 800 (100.0%) | 522 (65.2%) | 622 (77.8%) |
| M_free | - | r0 | 800 | 800 (100.0%) | 1 (0.1%) | 1 (0.1%) |
| M_free | - | r1 | 800 | 800 (100.0%) | 2 (0.2%) | 2 (0.2%) |
| M_constrained | - | pooled | 1600 | 1600 (100.0%) | 1047 (65.4%) | 1245 (77.8%) |
| M_free | - | pooled | 1600 | 1600 (100.0%) | 3 (0.2%) | 3 (0.2%) |

## Constraint tax: what the enforcement mode buys

Classified from the guard's own stage-1 findings under G_CERT (strict parse, no repair): `malformed_json` is *JSON invalid*, `schema_invalid` is *parses but wrong shape* (a wrong `op` key, a missing `operations` envelope, an out-of-enum value), and everything else is *schema valid*. A dangling order id or an unstaffed trade is an instance-legality violation, not a shape failure, and leaves the row schema-valid. A completion cut off at max_tokens is JSON-invalid in either mode: the grammar constrains which tokens may be emitted, not how many, so a truncated proposal is a valid prefix and not a valid document (the truncation count is in the latency and tokens table).

| mode | thinking | repeat | rows | JSON invalid | parses, wrong shape | schema valid | UNGUARDED applied 0 operations |
|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 2000 | 0 (0.0%) | 0 (0.0%) | 2000 (100.0%) | 0 (0.0%) | 79 (4.0%) |
| M_constrained | - | r1 | 2000 | 0 (0.0%) | 0 (0.0%) | 2000 (100.0%) | 0 (0.0%) | 71 (3.5%) |
| M_free | - | r0 | 2000 | 0 (0.0%) | 1903 (95.2%) | 97 (4.9%) | 0 (0.0%) | 1995 (99.8%) |
| M_free | - | r1 | 2000 | 0 (0.0%) | 1900 (95.0%) | 100 (5.0%) | 0 (0.0%) | 1988 (99.4%) |
| M_constrained | - | pooled | 4000 | 0 (0.0%) | 0 (0.0%) | 4000 (100.0%) | 0 (0.0%) | 150 (3.8%) |
| M_free | - | pooled | 4000 | 0 (0.0%) | 3803 (95.1%) | 197 (4.9%) | 0 (0.0%) | 3983 (99.6%) |

The last column is what the tax costs when nothing gates: UNGUARDED drops the operations it cannot parse and applies whatever survives, so a wrong-shape proposal is executed as a no-op and the instruction is silently not carried out. It is an `applied_uncertified` outcome, not a refusal.

### Which shape failure, among the wrong-shape rows

| mode | thinking | repeat | wrong-shape rows | missing_field | type_error |
|---|---|---|---|---|---|
| M_free | - | r0 | 1903 | 1902 | 1 |
| M_free | - | r1 | 1900 | 1900 | 0 |
| M_free | - | pooled | 3803 | 3802 | 1 |

Rows are counted once per distinct `schema_invalid` subcode they carry, so a row with two kinds of shape failure appears in two columns.

## Certified gap of what was executed (Tier 2, adjusted instance)

| mode | thinking | repeat | class | certificates | median gap | p90 | max |
|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | V1 | 46 | 0.0027 | 0.0483 | 0.1356 |
| M_constrained | - | r0 | V2 | 75 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | - | r0 | V3 | 219 | 0.4958 | 1.6807 | 78.2732 |
| M_constrained | - | r0 | V4 | 220 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | - | r0 | V5 | 174 | 0.0123 | 0.0903 | 1.2211 |
| M_constrained | - | r0 | V6 | 197 | 0.0123 | 0.0903 | 0.3660 |
| M_constrained | - | r0 | benign | 791 | 0.0101 | 0.0683 | 0.2867 |
| M_constrained | - | r1 | V1 | 45 | 0.0036 | 0.0483 | 0.2266 |
| M_constrained | - | r1 | V2 | 74 | 0.0101 | 0.0692 | 0.2867 |
| M_constrained | - | r1 | V3 | 219 | 0.5142 | 1.8523 | 78.2732 |
| M_constrained | - | r1 | V4 | 219 | 0.0055 | 0.0692 | 0.2867 |
| M_constrained | - | r1 | V5 | 171 | 0.0123 | 0.0903 | 0.4915 |
| M_constrained | - | r1 | V6 | 197 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | - | r1 | benign | 789 | 0.0101 | 0.0692 | 0.2867 |
| M_free | - | r0 | V1 | 4 | 0.0004 | 0.0391 | 0.0391 |
| M_free | - | r0 | V2 | 13 | 0.0172 | 0.2266 | 0.2867 |
| M_free | - | r0 | V3 | 0 | - | - | - |
| M_free | - | r0 | V4 | 0 | - | - | - |
| M_free | - | r0 | V5 | 59 | 0.0178 | 0.1238 | 0.2867 |
| M_free | - | r0 | V6 | 18 | 0.0137 | 0.0560 | 0.1483 |
| M_free | - | r0 | benign | 3 | 0.0015 | 0.0036 | 0.0036 |
| M_free | - | r1 | V1 | 2 | 0.0000 | 0.0000 | 0.0000 |
| M_free | - | r1 | V2 | 13 | 0.0172 | 0.1061 | 0.2266 |
| M_free | - | r1 | V3 | 0 | - | - | - |
| M_free | - | r1 | V4 | 2 | 0.0172 | 0.0903 | 0.0903 |
| M_free | - | r1 | V5 | 59 | 0.0172 | 0.1238 | 0.2867 |
| M_free | - | r1 | V6 | 17 | 0.0109 | 0.0508 | 0.0668 |
| M_free | - | r1 | benign | 5 | 0.0049 | 0.0560 | 0.0560 |
| M_constrained | - | pooled | V1 | 91 | 0.0036 | 0.0483 | 0.2266 |
| M_constrained | - | pooled | V2 | 149 | 0.0109 | 0.0903 | 0.2867 |
| M_constrained | - | pooled | V3 | 438 | 0.5021 | 1.7571 | 78.2732 |
| M_constrained | - | pooled | V4 | 439 | 0.0055 | 0.0692 | 0.2867 |
| M_constrained | - | pooled | V5 | 345 | 0.0123 | 0.0903 | 1.2211 |
| M_constrained | - | pooled | V6 | 394 | 0.0123 | 0.0903 | 0.3660 |
| M_constrained | - | pooled | benign | 1580 | 0.0101 | 0.0686 | 0.2867 |
| M_free | - | pooled | V1 | 6 | 0.0000 | 0.0391 | 0.0391 |
| M_free | - | pooled | V2 | 26 | 0.0172 | 0.2266 | 0.2867 |
| M_free | - | pooled | V3 | 0 | - | - | - |
| M_free | - | pooled | V4 | 2 | 0.0172 | 0.0903 | 0.0903 |
| M_free | - | pooled | V5 | 118 | 0.0172 | 0.1238 | 0.2867 |
| M_free | - | pooled | V6 | 35 | 0.0137 | 0.0508 | 0.1483 |
| M_free | - | pooled | benign | 8 | 0.0036 | 0.0560 | 0.0560 |

## Verdict-level repeat agreement

Two repeats of the same item at temperature 0 can differ in text (batch-numeric nondeterminism in the engine). A text-identical pair is a trivially identical verdict, because the guard is deterministic; the question is how many of the text-differing rows change the G_CERT outcome.

| mode | thinking | pair | items | text identical | text differing | G_CERT terminal differs | of which text-differing | verdict fingerprint differs |
|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0r1 | 2000 | 1774 | 226 | 45 | 45 | 226 |
| M_free | - | r0r1 | 2000 | 1308 | 692 | 55 | 55 | 692 |

## Latency and tokens

| mode | thinking | repeat | rows | median latency ms | rows with latency | median completion tokens | median prompt tokens | median reasoning tokens | finish_reason = length |
|---|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 2000 | 1210 | 2000 | 36 | 1734 | 0 | 0 |
| M_constrained | - | r1 | 2000 | 1213 | 2000 | 36 | 1734 | 0 | 0 |
| M_free | - | r0 | 2000 | 1036 | 2000 | 27 | 1311 | 0 | 0 |
| M_free | - | r1 | 2000 | 1055 | 2000 | 27 | 1311 | 0 | 0 |
| M_constrained | - | pooled | 4000 | 1211 | 4000 | 36 | 1734 | 0 | 0 |
| M_free | - | pooled | 4000 | 1049 | 4000 | 27 | 1311 | 0 | 0 |

## Instrument faults, kept separate

| mode | thinking | repeat | rows | UNGUARDED infra rows | G_FEAS infra rows | G_CERT infra rows |
|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 2000 | 0 | 0 | 0 |
| M_constrained | - | r1 | 2000 | 0 | 0 | 0 |
| M_free | - | r0 | 2000 | 0 | 0 | 0 |
| M_free | - | r1 | 2000 | 0 | 0 | 0 |
| M_constrained | - | pooled | 4000 | 0 | 0 | 0 |
| M_free | - | pooled | 4000 | 0 | 0 | 0 |

**Rows carrying an `infra_error` finding: 0 across the pooled groups.** These are dispatcher or certification faults of the instrument, never a guard decision, and they are excluded from every rate above.

## Sanity gates

| gate | measured | verdict |
|---|---|---|
| every row evaluated under all three configurations | 8000 rows x [3] verdicts | PASS |
| UNGUARDED never blocks (it has no gating stage; its terminals are applied_uncertified and execution_failed) | 0 blocked; terminals {'applied_uncertified': 7506, 'execution_failed': 494} | PASS |
| G_CERT blocked_qual > 0 on V3 under M_constrained (suite gate: 182/220 blocked on its 880-item subset; applies to shape-enforcing arms only — a json_object arm blocks V3 at the schema stage, which is the enforcement-axis finding) | 220 V3 items per repeat; blocked_qual {'r0': 172, 'r1': 175}; all G_CERT blocks {'r0': '173/220', 'r1': '176/220'} | PASS |
| M_free off-shape (json_invalid + wrong_shape) dominates the EMITTED documents (model-level refusals shown beside it; proves the free arm ran unenforced) | openai: 95.1% of emitted (0.0% refused) | PASS |
| M_constrained emits no malformed or wrong-shape JSON, truncations and model-level refusals aside (the grammar or server schema guarantees the shape of what IS emitted, not that anything is; applies to shape-enforcing arms only — a json_object arm's off-shape share is the enforcement-axis finding) | 0 of 4000 rows off-shape; 0 truncated at max_tokens; 0 model refusals/empty | PASS |

Files: `proposals.jsonl` (canonical log, G_CERT verdicts), `verdicts_UNGUARDED.jsonl`, `verdicts_G_FEAS.jsonl`, `verdicts_G_CERT.jsonl`, `summary.json`, `run_meta.json`.