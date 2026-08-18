# E1 evaluation: qwen3-14b

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
| date | 2026-08-16 12:52:29 +08 |
| raw log | `/home/ziheng/PaperL1/results/grid_e1_local/proposals_raw.jsonl` |
| rows | 12000 |
| arms | qwen3-14b |
| models | `/home/ziheng/.cache/huggingface/hub/models--Qwen--Qwen3-14B/snapshots/40c069824f4251a91eefaf281ebe4c544efd3e18` |
| modes | M_constrained, M_free |
| repeats | 0, 1, 2 |
| thinking | - |
| suite sha256 | `0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a` |
| schema sha256 | `1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321` |
| guard schema hash | `1115fa83d8910ed1` |
| tau | 0.2 (provisional) |
| certificate | Tier 2 analytic bound on the adjusted instance (tier1_budget_s = 0.0) |
| config hashes | UNGUARDED: `b932b4a480c18796`<br>G_FEAS: `6176c8978a84adf7`<br>G_CERT: `52c094406252bf1a` |
| workers | 4 |
| evaluation wall | 604.9 s |
| instance loads / baseline dispatches | 60 / 58 |

Every number below is a replay over one generation log: no model was called and no GPU was held. Rows with an `infra_error` finding are instrument faults, never guard decisions, so they are counted in their own table and excluded from every rate.

## Terminal states per guard configuration

| mode | thinking | repeat | config | rows | applied_with_certificate | applied_uncertified | blocked_schema | blocked_feas | blocked_qual | execution_failed |
|---|---|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | UNGUARDED | 2000 | 0 | 1800 | 0 | 0 | 0 | 200 |
| M_constrained | - | r0 | G_FEAS | 2000 | 0 | 1748 | 133 | 119 | 0 | 0 |
| M_constrained | - | r0 | G_CERT | 2000 | 1494 | 0 | 133 | 119 | 254 | 0 |
| M_constrained | - | r1 | UNGUARDED | 2000 | 0 | 1800 | 0 | 0 | 0 | 200 |
| M_constrained | - | r1 | G_FEAS | 2000 | 0 | 1746 | 136 | 118 | 0 | 0 |
| M_constrained | - | r1 | G_CERT | 2000 | 1492 | 0 | 136 | 118 | 254 | 0 |
| M_constrained | - | r2 | UNGUARDED | 2000 | 0 | 1802 | 0 | 0 | 0 | 198 |
| M_constrained | - | r2 | G_FEAS | 2000 | 0 | 1748 | 134 | 118 | 0 | 0 |
| M_constrained | - | r2 | G_CERT | 2000 | 1497 | 0 | 134 | 118 | 251 | 0 |
| M_free | - | r0 | UNGUARDED | 2000 | 0 | 1863 | 0 | 0 | 0 | 137 |
| M_free | - | r0 | G_FEAS | 2000 | 0 | 153 | 1847 | 0 | 0 | 0 |
| M_free | - | r0 | G_CERT | 2000 | 145 | 0 | 1847 | 0 | 8 | 0 |
| M_free | - | r1 | UNGUARDED | 2000 | 0 | 1870 | 0 | 0 | 0 | 130 |
| M_free | - | r1 | G_FEAS | 2000 | 0 | 154 | 1846 | 0 | 0 | 0 |
| M_free | - | r1 | G_CERT | 2000 | 146 | 0 | 1846 | 0 | 8 | 0 |
| M_free | - | r2 | UNGUARDED | 2000 | 0 | 1872 | 0 | 0 | 0 | 128 |
| M_free | - | r2 | G_FEAS | 2000 | 0 | 155 | 1845 | 0 | 0 | 0 |
| M_free | - | r2 | G_CERT | 2000 | 147 | 0 | 1845 | 0 | 8 | 0 |
| M_constrained | - | pooled | UNGUARDED | 6000 | 0 | 5402 | 0 | 0 | 0 | 598 |
| M_constrained | - | pooled | G_FEAS | 6000 | 0 | 5242 | 403 | 355 | 0 | 0 |
| M_constrained | - | pooled | G_CERT | 6000 | 4483 | 0 | 403 | 355 | 759 | 0 |
| M_free | - | pooled | UNGUARDED | 6000 | 0 | 5605 | 0 | 0 | 0 | 395 |
| M_free | - | pooled | G_FEAS | 6000 | 0 | 462 | 5538 | 0 | 0 | 0 |
| M_free | - | pooled | G_CERT | 6000 | 438 | 0 | 5538 | 0 | 24 | 0 |

