# E1 evaluation: qwen3.6-27b-fp8

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
| date | 2026-08-16 13:02:55 +08 |
| raw log | `/home/ziheng/PaperL1/results/grid_e1_local_27b/proposals_raw.jsonl` |
| rows | 12000 |
| arms | qwen3.6-27b-fp8 |
| models | `/home/ziheng/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B-FP8/snapshots/e89b16ebf1988b3d6befa7de50abc2d76f26eb09/` |
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
| evaluation wall | 625.3 s |
| instance loads / baseline dispatches | 60 / 58 |

Every number below is a replay over one generation log: no model was called and no GPU was held. Rows with an `infra_error` finding are instrument faults, never guard decisions, so they are counted in their own table and excluded from every rate.

## Terminal states per guard configuration

| mode | thinking | repeat | config | rows | applied_with_certificate | applied_uncertified | blocked_schema | blocked_feas | blocked_qual | execution_failed |
|---|---|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | UNGUARDED | 2000 | 0 | 1767 | 0 | 0 | 0 | 233 |
| M_constrained | - | r0 | G_FEAS | 2000 | 0 | 1735 | 109 | 156 | 0 | 0 |
| M_constrained | - | r0 | G_CERT | 2000 | 1499 | 0 | 109 | 156 | 236 | 0 |
| M_constrained | - | r1 | UNGUARDED | 2000 | 0 | 1772 | 0 | 0 | 0 | 228 |
| M_constrained | - | r1 | G_FEAS | 2000 | 0 | 1742 | 109 | 149 | 0 | 0 |
| M_constrained | - | r1 | G_CERT | 2000 | 1507 | 0 | 109 | 149 | 235 | 0 |
| M_constrained | - | r2 | UNGUARDED | 2000 | 0 | 1772 | 0 | 0 | 0 | 228 |
| M_constrained | - | r2 | G_FEAS | 2000 | 0 | 1742 | 109 | 149 | 0 | 0 |
| M_constrained | - | r2 | G_CERT | 2000 | 1507 | 0 | 109 | 149 | 235 | 0 |
| M_free | - | r0 | UNGUARDED | 2000 | 0 | 2000 | 0 | 0 | 0 | 0 |
| M_free | - | r0 | G_FEAS | 2000 | 0 | 214 | 1786 | 0 | 0 | 0 |
| M_free | - | r0 | G_CERT | 2000 | 207 | 0 | 1786 | 0 | 7 | 0 |
| M_free | - | r1 | UNGUARDED | 2000 | 0 | 2000 | 0 | 0 | 0 | 0 |
| M_free | - | r1 | G_FEAS | 2000 | 0 | 214 | 1786 | 0 | 0 | 0 |
| M_free | - | r1 | G_CERT | 2000 | 207 | 0 | 1786 | 0 | 7 | 0 |
| M_free | - | r2 | UNGUARDED | 2000 | 0 | 2000 | 0 | 0 | 0 | 0 |
| M_free | - | r2 | G_FEAS | 2000 | 0 | 214 | 1786 | 0 | 0 | 0 |
| M_free | - | r2 | G_CERT | 2000 | 207 | 0 | 1786 | 0 | 7 | 0 |
| M_constrained | - | pooled | UNGUARDED | 6000 | 0 | 5311 | 0 | 0 | 0 | 689 |
| M_constrained | - | pooled | G_FEAS | 6000 | 0 | 5219 | 327 | 454 | 0 | 0 |
| M_constrained | - | pooled | G_CERT | 6000 | 4513 | 0 | 327 | 454 | 706 | 0 |
| M_free | - | pooled | UNGUARDED | 6000 | 0 | 6000 | 0 | 0 | 0 | 0 |
| M_free | - | pooled | G_FEAS | 6000 | 0 | 642 | 5358 | 0 | 0 | 0 |
| M_free | - | pooled | G_CERT | 6000 | 621 | 0 | 5358 | 0 | 21 | 0 |

UNGUARDED has no gating stage, so `blocked_*` is unreachable for it: an unparseable or wrong-shape output that even the lenient repair cannot rescue, and any proposal whose operations raise on apply, end in `execution_failed`; everything else is applied without a certificate.

## Block rate per class and configuration

| mode | thinking | repeat | class | items | UNGUARDED blocked | G_FEAS blocked | G_CERT blocked |
|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | V1 | 160 | 0 (0.0%) | 110 (68.8%) | 111 (69.4%) |
| M_constrained | - | r0 | V2 | 200 | 0 (0.0%) | 124 (62.0%) | 127 (63.5%) |
| M_constrained | - | r0 | V3 | 220 | 0 (0.0%) | 1 (0.5%) | 193 (87.7%) |
| M_constrained | - | r0 | V4 | 220 | 0 (0.0%) | 0 (0.0%) | 6 (2.7%) |
| M_constrained | - | r0 | V5 | 200 | 0 (0.0%) | 1 (0.5%) | 8 (4.0%) |
| M_constrained | - | r0 | V6 | 200 | 0 (0.0%) | 4 (2.0%) | 10 (5.0%) |
| M_constrained | - | r0 | benign | 800 | 0 (0.0%) | 25 (3.1%) | 46 (5.8%) |
| M_constrained | - | r1 | V1 | 160 | 0 (0.0%) | 110 (68.8%) | 111 (69.4%) |
| M_constrained | - | r1 | V2 | 200 | 0 (0.0%) | 120 (60.0%) | 123 (61.5%) |
| M_constrained | - | r1 | V3 | 220 | 0 (0.0%) | 1 (0.5%) | 192 (87.3%) |
| M_constrained | - | r1 | V4 | 220 | 0 (0.0%) | 0 (0.0%) | 6 (2.7%) |
| M_constrained | - | r1 | V5 | 200 | 0 (0.0%) | 1 (0.5%) | 8 (4.0%) |
| M_constrained | - | r1 | V6 | 200 | 0 (0.0%) | 4 (2.0%) | 10 (5.0%) |
| M_constrained | - | r1 | benign | 800 | 0 (0.0%) | 22 (2.8%) | 43 (5.4%) |
| M_constrained | - | r2 | V1 | 160 | 0 (0.0%) | 110 (68.8%) | 111 (69.4%) |
| M_constrained | - | r2 | V2 | 200 | 0 (0.0%) | 120 (60.0%) | 123 (61.5%) |
| M_constrained | - | r2 | V3 | 220 | 0 (0.0%) | 1 (0.5%) | 192 (87.3%) |
| M_constrained | - | r2 | V4 | 220 | 0 (0.0%) | 0 (0.0%) | 6 (2.7%) |
| M_constrained | - | r2 | V5 | 200 | 0 (0.0%) | 1 (0.5%) | 8 (4.0%) |
| M_constrained | - | r2 | V6 | 200 | 0 (0.0%) | 4 (2.0%) | 10 (5.0%) |
| M_constrained | - | r2 | benign | 800 | 0 (0.0%) | 22 (2.8%) | 43 (5.4%) |
| M_free | - | r0 | V1 | 160 | 0 (0.0%) | 130 (81.2%) | 131 (81.9%) |
| M_free | - | r0 | V2 | 200 | 0 (0.0%) | 165 (82.5%) | 166 (83.0%) |
| M_free | - | r0 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | r0 | V4 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | r0 | V5 | 200 | 0 (0.0%) | 70 (35.0%) | 75 (37.5%) |
| M_free | - | r0 | V6 | 200 | 0 (0.0%) | 181 (90.5%) | 181 (90.5%) |
| M_free | - | r0 | benign | 800 | 0 (0.0%) | 800 (100.0%) | 800 (100.0%) |
| M_free | - | r1 | V1 | 160 | 0 (0.0%) | 130 (81.2%) | 131 (81.9%) |
| M_free | - | r1 | V2 | 200 | 0 (0.0%) | 165 (82.5%) | 166 (83.0%) |
| M_free | - | r1 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | r1 | V4 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | r1 | V5 | 200 | 0 (0.0%) | 70 (35.0%) | 75 (37.5%) |
| M_free | - | r1 | V6 | 200 | 0 (0.0%) | 181 (90.5%) | 181 (90.5%) |
| M_free | - | r1 | benign | 800 | 0 (0.0%) | 800 (100.0%) | 800 (100.0%) |
| M_free | - | r2 | V1 | 160 | 0 (0.0%) | 130 (81.2%) | 131 (81.9%) |
| M_free | - | r2 | V2 | 200 | 0 (0.0%) | 165 (82.5%) | 166 (83.0%) |
| M_free | - | r2 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | r2 | V4 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | r2 | V5 | 200 | 0 (0.0%) | 70 (35.0%) | 75 (37.5%) |
| M_free | - | r2 | V6 | 200 | 0 (0.0%) | 181 (90.5%) | 181 (90.5%) |
| M_free | - | r2 | benign | 800 | 0 (0.0%) | 800 (100.0%) | 800 (100.0%) |
| M_constrained | - | pooled | V1 | 480 | 0 (0.0%) | 330 (68.8%) | 333 (69.4%) |
| M_constrained | - | pooled | V2 | 600 | 0 (0.0%) | 364 (60.7%) | 373 (62.2%) |
| M_constrained | - | pooled | V3 | 660 | 0 (0.0%) | 3 (0.5%) | 577 (87.4%) |
| M_constrained | - | pooled | V4 | 660 | 0 (0.0%) | 0 (0.0%) | 18 (2.7%) |
| M_constrained | - | pooled | V5 | 600 | 0 (0.0%) | 3 (0.5%) | 24 (4.0%) |
| M_constrained | - | pooled | V6 | 600 | 0 (0.0%) | 12 (2.0%) | 30 (5.0%) |
| M_constrained | - | pooled | benign | 2400 | 0 (0.0%) | 69 (2.9%) | 132 (5.5%) |
| M_free | - | pooled | V1 | 480 | 0 (0.0%) | 390 (81.2%) | 393 (81.9%) |
| M_free | - | pooled | V2 | 600 | 0 (0.0%) | 495 (82.5%) | 498 (83.0%) |
| M_free | - | pooled | V3 | 660 | 0 (0.0%) | 660 (100.0%) | 660 (100.0%) |
| M_free | - | pooled | V4 | 660 | 0 (0.0%) | 660 (100.0%) | 660 (100.0%) |
| M_free | - | pooled | V5 | 600 | 0 (0.0%) | 210 (35.0%) | 225 (37.5%) |
| M_free | - | pooled | V6 | 600 | 0 (0.0%) | 543 (90.5%) | 543 (90.5%) |
| M_free | - | pooled | benign | 2400 | 0 (0.0%) | 2400 (100.0%) | 2400 (100.0%) |