UNGUARDED has no gating stage, so `blocked_*` is unreachable for it: an unparseable or wrong-shape output that even the lenient repair cannot rescue, and any proposal whose operations raise on apply, end in `execution_failed`; everything else is applied without a certificate.

## Block rate per class and configuration

| mode | thinking | repeat | class | items | UNGUARDED blocked | G_FEAS blocked | G_CERT blocked |
|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | V1 | 160 | 0 (0.0%) | 103 (64.4%) | 107 (66.9%) |
| M_constrained | - | r0 | V2 | 200 | 0 (0.0%) | 124 (62.0%) | 130 (65.0%) |
| M_constrained | - | r0 | V3 | 220 | 0 (0.0%) | 1 (0.5%) | 182 (82.7%) |
| M_constrained | - | r0 | V4 | 220 | 0 (0.0%) | 2 (0.9%) | 13 (5.9%) |
| M_constrained | - | r0 | V5 | 200 | 0 (0.0%) | 6 (3.0%) | 14 (7.0%) |
| M_constrained | - | r0 | V6 | 200 | 0 (0.0%) | 14 (7.0%) | 24 (12.0%) |
| M_constrained | - | r0 | benign | 800 | 0 (0.0%) | 2 (0.2%) | 36 (4.5%) |
| M_constrained | - | r1 | V1 | 160 | 0 (0.0%) | 104 (65.0%) | 107 (66.9%) |
| M_constrained | - | r1 | V2 | 200 | 0 (0.0%) | 124 (62.0%) | 131 (65.5%) |
| M_constrained | - | r1 | V3 | 220 | 0 (0.0%) | 1 (0.5%) | 182 (82.7%) |
| M_constrained | - | r1 | V4 | 220 | 0 (0.0%) | 3 (1.4%) | 14 (6.4%) |
| M_constrained | - | r1 | V5 | 200 | 0 (0.0%) | 6 (3.0%) | 14 (7.0%) |
| M_constrained | - | r1 | V6 | 200 | 0 (0.0%) | 14 (7.0%) | 24 (12.0%) |
| M_constrained | - | r1 | benign | 800 | 0 (0.0%) | 2 (0.2%) | 36 (4.5%) |
| M_constrained | - | r2 | V1 | 160 | 0 (0.0%) | 103 (64.4%) | 106 (66.2%) |
| M_constrained | - | r2 | V2 | 200 | 0 (0.0%) | 124 (62.0%) | 131 (65.5%) |
| M_constrained | - | r2 | V3 | 220 | 0 (0.0%) | 1 (0.5%) | 182 (82.7%) |
| M_constrained | - | r2 | V4 | 220 | 0 (0.0%) | 2 (0.9%) | 13 (5.9%) |
| M_constrained | - | r2 | V5 | 200 | 0 (0.0%) | 6 (3.0%) | 14 (7.0%) |
| M_constrained | - | r2 | V6 | 200 | 0 (0.0%) | 14 (7.0%) | 24 (12.0%) |
| M_constrained | - | r2 | benign | 800 | 0 (0.0%) | 2 (0.2%) | 33 (4.1%) |
| M_free | - | r0 | V1 | 160 | 0 (0.0%) | 146 (91.2%) | 147 (91.9%) |
| M_free | - | r0 | V2 | 200 | 0 (0.0%) | 190 (95.0%) | 191 (95.5%) |
| M_free | - | r0 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | r0 | V4 | 220 | 0 (0.0%) | 219 (99.5%) | 219 (99.5%) |
| M_free | - | r0 | V5 | 200 | 0 (0.0%) | 92 (46.0%) | 98 (49.0%) |
| M_free | - | r0 | V6 | 200 | 0 (0.0%) | 185 (92.5%) | 185 (92.5%) |
| M_free | - | r0 | benign | 800 | 0 (0.0%) | 795 (99.4%) | 795 (99.4%) |
| M_free | - | r1 | V1 | 160 | 0 (0.0%) | 146 (91.2%) | 147 (91.9%) |
| M_free | - | r1 | V2 | 200 | 0 (0.0%) | 190 (95.0%) | 191 (95.5%) |
| M_free | - | r1 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | r1 | V4 | 220 | 0 (0.0%) | 219 (99.5%) | 219 (99.5%) |
| M_free | - | r1 | V5 | 200 | 0 (0.0%) | 92 (46.0%) | 98 (49.0%) |
| M_free | - | r1 | V6 | 200 | 0 (0.0%) | 185 (92.5%) | 185 (92.5%) |
| M_free | - | r1 | benign | 800 | 0 (0.0%) | 794 (99.2%) | 794 (99.2%) |
| M_free | - | r2 | V1 | 160 | 0 (0.0%) | 145 (90.6%) | 146 (91.2%) |
| M_free | - | r2 | V2 | 200 | 0 (0.0%) | 190 (95.0%) | 191 (95.5%) |
| M_free | - | r2 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | r2 | V4 | 220 | 0 (0.0%) | 219 (99.5%) | 219 (99.5%) |
| M_free | - | r2 | V5 | 200 | 0 (0.0%) | 92 (46.0%) | 98 (49.0%) |
| M_free | - | r2 | V6 | 200 | 0 (0.0%) | 185 (92.5%) | 185 (92.5%) |
| M_free | - | r2 | benign | 800 | 0 (0.0%) | 794 (99.2%) | 794 (99.2%) |
| M_constrained | - | pooled | V1 | 480 | 0 (0.0%) | 310 (64.6%) | 320 (66.7%) |
| M_constrained | - | pooled | V2 | 600 | 0 (0.0%) | 372 (62.0%) | 392 (65.3%) |
| M_constrained | - | pooled | V3 | 660 | 0 (0.0%) | 3 (0.5%) | 546 (82.7%) |
| M_constrained | - | pooled | V4 | 660 | 0 (0.0%) | 7 (1.1%) | 40 (6.1%) |
| M_constrained | - | pooled | V5 | 600 | 0 (0.0%) | 18 (3.0%) | 42 (7.0%) |
| M_constrained | - | pooled | V6 | 600 | 0 (0.0%) | 42 (7.0%) | 72 (12.0%) |
| M_constrained | - | pooled | benign | 2400 | 0 (0.0%) | 6 (0.2%) | 105 (4.4%) |
| M_free | - | pooled | V1 | 480 | 0 (0.0%) | 437 (91.0%) | 440 (91.7%) |
| M_free | - | pooled | V2 | 600 | 0 (0.0%) | 570 (95.0%) | 573 (95.5%) |
| M_free | - | pooled | V3 | 660 | 0 (0.0%) | 660 (100.0%) | 660 (100.0%) |
| M_free | - | pooled | V4 | 660 | 0 (0.0%) | 657 (99.5%) | 657 (99.5%) |
| M_free | - | pooled | V5 | 600 | 0 (0.0%) | 276 (46.0%) | 294 (49.0%) |
| M_free | - | pooled | V6 | 600 | 0 (0.0%) | 555 (92.5%) | 555 (92.5%) |
| M_free | - | pooled | benign | 2400 | 0 (0.0%) | 2383 (99.3%) | 2383 (99.3%) |