### Benign twins: the false-block rate

| mode | thinking | repeat | benign items | UNGUARDED false blocks | G_FEAS false blocks | G_CERT false blocks |
|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 800 | 0 (0.0%) | 25 (3.1%) | 46 (5.8%) |
| M_constrained | - | r1 | 800 | 0 (0.0%) | 22 (2.8%) | 43 (5.4%) |
| M_constrained | - | r2 | 800 | 0 (0.0%) | 22 (2.8%) | 43 (5.4%) |
| M_free | - | r0 | 800 | 0 (0.0%) | 800 (100.0%) | 800 (100.0%) |
| M_free | - | r1 | 800 | 0 (0.0%) | 800 (100.0%) | 800 (100.0%) |
| M_free | - | r2 | 800 | 0 (0.0%) | 800 (100.0%) | 800 (100.0%) |
| M_constrained | - | pooled | 2400 | 0 (0.0%) | 69 (2.9%) | 132 (5.5%) |
| M_free | - | pooled | 2400 | 0 (0.0%) | 2400 (100.0%) | 2400 (100.0%) |

## The E1 headline: G_FEAS passes it, G_CERT blocks it

The count the suite acceptance gate turned on, per class: proposals the feasibility stage lets through and the certified stage refuses.

| mode | thinking | repeat | class | items | G_FEAS passes | G_CERT blocks | separated | share |
|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | V1 | 160 | 50 | 111 | 1 | 0.6% |
| M_constrained | - | r0 | V2 | 200 | 76 | 127 | 3 | 1.5% |
| M_constrained | - | r0 | V3 | 220 | 219 | 193 | 192 | 87.3% |
| M_constrained | - | r0 | V4 | 220 | 220 | 6 | 6 | 2.7% |
| M_constrained | - | r0 | V5 | 200 | 199 | 8 | 7 | 3.5% |
| M_constrained | - | r0 | V6 | 200 | 196 | 10 | 6 | 3.0% |
| M_constrained | - | r0 | benign | 800 | 775 | 46 | 21 | 2.6% |
| M_constrained | - | r1 | V1 | 160 | 50 | 111 | 1 | 0.6% |
| M_constrained | - | r1 | V2 | 200 | 80 | 123 | 3 | 1.5% |
| M_constrained | - | r1 | V3 | 220 | 219 | 192 | 191 | 86.8% |
| M_constrained | - | r1 | V4 | 220 | 220 | 6 | 6 | 2.7% |
| M_constrained | - | r1 | V5 | 200 | 199 | 8 | 7 | 3.5% |
| M_constrained | - | r1 | V6 | 200 | 196 | 10 | 6 | 3.0% |
| M_constrained | - | r1 | benign | 800 | 778 | 43 | 21 | 2.6% |
| M_constrained | - | r2 | V1 | 160 | 50 | 111 | 1 | 0.6% |
| M_constrained | - | r2 | V2 | 200 | 80 | 123 | 3 | 1.5% |
| M_constrained | - | r2 | V3 | 220 | 219 | 192 | 191 | 86.8% |
| M_constrained | - | r2 | V4 | 220 | 220 | 6 | 6 | 2.7% |
| M_constrained | - | r2 | V5 | 200 | 199 | 8 | 7 | 3.5% |
| M_constrained | - | r2 | V6 | 200 | 196 | 10 | 6 | 3.0% |
| M_constrained | - | r2 | benign | 800 | 778 | 43 | 21 | 2.6% |
| M_free | - | r0 | V1 | 160 | 30 | 131 | 1 | 0.6% |
| M_free | - | r0 | V2 | 200 | 35 | 166 | 1 | 0.5% |
| M_free | - | r0 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | r0 | V4 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | r0 | V5 | 200 | 130 | 75 | 5 | 2.5% |
| M_free | - | r0 | V6 | 200 | 19 | 181 | 0 | 0.0% |
| M_free | - | r0 | benign | 800 | 0 | 800 | 0 | 0.0% |
| M_free | - | r1 | V1 | 160 | 30 | 131 | 1 | 0.6% |
| M_free | - | r1 | V2 | 200 | 35 | 166 | 1 | 0.5% |
| M_free | - | r1 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | r1 | V4 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | r1 | V5 | 200 | 130 | 75 | 5 | 2.5% |
| M_free | - | r1 | V6 | 200 | 19 | 181 | 0 | 0.0% |
| M_free | - | r1 | benign | 800 | 0 | 800 | 0 | 0.0% |
| M_free | - | r2 | V1 | 160 | 30 | 131 | 1 | 0.6% |
| M_free | - | r2 | V2 | 200 | 35 | 166 | 1 | 0.5% |
| M_free | - | r2 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | r2 | V4 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | r2 | V5 | 200 | 130 | 75 | 5 | 2.5% |
| M_free | - | r2 | V6 | 200 | 19 | 181 | 0 | 0.0% |
| M_free | - | r2 | benign | 800 | 0 | 800 | 0 | 0.0% |
| M_constrained | - | pooled | V1 | 480 | 150 | 333 | 3 | 0.6% |
| M_constrained | - | pooled | V2 | 600 | 236 | 373 | 9 | 1.5% |
| M_constrained | - | pooled | V3 | 660 | 657 | 577 | 574 | 87.0% |
| M_constrained | - | pooled | V4 | 660 | 660 | 18 | 18 | 2.7% |
| M_constrained | - | pooled | V5 | 600 | 597 | 24 | 21 | 3.5% |
| M_constrained | - | pooled | V6 | 600 | 588 | 30 | 18 | 3.0% |
| M_constrained | - | pooled | benign | 2400 | 2331 | 132 | 63 | 2.6% |
| M_free | - | pooled | V1 | 480 | 90 | 393 | 3 | 0.6% |
| M_free | - | pooled | V2 | 600 | 105 | 498 | 3 | 0.5% |
| M_free | - | pooled | V3 | 660 | 0 | 660 | 0 | 0.0% |
| M_free | - | pooled | V4 | 660 | 0 | 660 | 0 | 0.0% |
| M_free | - | pooled | V5 | 600 | 390 | 225 | 15 | 2.5% |
| M_free | - | pooled | V6 | 600 | 57 | 543 | 0 | 0.0% |
| M_free | - | pooled | benign | 2400 | 0 | 2400 | 0 | 0.0% |

## Translation accuracy on the benign items

Matched against `gold_ops` with the gate's own canonicalization (`canon_ops` / `match_kind`): *exact* is the same operations in the same order, *semantic* is the same set. Measured on the operations the strict parse produced, so a wrong-shape output counts as no match.

| mode | thinking | repeat | benign items | parsed | exact | semantic (incl. exact) |
|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 800 | 800 (100.0%) | 584 (73.0%) | 710 (88.8%) |
| M_constrained | - | r1 | 800 | 800 (100.0%) | 588 (73.5%) | 714 (89.2%) |
| M_constrained | - | r2 | 800 | 800 (100.0%) | 588 (73.5%) | 714 (89.2%) |
| M_free | - | r0 | 800 | 800 (100.0%) | 0 (0.0%) | 0 (0.0%) |
| M_free | - | r1 | 800 | 800 (100.0%) | 0 (0.0%) | 0 (0.0%) |
| M_free | - | r2 | 800 | 800 (100.0%) | 0 (0.0%) | 0 (0.0%) |
| M_constrained | - | pooled | 2400 | 2400 (100.0%) | 1760 (73.3%) | 2138 (89.1%) |
| M_free | - | pooled | 2400 | 2400 (100.0%) | 0 (0.0%) | 0 (0.0%) |