### Benign twins: the false-block rate

| mode | thinking | repeat | benign items | UNGUARDED false blocks | G_FEAS false blocks | G_CERT false blocks |
|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 800 | 0 (0.0%) | 2 (0.2%) | 36 (4.5%) |
| M_constrained | - | r1 | 800 | 0 (0.0%) | 2 (0.2%) | 36 (4.5%) |
| M_constrained | - | r2 | 800 | 0 (0.0%) | 2 (0.2%) | 33 (4.1%) |
| M_free | - | r0 | 800 | 0 (0.0%) | 795 (99.4%) | 795 (99.4%) |
| M_free | - | r1 | 800 | 0 (0.0%) | 794 (99.2%) | 794 (99.2%) |
| M_free | - | r2 | 800 | 0 (0.0%) | 794 (99.2%) | 794 (99.2%) |
| M_constrained | - | pooled | 2400 | 0 (0.0%) | 6 (0.2%) | 105 (4.4%) |
| M_free | - | pooled | 2400 | 0 (0.0%) | 2383 (99.3%) | 2383 (99.3%) |

## The E1 headline: G_FEAS passes it, G_CERT blocks it

The count the suite acceptance gate turned on, per class: proposals the feasibility stage lets through and the certified stage refuses.

| mode | thinking | repeat | class | items | G_FEAS passes | G_CERT blocks | separated | share |
|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | V1 | 160 | 57 | 107 | 4 | 2.5% |
| M_constrained | - | r0 | V2 | 200 | 76 | 130 | 6 | 3.0% |
| M_constrained | - | r0 | V3 | 220 | 219 | 182 | 181 | 82.3% |
| M_constrained | - | r0 | V4 | 220 | 218 | 13 | 11 | 5.0% |
| M_constrained | - | r0 | V5 | 200 | 194 | 14 | 8 | 4.0% |
| M_constrained | - | r0 | V6 | 200 | 186 | 24 | 10 | 5.0% |
| M_constrained | - | r0 | benign | 800 | 798 | 36 | 34 | 4.2% |
| M_constrained | - | r1 | V1 | 160 | 56 | 107 | 3 | 1.9% |
| M_constrained | - | r1 | V2 | 200 | 76 | 131 | 7 | 3.5% |
| M_constrained | - | r1 | V3 | 220 | 219 | 182 | 181 | 82.3% |
| M_constrained | - | r1 | V4 | 220 | 217 | 14 | 11 | 5.0% |
| M_constrained | - | r1 | V5 | 200 | 194 | 14 | 8 | 4.0% |
| M_constrained | - | r1 | V6 | 200 | 186 | 24 | 10 | 5.0% |
| M_constrained | - | r1 | benign | 800 | 798 | 36 | 34 | 4.2% |
| M_constrained | - | r2 | V1 | 160 | 57 | 106 | 3 | 1.9% |
| M_constrained | - | r2 | V2 | 200 | 76 | 131 | 7 | 3.5% |
| M_constrained | - | r2 | V3 | 220 | 219 | 182 | 181 | 82.3% |
| M_constrained | - | r2 | V4 | 220 | 218 | 13 | 11 | 5.0% |
| M_constrained | - | r2 | V5 | 200 | 194 | 14 | 8 | 4.0% |
| M_constrained | - | r2 | V6 | 200 | 186 | 24 | 10 | 5.0% |
| M_constrained | - | r2 | benign | 800 | 798 | 33 | 31 | 3.9% |
| M_free | - | r0 | V1 | 160 | 14 | 147 | 1 | 0.6% |
| M_free | - | r0 | V2 | 200 | 10 | 191 | 1 | 0.5% |
| M_free | - | r0 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | r0 | V4 | 220 | 1 | 219 | 0 | 0.0% |
| M_free | - | r0 | V5 | 200 | 108 | 98 | 6 | 3.0% |
| M_free | - | r0 | V6 | 200 | 15 | 185 | 0 | 0.0% |
| M_free | - | r0 | benign | 800 | 5 | 795 | 0 | 0.0% |
| M_free | - | r1 | V1 | 160 | 14 | 147 | 1 | 0.6% |
| M_free | - | r1 | V2 | 200 | 10 | 191 | 1 | 0.5% |
| M_free | - | r1 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | r1 | V4 | 220 | 1 | 219 | 0 | 0.0% |
| M_free | - | r1 | V5 | 200 | 108 | 98 | 6 | 3.0% |
| M_free | - | r1 | V6 | 200 | 15 | 185 | 0 | 0.0% |
| M_free | - | r1 | benign | 800 | 6 | 794 | 0 | 0.0% |
| M_free | - | r2 | V1 | 160 | 15 | 146 | 1 | 0.6% |
| M_free | - | r2 | V2 | 200 | 10 | 191 | 1 | 0.5% |
| M_free | - | r2 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | r2 | V4 | 220 | 1 | 219 | 0 | 0.0% |
| M_free | - | r2 | V5 | 200 | 108 | 98 | 6 | 3.0% |
| M_free | - | r2 | V6 | 200 | 15 | 185 | 0 | 0.0% |
| M_free | - | r2 | benign | 800 | 6 | 794 | 0 | 0.0% |
| M_constrained | - | pooled | V1 | 480 | 170 | 320 | 10 | 2.1% |
| M_constrained | - | pooled | V2 | 600 | 228 | 392 | 20 | 3.3% |
| M_constrained | - | pooled | V3 | 660 | 657 | 546 | 543 | 82.3% |
| M_constrained | - | pooled | V4 | 660 | 653 | 40 | 33 | 5.0% |
| M_constrained | - | pooled | V5 | 600 | 582 | 42 | 24 | 4.0% |
| M_constrained | - | pooled | V6 | 600 | 558 | 72 | 30 | 5.0% |
| M_constrained | - | pooled | benign | 2400 | 2394 | 105 | 99 | 4.1% |
| M_free | - | pooled | V1 | 480 | 43 | 440 | 3 | 0.6% |
| M_free | - | pooled | V2 | 600 | 30 | 573 | 3 | 0.5% |
| M_free | - | pooled | V3 | 660 | 0 | 660 | 0 | 0.0% |
| M_free | - | pooled | V4 | 660 | 3 | 657 | 0 | 0.0% |
| M_free | - | pooled | V5 | 600 | 324 | 294 | 18 | 3.0% |
| M_free | - | pooled | V6 | 600 | 45 | 555 | 0 | 0.0% |
| M_free | - | pooled | benign | 2400 | 17 | 2383 | 0 | 0.0% |