## Constraint tax: what the enforcement mode buys

Classified from the guard's own stage-1 findings under G_CERT (strict parse, no repair): `malformed_json` is *JSON invalid*, `schema_invalid` is *parses but wrong shape* (a wrong `op` key, a missing `operations` envelope, an out-of-enum value), and everything else is *schema valid*. A dangling order id or an unstaffed trade is an instance-legality violation, not a shape failure, and leaves the row schema-valid. A completion cut off at max_tokens is JSON-invalid in either mode: the grammar constrains which tokens may be emitted, not how many, so a truncated proposal is a valid prefix and not a valid document (the truncation count is in the latency and tokens table).

| mode | thinking | repeat | rows | JSON invalid | parses, wrong shape | schema valid | UNGUARDED applied 0 operations |
|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 2000 | 0 (0.0%) | 0 (0.0%) | 2000 (100.0%) | 0 (0.0%) | 210 (10.5%) |
| M_constrained | - | r1 | 2000 | 0 (0.0%) | 0 (0.0%) | 2000 (100.0%) | 0 (0.0%) | 209 (10.4%) |
| M_constrained | - | r2 | 2000 | 0 (0.0%) | 0 (0.0%) | 2000 (100.0%) | 0 (0.0%) | 209 (10.4%) |
| M_free | - | r0 | 2000 | 0 (0.0%) | 1786 (89.3%) | 214 (10.7%) | 0 (0.0%) | 1989 (99.5%) |
| M_free | - | r1 | 2000 | 0 (0.0%) | 1786 (89.3%) | 214 (10.7%) | 0 (0.0%) | 1989 (99.5%) |
| M_free | - | r2 | 2000 | 0 (0.0%) | 1786 (89.3%) | 214 (10.7%) | 0 (0.0%) | 1989 (99.5%) |
| M_constrained | - | pooled | 6000 | 0 (0.0%) | 0 (0.0%) | 6000 (100.0%) | 0 (0.0%) | 628 (10.5%) |
| M_free | - | pooled | 6000 | 0 (0.0%) | 5358 (89.3%) | 642 (10.7%) | 0 (0.0%) | 5967 (99.5%) |

The last column is what the tax costs when nothing gates: UNGUARDED drops the operations it cannot parse and applies whatever survives, so a wrong-shape proposal is executed as a no-op and the instruction is silently not carried out. It is an `applied_uncertified` outcome, not a refusal.

### Which shape failure, among the wrong-shape rows

| mode | thinking | repeat | wrong-shape rows | missing_field |
|---|---|---|---|---|
| M_free | - | r0 | 1786 | 1786 |
| M_free | - | r1 | 1786 | 1786 |
| M_free | - | r2 | 1786 | 1786 |
| M_free | - | pooled | 5358 | 5358 |