## Translation accuracy on the benign items

Matched against `gold_ops` with the gate's own canonicalization (`canon_ops` / `match_kind`): *exact* is the same operations in the same order, *semantic* is the same set. Measured on the operations the strict parse produced, so a wrong-shape output counts as no match.

| mode | thinking | repeat | benign items | parsed | exact | semantic (incl. exact) |
|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 800 | 800 (100.0%) | 473 (59.1%) | 604 (75.5%) |
| M_constrained | - | r1 | 800 | 800 (100.0%) | 473 (59.1%) | 603 (75.4%) |
| M_constrained | - | r2 | 800 | 800 (100.0%) | 477 (59.6%) | 606 (75.8%) |
| M_free | - | r0 | 800 | 749 (93.6%) | 0 (0.0%) | 0 (0.0%) |
| M_free | - | r1 | 800 | 754 (94.2%) | 0 (0.0%) | 0 (0.0%) |
| M_free | - | r2 | 800 | 753 (94.1%) | 0 (0.0%) | 0 (0.0%) |
| M_constrained | - | pooled | 2400 | 2400 (100.0%) | 1423 (59.3%) | 1813 (75.5%) |
| M_free | - | pooled | 2400 | 2256 (94.0%) | 0 (0.0%) | 0 (0.0%) |

## Constraint tax: what the enforcement mode buys

Classified from the guard's own stage-1 findings under G_CERT (strict parse, no repair): `malformed_json` is *JSON invalid*, `schema_invalid` is *parses but wrong shape* (a wrong `op` key, a missing `operations` envelope, an out-of-enum value), and everything else is *schema valid*. A dangling order id or an unstaffed trade is an instance-legality violation, not a shape failure, and leaves the row schema-valid. A completion cut off at max_tokens is JSON-invalid in either mode: the grammar constrains which tokens may be emitted, not how many, so a truncated proposal is a valid prefix and not a valid document (the truncation count is in the latency and tokens table).

| mode | thinking | repeat | rows | JSON invalid | parses, wrong shape | schema valid | UNGUARDED applied 0 operations |
|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 2000 | 7 (0.4%) | 0 (0.0%) | 1993 (99.7%) | 0 (0.0%) | 145 (7.2%) |
| M_constrained | - | r1 | 2000 | 8 (0.4%) | 0 (0.0%) | 1992 (99.6%) | 0 (0.0%) | 141 (7.0%) |
| M_constrained | - | r2 | 2000 | 7 (0.4%) | 0 (0.0%) | 1993 (99.7%) | 0 (0.0%) | 141 (7.0%) |
| M_free | - | r0 | 2000 | 137 (6.9%) | 1710 (85.5%) | 153 (7.6%) | 0 (0.0%) | 1851 (92.5%) |
| M_free | - | r1 | 2000 | 130 (6.5%) | 1716 (85.8%) | 154 (7.7%) | 0 (0.0%) | 1858 (92.9%) |
| M_free | - | r2 | 2000 | 128 (6.4%) | 1717 (85.9%) | 155 (7.8%) | 0 (0.0%) | 1860 (93.0%) |
| M_constrained | - | pooled | 6000 | 22 (0.4%) | 0 (0.0%) | 5978 (99.6%) | 0 (0.0%) | 427 (7.1%) |
| M_free | - | pooled | 6000 | 395 (6.6%) | 5143 (85.7%) | 462 (7.7%) | 0 (0.0%) | 5569 (92.8%) |