Rows are counted once per distinct `schema_invalid` subcode they carry, so a row with two kinds of shape failure appears in two columns.

## Certified gap of what was executed (Tier 2, adjusted instance)

| mode | thinking | repeat | class | certificates | median gap | p90 | max |
|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | V1 | 50 | 0.0015 | 0.0426 | 0.2867 |
| M_constrained | - | r0 | V2 | 76 | 0.0134 | 0.0903 | 0.2867 |
| M_constrained | - | r0 | V3 | 219 | 0.6030 | 2.8034 | 172.2048 |
| M_constrained | - | r0 | V4 | 220 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | - | r0 | V5 | 199 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | - | r0 | V6 | 196 | 0.0109 | 0.0903 | 0.2867 |
| M_constrained | - | r0 | benign | 775 | 0.0101 | 0.0692 | 0.2867 |
| M_constrained | - | r1 | V1 | 50 | 0.0015 | 0.0483 | 0.2867 |
| M_constrained | - | r1 | V2 | 80 | 0.0109 | 0.0692 | 0.2867 |
| M_constrained | - | r1 | V3 | 219 | 0.6030 | 2.8034 | 172.2048 |
| M_constrained | - | r1 | V4 | 220 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | - | r1 | V5 | 199 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | - | r1 | V6 | 196 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | - | r1 | benign | 778 | 0.0101 | 0.0692 | 0.2867 |
| M_constrained | - | r2 | V1 | 50 | 0.0015 | 0.0483 | 0.2867 |
| M_constrained | - | r2 | V2 | 80 | 0.0109 | 0.0692 | 0.2867 |
| M_constrained | - | r2 | V3 | 219 | 0.6030 | 2.8034 | 172.2048 |
| M_constrained | - | r2 | V4 | 220 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | - | r2 | V5 | 199 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | - | r2 | V6 | 196 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | - | r2 | benign | 778 | 0.0101 | 0.0692 | 0.2867 |
| M_free | - | r0 | V1 | 30 | 0.0017 | 0.0483 | 0.2867 |
| M_free | - | r0 | V2 | 35 | 0.0109 | 0.0656 | 0.2266 |
| M_free | - | r0 | V3 | 0 | - | - | - |
| M_free | - | r0 | V4 | 0 | - | - | - |
| M_free | - | r0 | V5 | 130 | 0.0123 | 0.0903 | 0.2867 |
| M_free | - | r0 | V6 | 19 | 0.0101 | 0.0508 | 0.0903 |
| M_free | - | r0 | benign | 0 | - | - | - |
| M_free | - | r1 | V1 | 30 | 0.0017 | 0.0483 | 0.2867 |
| M_free | - | r1 | V2 | 35 | 0.0109 | 0.0656 | 0.2266 |
| M_free | - | r1 | V3 | 0 | - | - | - |
| M_free | - | r1 | V4 | 0 | - | - | - |
| M_free | - | r1 | V5 | 130 | 0.0123 | 0.0903 | 0.2867 |
| M_free | - | r1 | V6 | 19 | 0.0101 | 0.0508 | 0.0903 |
| M_free | - | r1 | benign | 0 | - | - | - |
| M_free | - | r2 | V1 | 30 | 0.0017 | 0.0483 | 0.2867 |
| M_free | - | r2 | V2 | 35 | 0.0109 | 0.0656 | 0.2266 |
| M_free | - | r2 | V3 | 0 | - | - | - |
| M_free | - | r2 | V4 | 0 | - | - | - |
| M_free | - | r2 | V5 | 130 | 0.0123 | 0.0903 | 0.2867 |
| M_free | - | r2 | V6 | 19 | 0.0101 | 0.0508 | 0.0903 |
| M_free | - | r2 | benign | 0 | - | - | - |
| M_constrained | - | pooled | V1 | 150 | 0.0015 | 0.0483 | 0.2867 |
| M_constrained | - | pooled | V2 | 236 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | - | pooled | V3 | 657 | 0.6030 | 2.8034 | 172.2048 |
| M_constrained | - | pooled | V4 | 660 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | - | pooled | V5 | 597 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | - | pooled | V6 | 588 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | - | pooled | benign | 2331 | 0.0101 | 0.0692 | 0.2867 |
| M_free | - | pooled | V1 | 90 | 0.0017 | 0.0483 | 0.2867 |
| M_free | - | pooled | V2 | 105 | 0.0109 | 0.0656 | 0.2266 |
| M_free | - | pooled | V3 | 0 | - | - | - |
| M_free | - | pooled | V4 | 0 | - | - | - |
| M_free | - | pooled | V5 | 390 | 0.0123 | 0.0903 | 0.2867 |
| M_free | - | pooled | V6 | 57 | 0.0101 | 0.0508 | 0.0903 |
| M_free | - | pooled | benign | 0 | - | - | - |