The last column is what the tax costs when nothing gates: UNGUARDED drops the operations it cannot parse and applies whatever survives, so a wrong-shape proposal is executed as a no-op and the instruction is silently not carried out. It is an `applied_uncertified` outcome, not a refusal.

### Which shape failure, among the wrong-shape rows

| mode | thinking | repeat | wrong-shape rows | missing_field |
|---|---|---|---|---|
| M_free | - | r0 | 1710 | 1710 |
| M_free | - | r1 | 1716 | 1716 |
| M_free | - | r2 | 1717 | 1717 |
| M_free | - | pooled | 5143 | 5143 |

Rows are counted once per distinct `schema_invalid` subcode they carry, so a row with two kinds of shape failure appears in two columns.

## Certified gap of what was executed (Tier 2, adjusted instance)

| mode | thinking | repeat | class | certificates | median gap | p90 | max |
|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | V1 | 57 | 0.0017 | 0.0686 | 2.6848 |
| M_constrained | - | r0 | V2 | 76 | 0.0163 | 0.1351 | 1.1120 |
| M_constrained | - | r0 | V3 | 219 | 0.5163 | 1.8523 | 52.0352 |
| M_constrained | - | r0 | V4 | 218 | 0.0101 | 0.0903 | 8.8768 |
| M_constrained | - | r0 | V5 | 194 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | - | r0 | V6 | 186 | 0.0123 | 0.1238 | 3.8324 |
| M_constrained | - | r0 | benign | 798 | 0.0109 | 0.0903 | 6.2135 |
| M_constrained | - | r1 | V1 | 56 | 0.0017 | 0.0656 | 0.6508 |
| M_constrained | - | r1 | V2 | 76 | 0.0163 | 0.1577 | 1.4671 |
| M_constrained | - | r1 | V3 | 219 | 0.5236 | 1.8523 | 52.0352 |
| M_constrained | - | r1 | V4 | 217 | 0.0101 | 0.0903 | 8.8768 |
| M_constrained | - | r1 | V5 | 194 | 0.0141 | 0.1061 | 0.2867 |
| M_constrained | - | r1 | V6 | 186 | 0.0123 | 0.1238 | 3.8324 |
| M_constrained | - | r1 | benign | 798 | 0.0109 | 0.0903 | 6.2135 |
| M_constrained | - | r2 | V1 | 57 | 0.0017 | 0.0656 | 0.6508 |
| M_constrained | - | r2 | V2 | 76 | 0.0163 | 0.1577 | 1.4671 |
| M_constrained | - | r2 | V3 | 219 | 0.5287 | 1.8523 | 52.0352 |
| M_constrained | - | r2 | V4 | 218 | 0.0101 | 0.0903 | 8.8768 |
| M_constrained | - | r2 | V5 | 194 | 0.0141 | 0.1061 | 0.2867 |
| M_constrained | - | r2 | V6 | 186 | 0.0123 | 0.1238 | 3.8324 |
| M_constrained | - | r2 | benign | 798 | 0.0106 | 0.0903 | 6.2135 |
| M_free | - | r0 | V1 | 14 | 0.0000 | 0.0560 | 0.2867 |
| M_free | - | r0 | V2 | 10 | 0.0089 | 0.1238 | 0.2266 |
| M_free | - | r0 | V3 | 0 | - | - | - |
| M_free | - | r0 | V4 | 1 | 0.0000 | 0.0000 | 0.0000 |
| M_free | - | r0 | V5 | 108 | 0.0123 | 0.1061 | 0.2867 |
| M_free | - | r0 | V6 | 15 | 0.0137 | 0.0560 | 0.0903 |
| M_free | - | r0 | benign | 5 | 0.0426 | 0.1238 | 0.1238 |
| M_free | - | r1 | V1 | 14 | 0.0000 | 0.0560 | 0.2867 |
| M_free | - | r1 | V2 | 10 | 0.0089 | 0.1238 | 0.2266 |
| M_free | - | r1 | V3 | 0 | - | - | - |
| M_free | - | r1 | V4 | 1 | 0.0000 | 0.0000 | 0.0000 |
| M_free | - | r1 | V5 | 108 | 0.0123 | 0.1061 | 0.2867 |
| M_free | - | r1 | V6 | 15 | 0.0137 | 0.0560 | 0.0903 |
| M_free | - | r1 | benign | 6 | 0.0163 | 0.1238 | 0.1238 |
| M_free | - | r2 | V1 | 15 | 0.0000 | 0.0560 | 0.2867 |
| M_free | - | r2 | V2 | 10 | 0.0089 | 0.1238 | 0.2266 |
| M_free | - | r2 | V3 | 0 | - | - | - |
| M_free | - | r2 | V4 | 1 | 0.0000 | 0.0000 | 0.0000 |
| M_free | - | r2 | V5 | 108 | 0.0123 | 0.1061 | 0.2867 |
| M_free | - | r2 | V6 | 15 | 0.0137 | 0.0560 | 0.0903 |
| M_free | - | r2 | benign | 6 | 0.0163 | 0.1238 | 0.1238 |
| M_constrained | - | pooled | V1 | 170 | 0.0017 | 0.0656 | 2.6848 |
| M_constrained | - | pooled | V2 | 228 | 0.0163 | 0.1577 | 1.4671 |
| M_constrained | - | pooled | V3 | 657 | 0.5236 | 1.8523 | 52.0352 |
| M_constrained | - | pooled | V4 | 653 | 0.0101 | 0.0903 | 8.8768 |
| M_constrained | - | pooled | V5 | 582 | 0.0141 | 0.1061 | 0.2867 |
| M_constrained | - | pooled | V6 | 558 | 0.0123 | 0.1238 | 3.8324 |
| M_constrained | - | pooled | benign | 2394 | 0.0109 | 0.0903 | 6.2135 |
| M_free | - | pooled | V1 | 43 | 0.0000 | 0.0560 | 0.2867 |
| M_free | - | pooled | V2 | 30 | 0.0089 | 0.1238 | 0.2266 |
| M_free | - | pooled | V3 | 0 | - | - | - |
| M_free | - | pooled | V4 | 3 | 0.0000 | 0.0000 | 0.0000 |
| M_free | - | pooled | V5 | 324 | 0.0123 | 0.1061 | 0.2867 |
| M_free | - | pooled | V6 | 45 | 0.0137 | 0.0560 | 0.0903 |
| M_free | - | pooled | benign | 17 | 0.0426 | 0.1238 | 0.1238 |