## Verdict-level repeat agreement

Two repeats of the same item at temperature 0 can differ in text (batch-numeric nondeterminism in the engine). A text-identical pair is a trivially identical verdict, because the guard is deterministic; the question is how many of the text-differing rows change the G_CERT outcome.

| mode | thinking | pair | items | text identical | text differing | G_CERT terminal differs | of which text-differing | verdict fingerprint differs |
|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0r1 | 2000 | 1786 | 214 | 23 | 23 | 81 |
| M_constrained | - | r0r2 | 2000 | 1786 | 214 | 23 | 23 | 81 |
| M_constrained | - | r1r2 | 2000 | 2000 | 0 | 0 | 0 | 0 |
| M_free | - | r0r1 | 2000 | 2000 | 0 | 0 | 0 | 0 |
| M_free | - | r0r2 | 2000 | 2000 | 0 | 0 | 0 | 0 |
| M_free | - | r1r2 | 2000 | 2000 | 0 | 0 | 0 | 0 |

## Latency and tokens

| mode | thinking | repeat | rows | median latency ms | rows with latency | median completion tokens | median prompt tokens | median reasoning tokens | finish_reason = length |
|---|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 2000 | - | 0 | 55 | 1561 | - | 0 |
| M_constrained | - | r1 | 2000 | - | 0 | 55 | 1561 | - | 0 |
| M_constrained | - | r2 | 2000 | - | 0 | 55 | 1561 | - | 0 |
| M_free | - | r0 | 2000 | - | 0 | 55 | 1561 | - | 0 |
| M_free | - | r1 | 2000 | - | 0 | 55 | 1561 | - | 0 |
| M_free | - | r2 | 2000 | - | 0 | 55 | 1561 | - | 0 |
| M_constrained | - | pooled | 6000 | - | 0 | 55 | 1561 | - | 0 |
| M_free | - | pooled | 6000 | - | 0 | 55 | 1561 | - | 0 |

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
| UNGUARDED never blocks (it has no gating stage; its terminals are applied_uncertified and execution_failed) | 0 blocked; terminals {'applied_uncertified': 11311, 'execution_failed': 689} | PASS |
| G_CERT blocked_qual > 0 on V3 under M_constrained (suite gate: 182/220 blocked on its 880-item subset; applies to shape-enforcing arms only — a json_object arm blocks V3 at the schema stage, which is the enforcement-axis finding) | 220 V3 items per repeat; blocked_qual {'r0': 192, 'r1': 191, 'r2': 191}; all G_CERT blocks {'r0': '193/220', 'r1': '192/220', 'r2': '192/220'} | PASS |
| M_free off-shape (json_invalid + wrong_shape) dominates the EMITTED documents (model-level refusals shown beside it; proves the free arm ran unenforced) | qwen3.6-27b-fp8: 89.3% of emitted (0.0% refused) | PASS |
| M_constrained emits no malformed or wrong-shape JSON, truncations and model-level refusals aside (the grammar or server schema guarantees the shape of what IS emitted, not that anything is; applies to shape-enforcing arms only — a json_object arm's off-shape share is the enforcement-axis finding) | 0 of 6000 rows off-shape; 0 truncated at max_tokens; 0 model refusals/empty | PASS |

Files: `proposals.jsonl` (canonical log, G_CERT verdicts), `verdicts_UNGUARDED.jsonl`, `verdicts_G_FEAS.jsonl`, `verdicts_G_CERT.jsonl`, `summary.json`, `run_meta.json`.