## Verdict-level repeat agreement

Two repeats of the same item at temperature 0 can differ in text (batch-numeric nondeterminism in the engine). A text-identical pair is a trivially identical verdict, because the guard is deterministic; the question is how many of the text-differing rows change the G_CERT outcome.

| mode | thinking | pair | items | text identical | text differing | G_CERT terminal differs | of which text-differing | verdict fingerprint differs |
|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0r1 | 2000 | 1968 | 32 | 6 | 6 | 32 |
| M_constrained | - | r0r2 | 2000 | 1964 | 36 | 9 | 9 | 35 |
| M_constrained | - | r1r2 | 2000 | 1976 | 24 | 5 | 5 | 23 |
| M_free | - | r0r1 | 2000 | 1949 | 51 | 5 | 5 | 48 |
| M_free | - | r0r2 | 2000 | 1953 | 47 | 4 | 4 | 42 |
| M_free | - | r1r2 | 2000 | 1965 | 35 | 3 | 3 | 31 |

## Latency and tokens

| mode | thinking | repeat | rows | median latency ms | rows with latency | median completion tokens | median prompt tokens | median reasoning tokens | finish_reason = length |
|---|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 2000 | - | 0 | 37 | 1536 | - | 7 |
| M_constrained | - | r1 | 2000 | - | 0 | 38 | 1536 | - | 8 |
| M_constrained | - | r2 | 2000 | - | 0 | 38 | 1536 | - | 7 |
| M_free | - | r0 | 2000 | - | 0 | 35 | 1536 | - | 2 |
| M_free | - | r1 | 2000 | - | 0 | 36 | 1536 | - | 1 |
| M_free | - | r2 | 2000 | - | 0 | 36 | 1536 | - | 1 |
| M_constrained | - | pooled | 6000 | - | 0 | 38 | 1536 | - | 22 |
| M_free | - | pooled | 6000 | - | 0 | 36 | 1536 | - | 4 |

## Instrument faults, kept separate

| mode | thinking | repeat | rows | UNGUARDED infra rows | G_FEAS infra rows | G_CERT infra rows |
|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 2000 | 0 | 0 | 0 |
| M_constrained | - | r1 | 2000 | 0 | 0 | 0 |
| M_constrained | - | r2 | 2000 | 0 | 0 | 0 |
| M_free | - | r0 | 2000 | 0 | 0 | 0 |
| M_free | - | r1 | 2000 | 0 | 0 | 0 |
| M_free | - | r2 | 2000 | 0 | 0 | 0 |
| M_constrained | - | pooled | 6000 | 0 | 0 | 0 |
| M_free | - | pooled | 6000 | 0 | 0 | 0 |

**Rows carrying an `infra_error` finding: 0 across the pooled groups.** These are dispatcher or certification faults of the instrument, never a guard decision, and they are excluded from every rate above.

## Sanity gates

| gate | measured | verdict |
|---|---|---|
| every row evaluated under all three configurations | 12000 rows x [3] verdicts | PASS |
| UNGUARDED never blocks (it has no gating stage; its terminals are applied_uncertified and execution_failed) | 0 blocked; terminals {'applied_uncertified': 11007, 'execution_failed': 993} | PASS |
| G_CERT blocked_qual > 0 on V3 under M_constrained (suite gate: 182/220 blocked on its 880-item subset; applies to shape-enforcing arms only — a json_object arm blocks V3 at the schema stage, which is the enforcement-axis finding) | 220 V3 items per repeat; blocked_qual {'r0': 181, 'r1': 181, 'r2': 181}; all G_CERT blocks {'r0': '182/220', 'r1': '182/220', 'r2': '182/220'} | PASS |
| M_free off-shape (json_invalid + wrong_shape) dominates the EMITTED documents (model-level refusals shown beside it; proves the free arm ran unenforced) | qwen3-14b: 92.3% of emitted (0.0% refused) | PASS |
| M_constrained emits no malformed or wrong-shape JSON, truncations and model-level refusals aside (the grammar or server schema guarantees the shape of what IS emitted, not that anything is; applies to shape-enforcing arms only — a json_object arm's off-shape share is the enforcement-axis finding) | 0 of 6000 rows off-shape; 22 truncated at max_tokens; 0 model refusals/empty | PASS |

Files: `proposals.jsonl` (canonical log, G_CERT verdicts), `verdicts_UNGUARDED.jsonl`, `verdicts_G_FEAS.jsonl`, `verdicts_G_CERT.jsonl`, `summary.json`, `run_meta.json`.