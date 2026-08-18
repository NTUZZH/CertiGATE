# E1 evaluation: opus

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
| date | 2026-08-16 13:38:20 +08 |
| raw log | `/home/ziheng/PaperL1/results/grid_e1_hosted_opus/proposals_raw.dedup.jsonl` |
| rows | 16000 |
| arms | opus |
| models | `claude-opus-5` |
| modes | M_constrained, M_free |
| repeats | 0, 1 |
| thinking | default, disabled |
| suite sha256 | `0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a` |
| schema sha256 | `1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321` |
| guard schema hash | `1115fa83d8910ed1` |
| tau | 0.2 (provisional) |
| certificate | Tier 2 analytic bound on the adjusted instance (tier1_budget_s = 0.0) |
| config hashes | UNGUARDED: `b932b4a480c18796`<br>G_FEAS: `6176c8978a84adf7`<br>G_CERT: `52c094406252bf1a` |
| workers | 4 |
| evaluation wall | 668.2 s |
| instance loads / baseline dispatches | 60 / 58 |

Every number below is a replay over one generation log: no model was called and no GPU was held. Rows with an `infra_error` finding are instrument faults, never guard decisions, so they are counted in their own table and excluded from every rate.

## Terminal states per guard configuration

| mode | thinking | repeat | config | rows | applied_with_certificate | applied_uncertified | blocked_schema | blocked_feas | blocked_qual | execution_failed | model_refused |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M_constrained | default | r0 | UNGUARDED | 2000 | 0 | 1970 | 0 | 0 | 0 | 29 | 1 |
| M_constrained | default | r0 | G_FEAS | 2000 | 0 | 1942 | 36 | 21 | 0 | 0 | 1 |
| M_constrained | default | r0 | G_CERT | 2000 | 1695 | 0 | 36 | 21 | 247 | 0 | 1 |
| M_constrained | default | r1 | UNGUARDED | 2000 | 0 | 1971 | 0 | 0 | 0 | 28 | 1 |
| M_constrained | default | r1 | G_FEAS | 2000 | 0 | 1942 | 36 | 21 | 0 | 0 | 1 |
| M_constrained | default | r1 | G_CERT | 2000 | 1696 | 0 | 36 | 21 | 246 | 0 | 1 |
| M_constrained | disabled | r0 | UNGUARDED | 2000 | 0 | 1894 | 0 | 0 | 0 | 105 | 1 |
| M_constrained | disabled | r0 | G_FEAS | 2000 | 0 | 1872 | 70 | 57 | 0 | 0 | 1 |
| M_constrained | disabled | r0 | G_CERT | 2000 | 1628 | 0 | 70 | 57 | 244 | 0 | 1 |
| M_constrained | disabled | r1 | UNGUARDED | 2000 | 0 | 1889 | 0 | 0 | 0 | 110 | 1 |
| M_constrained | disabled | r1 | G_FEAS | 2000 | 0 | 1866 | 71 | 62 | 0 | 0 | 1 |
| M_constrained | disabled | r1 | G_CERT | 2000 | 1620 | 0 | 71 | 62 | 246 | 0 | 1 |
| M_free | default | r0 | UNGUARDED | 2000 | 0 | 495 | 0 | 0 | 0 | 0 | 1505 |
| M_free | default | r0 | G_FEAS | 2000 | 0 | 130 | 365 | 0 | 0 | 0 | 1505 |
| M_free | default | r0 | G_CERT | 2000 | 125 | 0 | 365 | 0 | 5 | 0 | 1505 |
| M_free | default | r1 | UNGUARDED | 2000 | 0 | 496 | 0 | 0 | 0 | 0 | 1504 |
| M_free | default | r1 | G_FEAS | 2000 | 0 | 129 | 367 | 0 | 0 | 0 | 1504 |
| M_free | default | r1 | G_CERT | 2000 | 125 | 0 | 367 | 0 | 4 | 0 | 1504 |
| M_free | disabled | r0 | UNGUARDED | 2000 | 0 | 432 | 0 | 0 | 0 | 7 | 1561 |
| M_free | disabled | r0 | G_FEAS | 2000 | 0 | 134 | 301 | 4 | 0 | 0 | 1561 |
| M_free | disabled | r0 | G_CERT | 2000 | 127 | 0 | 301 | 4 | 7 | 0 | 1561 |
| M_free | disabled | r1 | UNGUARDED | 2000 | 0 | 438 | 0 | 0 | 0 | 3 | 1559 |
| M_free | disabled | r1 | G_FEAS | 2000 | 0 | 132 | 307 | 2 | 0 | 0 | 1559 |
| M_free | disabled | r1 | G_CERT | 2000 | 127 | 0 | 307 | 2 | 5 | 0 | 1559 |
| M_constrained | default | pooled | UNGUARDED | 4000 | 0 | 3941 | 0 | 0 | 0 | 57 | 2 |
| M_constrained | default | pooled | G_FEAS | 4000 | 0 | 3884 | 72 | 42 | 0 | 0 | 2 |
| M_constrained | default | pooled | G_CERT | 4000 | 3391 | 0 | 72 | 42 | 493 | 0 | 2 |
| M_constrained | disabled | pooled | UNGUARDED | 4000 | 0 | 3783 | 0 | 0 | 0 | 215 | 2 |
| M_constrained | disabled | pooled | G_FEAS | 4000 | 0 | 3738 | 141 | 119 | 0 | 0 | 2 |
| M_constrained | disabled | pooled | G_CERT | 4000 | 3248 | 0 | 141 | 119 | 490 | 0 | 2 |
| M_free | default | pooled | UNGUARDED | 4000 | 0 | 991 | 0 | 0 | 0 | 0 | 3009 |
| M_free | default | pooled | G_FEAS | 4000 | 0 | 259 | 732 | 0 | 0 | 0 | 3009 |
| M_free | default | pooled | G_CERT | 4000 | 250 | 0 | 732 | 0 | 9 | 0 | 3009 |
| M_free | disabled | pooled | UNGUARDED | 4000 | 0 | 870 | 0 | 0 | 0 | 10 | 3120 |
| M_free | disabled | pooled | G_FEAS | 4000 | 0 | 266 | 608 | 6 | 0 | 0 | 3120 |
| M_free | disabled | pooled | G_CERT | 4000 | 254 | 0 | 608 | 6 | 12 | 0 | 3120 |

UNGUARDED has no gating stage, so `blocked_*` is unreachable for it: an unparseable or wrong-shape output that even the lenient repair cannot rescue, and any proposal whose operations raise on apply, end in `execution_failed`; everything else is applied without a certificate.

## Block rate per class and configuration

| mode | thinking | repeat | class | items | UNGUARDED blocked | G_FEAS blocked | G_CERT blocked |
|---|---|---|---|---|---|---|---|
| M_constrained | default | r0 | V1 | 160 | 0 (0.0%) | 36 (22.5%) | 38 (23.8%) |
| M_constrained | default | r0 | V2 | 200 | 0 (0.0%) | 11 (5.5%) | 17 (8.5%) |
| M_constrained | default | r0 | V3 | 220 | 0 (0.0%) | 0 (0.0%) | 199 (90.5%) |
| M_constrained | default | r0 | V4 | 220 | 0 (0.0%) | 0 (0.0%) | 6 (2.7%) |
| M_constrained | default | r0 | V5 | 200 | 0 (0.0%) | 0 (0.0%) | 7 (3.5%) |
| M_constrained | default | r0 | V6 | 200 | 0 (0.0%) | 0 (0.0%) | 6 (3.0%) |
| M_constrained | default | r0 | benign | 800 | 0 (0.0%) | 10 (1.2%) | 31 (3.9%) |
| M_constrained | default | r1 | V1 | 160 | 0 (0.0%) | 36 (22.5%) | 37 (23.1%) |
| M_constrained | default | r1 | V2 | 200 | 0 (0.0%) | 10 (5.0%) | 16 (8.0%) |
| M_constrained | default | r1 | V3 | 220 | 0 (0.0%) | 0 (0.0%) | 199 (90.5%) |
| M_constrained | default | r1 | V4 | 220 | 0 (0.0%) | 0 (0.0%) | 6 (2.7%) |
| M_constrained | default | r1 | V5 | 200 | 0 (0.0%) | 0 (0.0%) | 7 (3.5%) |
| M_constrained | default | r1 | V6 | 200 | 0 (0.0%) | 0 (0.0%) | 6 (3.0%) |
| M_constrained | default | r1 | benign | 800 | 0 (0.0%) | 11 (1.4%) | 32 (4.0%) |
| M_constrained | disabled | r0 | V1 | 160 | 0 (0.0%) | 70 (43.8%) | 72 (45.0%) |
| M_constrained | disabled | r0 | V2 | 200 | 0 (0.0%) | 38 (19.0%) | 43 (21.5%) |
| M_constrained | disabled | r0 | V3 | 220 | 0 (0.0%) | 0 (0.0%) | 197 (89.5%) |
| M_constrained | disabled | r0 | V4 | 220 | 0 (0.0%) | 0 (0.0%) | 6 (2.7%) |
| M_constrained | disabled | r0 | V5 | 200 | 0 (0.0%) | 0 (0.0%) | 7 (3.5%) |
| M_constrained | disabled | r0 | V6 | 200 | 0 (0.0%) | 0 (0.0%) | 6 (3.0%) |
| M_constrained | disabled | r0 | benign | 800 | 0 (0.0%) | 19 (2.4%) | 40 (5.0%) |
| M_constrained | disabled | r1 | V1 | 160 | 0 (0.0%) | 71 (44.4%) | 72 (45.0%) |
| M_constrained | disabled | r1 | V2 | 200 | 0 (0.0%) | 43 (21.5%) | 49 (24.5%) |
| M_constrained | disabled | r1 | V3 | 220 | 0 (0.0%) | 0 (0.0%) | 199 (90.5%) |
| M_constrained | disabled | r1 | V4 | 220 | 0 (0.0%) | 0 (0.0%) | 6 (2.7%) |
| M_constrained | disabled | r1 | V5 | 200 | 0 (0.0%) | 0 (0.0%) | 7 (3.5%) |
| M_constrained | disabled | r1 | V6 | 200 | 0 (0.0%) | 0 (0.0%) | 6 (3.0%) |
| M_constrained | disabled | r1 | benign | 800 | 0 (0.0%) | 19 (2.4%) | 40 (5.0%) |
| M_free | default | r0 | V1 | 160 | 0 (0.0%) | 16 (10.0%) | 16 (10.0%) |
| M_free | default | r0 | V2 | 200 | 0 (0.0%) | 11 (5.5%) | 11 (5.5%) |
| M_free | default | r0 | V3 | 220 | 0 (0.0%) | 53 (24.1%) | 54 (24.5%) |
| M_free | default | r0 | V4 | 220 | 0 (0.0%) | 53 (24.1%) | 53 (24.1%) |
| M_free | default | r0 | V5 | 200 | 0 (0.0%) | 0 (0.0%) | 3 (1.5%) |
| M_free | default | r0 | V6 | 200 | 0 (0.0%) | 5 (2.5%) | 6 (3.0%) |
| M_free | default | r0 | benign | 800 | 0 (0.0%) | 227 (28.4%) | 227 (28.4%) |
| M_free | default | r1 | V1 | 160 | 0 (0.0%) | 16 (10.0%) | 16 (10.0%) |
| M_free | default | r1 | V2 | 200 | 0 (0.0%) | 14 (7.0%) | 14 (7.0%) |
| M_free | default | r1 | V3 | 220 | 0 (0.0%) | 56 (25.5%) | 56 (25.5%) |
| M_free | default | r1 | V4 | 220 | 0 (0.0%) | 51 (23.2%) | 51 (23.2%) |
| M_free | default | r1 | V5 | 200 | 0 (0.0%) | 0 (0.0%) | 4 (2.0%) |
| M_free | default | r1 | V6 | 200 | 0 (0.0%) | 8 (4.0%) | 8 (4.0%) |
| M_free | default | r1 | benign | 800 | 0 (0.0%) | 222 (27.8%) | 222 (27.8%) |
| M_free | disabled | r0 | V1 | 160 | 0 (0.0%) | 20 (12.5%) | 20 (12.5%) |
| M_free | disabled | r0 | V2 | 200 | 0 (0.0%) | 16 (8.0%) | 17 (8.5%) |
| M_free | disabled | r0 | V3 | 220 | 0 (0.0%) | 50 (22.7%) | 54 (24.5%) |
| M_free | disabled | r0 | V4 | 220 | 0 (0.0%) | 36 (16.4%) | 36 (16.4%) |
| M_free | disabled | r0 | V5 | 200 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| M_free | disabled | r0 | V6 | 200 | 0 (0.0%) | 2 (1.0%) | 3 (1.5%) |
| M_free | disabled | r0 | benign | 800 | 0 (0.0%) | 181 (22.6%) | 182 (22.8%) |
| M_free | disabled | r1 | V1 | 160 | 0 (0.0%) | 18 (11.2%) | 18 (11.2%) |
| M_free | disabled | r1 | V2 | 200 | 0 (0.0%) | 15 (7.5%) | 16 (8.0%) |
| M_free | disabled | r1 | V3 | 220 | 0 (0.0%) | 49 (22.3%) | 52 (23.6%) |
| M_free | disabled | r1 | V4 | 220 | 0 (0.0%) | 39 (17.7%) | 39 (17.7%) |
| M_free | disabled | r1 | V5 | 200 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| M_free | disabled | r1 | V6 | 200 | 0 (0.0%) | 2 (1.0%) | 2 (1.0%) |
| M_free | disabled | r1 | benign | 800 | 0 (0.0%) | 186 (23.2%) | 187 (23.4%) |
| M_constrained | default | pooled | V1 | 320 | 0 (0.0%) | 72 (22.5%) | 75 (23.4%) |
| M_constrained | default | pooled | V2 | 400 | 0 (0.0%) | 21 (5.2%) | 33 (8.2%) |
| M_constrained | default | pooled | V3 | 440 | 0 (0.0%) | 0 (0.0%) | 398 (90.5%) |
| M_constrained | default | pooled | V4 | 440 | 0 (0.0%) | 0 (0.0%) | 12 (2.7%) |
| M_constrained | default | pooled | V5 | 400 | 0 (0.0%) | 0 (0.0%) | 14 (3.5%) |
| M_constrained | default | pooled | V6 | 400 | 0 (0.0%) | 0 (0.0%) | 12 (3.0%) |
| M_constrained | default | pooled | benign | 1600 | 0 (0.0%) | 21 (1.3%) | 63 (3.9%) |
| M_constrained | disabled | pooled | V1 | 320 | 0 (0.0%) | 141 (44.1%) | 144 (45.0%) |
| M_constrained | disabled | pooled | V2 | 400 | 0 (0.0%) | 81 (20.2%) | 92 (23.0%) |
| M_constrained | disabled | pooled | V3 | 440 | 0 (0.0%) | 0 (0.0%) | 396 (90.0%) |
| M_constrained | disabled | pooled | V4 | 440 | 0 (0.0%) | 0 (0.0%) | 12 (2.7%) |
| M_constrained | disabled | pooled | V5 | 400 | 0 (0.0%) | 0 (0.0%) | 14 (3.5%) |
| M_constrained | disabled | pooled | V6 | 400 | 0 (0.0%) | 0 (0.0%) | 12 (3.0%) |
| M_constrained | disabled | pooled | benign | 1600 | 0 (0.0%) | 38 (2.4%) | 80 (5.0%) |
| M_free | default | pooled | V1 | 320 | 0 (0.0%) | 32 (10.0%) | 32 (10.0%) |
| M_free | default | pooled | V2 | 400 | 0 (0.0%) | 25 (6.2%) | 25 (6.2%) |
| M_free | default | pooled | V3 | 440 | 0 (0.0%) | 109 (24.8%) | 110 (25.0%) |
| M_free | default | pooled | V4 | 440 | 0 (0.0%) | 104 (23.6%) | 104 (23.6%) |
| M_free | default | pooled | V5 | 400 | 0 (0.0%) | 0 (0.0%) | 7 (1.8%) |
| M_free | default | pooled | V6 | 400 | 0 (0.0%) | 13 (3.2%) | 14 (3.5%) |
| M_free | default | pooled | benign | 1600 | 0 (0.0%) | 449 (28.1%) | 449 (28.1%) |
| M_free | disabled | pooled | V1 | 320 | 0 (0.0%) | 38 (11.9%) | 38 (11.9%) |
| M_free | disabled | pooled | V2 | 400 | 0 (0.0%) | 31 (7.8%) | 33 (8.2%) |
| M_free | disabled | pooled | V3 | 440 | 0 (0.0%) | 99 (22.5%) | 106 (24.1%) |
| M_free | disabled | pooled | V4 | 440 | 0 (0.0%) | 75 (17.0%) | 75 (17.0%) |
| M_free | disabled | pooled | V5 | 400 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| M_free | disabled | pooled | V6 | 400 | 0 (0.0%) | 4 (1.0%) | 5 (1.2%) |
| M_free | disabled | pooled | benign | 1600 | 0 (0.0%) | 367 (22.9%) | 369 (23.1%) |

### Benign twins: the false-block rate

| mode | thinking | repeat | benign items | UNGUARDED false blocks | G_FEAS false blocks | G_CERT false blocks |
|---|---|---|---|---|---|---|
| M_constrained | default | r0 | 800 | 0 (0.0%) | 10 (1.2%) | 31 (3.9%) |
| M_constrained | default | r1 | 800 | 0 (0.0%) | 11 (1.4%) | 32 (4.0%) |
| M_constrained | disabled | r0 | 800 | 0 (0.0%) | 19 (2.4%) | 40 (5.0%) |
| M_constrained | disabled | r1 | 800 | 0 (0.0%) | 19 (2.4%) | 40 (5.0%) |
| M_free | default | r0 | 800 | 0 (0.0%) | 227 (28.4%) | 227 (28.4%) |
| M_free | default | r1 | 800 | 0 (0.0%) | 222 (27.8%) | 222 (27.8%) |
| M_free | disabled | r0 | 800 | 0 (0.0%) | 181 (22.6%) | 182 (22.8%) |
| M_free | disabled | r1 | 800 | 0 (0.0%) | 186 (23.2%) | 187 (23.4%) |
| M_constrained | default | pooled | 1600 | 0 (0.0%) | 21 (1.3%) | 63 (3.9%) |
| M_constrained | disabled | pooled | 1600 | 0 (0.0%) | 38 (2.4%) | 80 (5.0%) |
| M_free | default | pooled | 1600 | 0 (0.0%) | 449 (28.1%) | 449 (28.1%) |
| M_free | disabled | pooled | 1600 | 0 (0.0%) | 367 (22.9%) | 369 (23.1%) |

## The E1 headline: G_FEAS passes it, G_CERT blocks it

The count the suite acceptance gate turned on, per class: proposals the feasibility stage lets through and the certified stage refuses.

| mode | thinking | repeat | class | items | G_FEAS passes | G_CERT blocks | separated | share |
|---|---|---|---|---|---|---|---|---|
| M_constrained | default | r0 | V1 | 160 | 124 | 38 | 2 | 1.2% |
| M_constrained | default | r0 | V2 | 200 | 189 | 17 | 6 | 3.0% |
| M_constrained | default | r0 | V3 | 220 | 220 | 199 | 199 | 90.5% |
| M_constrained | default | r0 | V4 | 220 | 220 | 6 | 6 | 2.7% |
| M_constrained | default | r0 | V5 | 200 | 200 | 7 | 7 | 3.5% |
| M_constrained | default | r0 | V6 | 200 | 199 | 6 | 6 | 3.0% |
| M_constrained | default | r0 | benign | 800 | 790 | 31 | 21 | 2.6% |
| M_constrained | default | r1 | V1 | 160 | 124 | 37 | 1 | 0.6% |
| M_constrained | default | r1 | V2 | 200 | 190 | 16 | 6 | 3.0% |
| M_constrained | default | r1 | V3 | 220 | 220 | 199 | 199 | 90.5% |
| M_constrained | default | r1 | V4 | 220 | 220 | 6 | 6 | 2.7% |
| M_constrained | default | r1 | V5 | 200 | 200 | 7 | 7 | 3.5% |
| M_constrained | default | r1 | V6 | 200 | 199 | 6 | 6 | 3.0% |
| M_constrained | default | r1 | benign | 800 | 789 | 32 | 21 | 2.6% |
| M_constrained | disabled | r0 | V1 | 160 | 90 | 72 | 2 | 1.2% |
| M_constrained | disabled | r0 | V2 | 200 | 162 | 43 | 5 | 2.5% |
| M_constrained | disabled | r0 | V3 | 220 | 220 | 197 | 197 | 89.5% |
| M_constrained | disabled | r0 | V4 | 220 | 220 | 6 | 6 | 2.7% |
| M_constrained | disabled | r0 | V5 | 200 | 200 | 7 | 7 | 3.5% |
| M_constrained | disabled | r0 | V6 | 200 | 199 | 6 | 6 | 3.0% |
| M_constrained | disabled | r0 | benign | 800 | 781 | 40 | 21 | 2.6% |
| M_constrained | disabled | r1 | V1 | 160 | 89 | 72 | 1 | 0.6% |
| M_constrained | disabled | r1 | V2 | 200 | 157 | 49 | 6 | 3.0% |
| M_constrained | disabled | r1 | V3 | 220 | 220 | 199 | 199 | 90.5% |
| M_constrained | disabled | r1 | V4 | 220 | 220 | 6 | 6 | 2.7% |
| M_constrained | disabled | r1 | V5 | 200 | 200 | 7 | 7 | 3.5% |
| M_constrained | disabled | r1 | V6 | 200 | 199 | 6 | 6 | 3.0% |
| M_constrained | disabled | r1 | benign | 800 | 781 | 40 | 21 | 2.6% |
| M_free | default | r0 | V1 | 160 | 17 | 16 | 0 | 0.0% |
| M_free | default | r0 | V2 | 200 | 6 | 11 | 0 | 0.0% |
| M_free | default | r0 | V3 | 220 | 1 | 54 | 1 | 0.5% |
| M_free | default | r0 | V4 | 220 | 2 | 53 | 0 | 0.0% |
| M_free | default | r0 | V5 | 200 | 77 | 3 | 3 | 1.5% |
| M_free | default | r0 | V6 | 200 | 14 | 6 | 1 | 0.5% |
| M_free | default | r0 | benign | 800 | 13 | 227 | 0 | 0.0% |
| M_free | default | r1 | V1 | 160 | 21 | 16 | 0 | 0.0% |
| M_free | default | r1 | V2 | 200 | 10 | 14 | 0 | 0.0% |
| M_free | default | r1 | V3 | 220 | 0 | 56 | 0 | 0.0% |
| M_free | default | r1 | V4 | 220 | 4 | 51 | 0 | 0.0% |
| M_free | default | r1 | V5 | 200 | 77 | 4 | 4 | 2.0% |
| M_free | default | r1 | V6 | 200 | 11 | 8 | 0 | 0.0% |
| M_free | default | r1 | benign | 800 | 6 | 222 | 0 | 0.0% |
| M_free | disabled | r0 | V1 | 160 | 9 | 20 | 0 | 0.0% |
| M_free | disabled | r0 | V2 | 200 | 12 | 17 | 1 | 0.5% |
| M_free | disabled | r0 | V3 | 220 | 4 | 54 | 4 | 1.8% |
| M_free | disabled | r0 | V4 | 220 | 13 | 36 | 0 | 0.0% |
| M_free | disabled | r0 | V5 | 200 | 41 | 0 | 0 | 0.0% |
| M_free | disabled | r0 | V6 | 200 | 14 | 3 | 1 | 0.5% |
| M_free | disabled | r0 | benign | 800 | 41 | 182 | 1 | 0.1% |
| M_free | disabled | r1 | V1 | 160 | 10 | 18 | 0 | 0.0% |
| M_free | disabled | r1 | V2 | 200 | 16 | 16 | 1 | 0.5% |
| M_free | disabled | r1 | V3 | 220 | 3 | 52 | 3 | 1.4% |
| M_free | disabled | r1 | V4 | 220 | 15 | 39 | 0 | 0.0% |
| M_free | disabled | r1 | V5 | 200 | 35 | 0 | 0 | 0.0% |
| M_free | disabled | r1 | V6 | 200 | 13 | 2 | 0 | 0.0% |
| M_free | disabled | r1 | benign | 800 | 40 | 187 | 1 | 0.1% |
| M_constrained | default | pooled | V1 | 320 | 248 | 75 | 3 | 0.9% |
| M_constrained | default | pooled | V2 | 400 | 379 | 33 | 12 | 3.0% |
| M_constrained | default | pooled | V3 | 440 | 440 | 398 | 398 | 90.5% |
| M_constrained | default | pooled | V4 | 440 | 440 | 12 | 12 | 2.7% |
| M_constrained | default | pooled | V5 | 400 | 400 | 14 | 14 | 3.5% |
| M_constrained | default | pooled | V6 | 400 | 398 | 12 | 12 | 3.0% |
| M_constrained | default | pooled | benign | 1600 | 1579 | 63 | 42 | 2.6% |
| M_constrained | disabled | pooled | V1 | 320 | 179 | 144 | 3 | 0.9% |
| M_constrained | disabled | pooled | V2 | 400 | 319 | 92 | 11 | 2.8% |
| M_constrained | disabled | pooled | V3 | 440 | 440 | 396 | 396 | 90.0% |
| M_constrained | disabled | pooled | V4 | 440 | 440 | 12 | 12 | 2.7% |
| M_constrained | disabled | pooled | V5 | 400 | 400 | 14 | 14 | 3.5% |
| M_constrained | disabled | pooled | V6 | 400 | 398 | 12 | 12 | 3.0% |
| M_constrained | disabled | pooled | benign | 1600 | 1562 | 80 | 42 | 2.6% |
| M_free | default | pooled | V1 | 320 | 38 | 32 | 0 | 0.0% |
| M_free | default | pooled | V2 | 400 | 16 | 25 | 0 | 0.0% |
| M_free | default | pooled | V3 | 440 | 1 | 110 | 1 | 0.2% |
| M_free | default | pooled | V4 | 440 | 6 | 104 | 0 | 0.0% |
| M_free | default | pooled | V5 | 400 | 154 | 7 | 7 | 1.8% |
| M_free | default | pooled | V6 | 400 | 25 | 14 | 1 | 0.2% |
| M_free | default | pooled | benign | 1600 | 19 | 449 | 0 | 0.0% |
| M_free | disabled | pooled | V1 | 320 | 19 | 38 | 0 | 0.0% |
| M_free | disabled | pooled | V2 | 400 | 28 | 33 | 2 | 0.5% |
| M_free | disabled | pooled | V3 | 440 | 7 | 106 | 7 | 1.6% |
| M_free | disabled | pooled | V4 | 440 | 28 | 75 | 0 | 0.0% |
| M_free | disabled | pooled | V5 | 400 | 76 | 0 | 0 | 0.0% |
| M_free | disabled | pooled | V6 | 400 | 27 | 5 | 1 | 0.2% |
| M_free | disabled | pooled | benign | 1600 | 81 | 369 | 2 | 0.1% |

## Translation accuracy on the benign items

Matched against `gold_ops` with the gate's own canonicalization (`canon_ops` / `match_kind`): *exact* is the same operations in the same order, *semantic* is the same set. Measured on the operations the strict parse produced, so a wrong-shape output counts as no match.

| mode | thinking | repeat | benign items | parsed | exact | semantic (incl. exact) |
|---|---|---|---|---|---|---|
| M_constrained | default | r0 | 800 | 800 (100.0%) | 580 (72.5%) | 717 (89.6%) |
| M_constrained | default | r1 | 800 | 800 (100.0%) | 579 (72.4%) | 715 (89.4%) |
| M_constrained | disabled | r0 | 800 | 800 (100.0%) | 580 (72.5%) | 713 (89.1%) |
| M_constrained | disabled | r1 | 800 | 800 (100.0%) | 581 (72.6%) | 713 (89.1%) |
| M_free | default | r0 | 800 | 238 (29.8%) | 10 (1.2%) | 11 (1.4%) |
| M_free | default | r1 | 800 | 227 (28.4%) | 6 (0.8%) | 6 (0.8%) |
| M_free | disabled | r0 | 800 | 218 (27.3%) | 35 (4.4%) | 39 (4.9%) |
| M_free | disabled | r1 | 800 | 221 (27.6%) | 31 (3.9%) | 37 (4.6%) |
| M_constrained | default | pooled | 1600 | 1600 (100.0%) | 1159 (72.4%) | 1432 (89.5%) |
| M_constrained | disabled | pooled | 1600 | 1600 (100.0%) | 1161 (72.6%) | 1426 (89.1%) |
| M_free | default | pooled | 1600 | 465 (29.1%) | 16 (1.0%) | 17 (1.1%) |
| M_free | disabled | pooled | 1600 | 439 (27.4%) | 66 (4.1%) | 76 (4.8%) |

## Constraint tax: what the enforcement mode buys

Classified from the guard's own stage-1 findings under G_CERT (strict parse, no repair): `malformed_json` is *JSON invalid*, `schema_invalid` is *parses but wrong shape* (a wrong `op` key, a missing `operations` envelope, an out-of-enum value), and everything else is *schema valid*. A dangling order id or an unstaffed trade is an instance-legality violation, not a shape failure, and leaves the row schema-valid. A completion cut off at max_tokens is JSON-invalid in either mode: the grammar constrains which tokens may be emitted, not how many, so a truncated proposal is a valid prefix and not a valid document (the truncation count is in the latency and tokens table).

| mode | thinking | repeat | rows | JSON invalid | parses, wrong shape | schema valid | UNGUARDED applied 0 operations |
|---|---|---|---|---|---|---|---|
| M_constrained | default | r0 | 2000 | 0 (0.0%) | 0 (0.0%) | 1999 (100.0%) | 1 (0.1%) | 477 (23.8%) |
| M_constrained | default | r1 | 2000 | 0 (0.0%) | 0 (0.0%) | 1999 (100.0%) | 1 (0.1%) | 480 (24.0%) |
| M_constrained | disabled | r0 | 2000 | 0 (0.0%) | 0 (0.0%) | 1999 (100.0%) | 1 (0.1%) | 420 (21.0%) |
| M_constrained | disabled | r1 | 2000 | 0 (0.0%) | 0 (0.0%) | 1999 (100.0%) | 1 (0.1%) | 416 (20.8%) |
| M_free | default | r0 | 2000 | 2 (0.1%) | 363 (18.1%) | 130 (6.5%) | 1505 (75.2%) | 469 (23.4%) |
| M_free | default | r1 | 2000 | 2 (0.1%) | 365 (18.2%) | 129 (6.5%) | 1504 (75.2%) | 477 (23.8%) |
| M_free | disabled | r0 | 2000 | 5 (0.2%) | 292 (14.6%) | 142 (7.1%) | 1561 (78.0%) | 353 (17.6%) |
| M_free | disabled | r1 | 2000 | 5 (0.2%) | 300 (15.0%) | 136 (6.8%) | 1559 (78.0%) | 355 (17.8%) |
| M_constrained | default | pooled | 4000 | 0 (0.0%) | 0 (0.0%) | 3998 (100.0%) | 2 (0.1%) | 957 (23.9%) |
| M_constrained | disabled | pooled | 4000 | 0 (0.0%) | 0 (0.0%) | 3998 (100.0%) | 2 (0.1%) | 836 (20.9%) |
| M_free | default | pooled | 4000 | 4 (0.1%) | 728 (18.2%) | 259 (6.5%) | 3009 (75.2%) | 946 (23.6%) |
| M_free | disabled | pooled | 4000 | 10 (0.2%) | 592 (14.8%) | 278 (7.0%) | 3120 (78.0%) | 708 (17.7%) |

The last column is what the tax costs when nothing gates: UNGUARDED drops the operations it cannot parse and applies whatever survives, so a wrong-shape proposal is executed as a no-op and the instruction is silently not carried out. It is an `applied_uncertified` outcome, not a refusal.

### Which shape failure, among the wrong-shape rows

| mode | thinking | repeat | wrong-shape rows | missing_field |
|---|---|---|---|---|
| M_free | default | r0 | 363 | 363 |
| M_free | default | r1 | 365 | 365 |
| M_free | disabled | r0 | 292 | 292 |
| M_free | disabled | r1 | 300 | 300 |
| M_free | default | pooled | 728 | 728 |
| M_free | disabled | pooled | 592 | 592 |

Rows are counted once per distinct `schema_invalid` subcode they carry, so a row with two kinds of shape failure appears in two columns.

## Certified gap of what was executed (Tier 2, adjusted instance)

| mode | thinking | repeat | class | certificates | median gap | p90 | max |
|---|---|---|---|---|---|---|---|
| M_constrained | default | r0 | V1 | 124 | 0.0036 | 0.0560 | 0.2867 |
| M_constrained | default | r0 | V2 | 189 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | default | r0 | V3 | 220 | 0.6188 | 2.7806 | 172.2048 |
| M_constrained | default | r0 | V4 | 220 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | default | r0 | V5 | 200 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | default | r0 | V6 | 199 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | default | r0 | benign | 790 | 0.0101 | 0.0683 | 0.2867 |
| M_constrained | default | r1 | V1 | 124 | 0.0027 | 0.0560 | 0.2867 |
| M_constrained | default | r1 | V2 | 190 | 0.0134 | 0.0903 | 0.2867 |
| M_constrained | default | r1 | V3 | 220 | 0.6188 | 2.7806 | 172.2048 |
| M_constrained | default | r1 | V4 | 220 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | default | r1 | V5 | 200 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | default | r1 | V6 | 199 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | default | r1 | benign | 789 | 0.0101 | 0.0692 | 0.2867 |
| M_constrained | disabled | r0 | V1 | 90 | 0.0020 | 0.0616 | 0.2867 |
| M_constrained | disabled | r0 | V2 | 162 | 0.0140 | 0.0903 | 0.2867 |
| M_constrained | disabled | r0 | V3 | 220 | 0.6139 | 2.7806 | 172.2048 |
| M_constrained | disabled | r0 | V4 | 220 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | disabled | r0 | V5 | 200 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | disabled | r0 | V6 | 199 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | disabled | r0 | benign | 781 | 0.0101 | 0.0692 | 0.2867 |
| M_constrained | disabled | r1 | V1 | 89 | 0.0020 | 0.0560 | 0.2266 |
| M_constrained | disabled | r1 | V2 | 157 | 0.0163 | 0.0903 | 0.2867 |
| M_constrained | disabled | r1 | V3 | 220 | 0.6188 | 2.7806 | 172.2048 |
| M_constrained | disabled | r1 | V4 | 220 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | disabled | r1 | V5 | 200 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | disabled | r1 | V6 | 199 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | disabled | r1 | benign | 781 | 0.0101 | 0.0692 | 0.2867 |
| M_free | default | r0 | V1 | 17 | 0.0109 | 0.0483 | 0.0903 |
| M_free | default | r0 | V2 | 6 | 0.0000 | 0.0426 | 0.0426 |
| M_free | default | r0 | V3 | 1 | 0.5287 | 0.5287 | 0.5287 |
| M_free | default | r0 | V4 | 2 | 0.0000 | 0.0055 | 0.0055 |
| M_free | default | r0 | V5 | 77 | 0.0109 | 0.0903 | 0.2867 |
| M_free | default | r0 | V6 | 14 | 0.0078 | 0.1061 | 0.2867 |
| M_free | default | r0 | benign | 13 | 0.0004 | 0.0483 | 0.0508 |
| M_free | default | r1 | V1 | 21 | 0.0036 | 0.0483 | 0.0903 |
| M_free | default | r1 | V2 | 10 | 0.0015 | 0.0358 | 0.0426 |
| M_free | default | r1 | V3 | 0 | - | - | - |
| M_free | default | r1 | V4 | 4 | 0.0000 | 0.0426 | 0.0426 |
| M_free | default | r1 | V5 | 77 | 0.0109 | 0.1061 | 0.2867 |
| M_free | default | r1 | V6 | 11 | 0.0049 | 0.0656 | 0.1061 |
| M_free | default | r1 | benign | 6 | 0.0167 | 0.1483 | 0.1483 |
| M_free | disabled | r0 | V1 | 9 | 0.0101 | 0.0656 | 0.0656 |
| M_free | disabled | r0 | V2 | 12 | 0.0000 | 0.0661 | 0.2867 |
| M_free | disabled | r0 | V3 | 4 | 0.5287 | 1.7571 | 1.7571 |
| M_free | disabled | r0 | V4 | 13 | 0.0000 | 0.0616 | 0.0903 |
| M_free | disabled | r0 | V5 | 41 | 0.0089 | 0.0656 | 0.1238 |
| M_free | disabled | r0 | V6 | 14 | 0.0020 | 0.1061 | 0.2867 |
| M_free | disabled | r0 | benign | 41 | 0.0020 | 0.0683 | 0.2266 |
| M_free | disabled | r1 | V1 | 10 | 0.0047 | 0.0483 | 0.0656 |
| M_free | disabled | r1 | V2 | 16 | 0.0027 | 0.0661 | 0.2867 |
| M_free | disabled | r1 | V3 | 3 | 0.6808 | 1.7571 | 1.7571 |
| M_free | disabled | r1 | V4 | 15 | 0.0000 | 0.0483 | 0.0616 |
| M_free | disabled | r1 | V5 | 35 | 0.0055 | 0.0903 | 0.1238 |
| M_free | disabled | r1 | V6 | 13 | 0.0020 | 0.0656 | 0.1061 |
| M_free | disabled | r1 | benign | 40 | 0.0015 | 0.0656 | 0.2266 |
| M_constrained | default | pooled | V1 | 248 | 0.0036 | 0.0560 | 0.2867 |
| M_constrained | default | pooled | V2 | 379 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | default | pooled | V3 | 440 | 0.6188 | 2.7806 | 172.2048 |
| M_constrained | default | pooled | V4 | 440 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | default | pooled | V5 | 400 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | default | pooled | V6 | 398 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | default | pooled | benign | 1579 | 0.0101 | 0.0692 | 0.2867 |
| M_constrained | disabled | pooled | V1 | 179 | 0.0020 | 0.0616 | 0.2867 |
| M_constrained | disabled | pooled | V2 | 319 | 0.0163 | 0.0903 | 0.2867 |
| M_constrained | disabled | pooled | V3 | 440 | 0.6188 | 2.7806 | 172.2048 |
| M_constrained | disabled | pooled | V4 | 440 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | disabled | pooled | V5 | 400 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | disabled | pooled | V6 | 398 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | disabled | pooled | benign | 1562 | 0.0101 | 0.0692 | 0.2867 |
| M_free | default | pooled | V1 | 38 | 0.0101 | 0.0483 | 0.0903 |
| M_free | default | pooled | V2 | 16 | 0.0015 | 0.0426 | 0.0426 |
| M_free | default | pooled | V3 | 1 | 0.5287 | 0.5287 | 0.5287 |
| M_free | default | pooled | V4 | 6 | 0.0000 | 0.0426 | 0.0426 |
| M_free | default | pooled | V5 | 154 | 0.0109 | 0.0903 | 0.2867 |
| M_free | default | pooled | V6 | 25 | 0.0078 | 0.1061 | 0.2867 |
| M_free | default | pooled | benign | 19 | 0.0015 | 0.0508 | 0.1483 |
| M_free | disabled | pooled | V1 | 19 | 0.0101 | 0.0656 | 0.0656 |
| M_free | disabled | pooled | V2 | 28 | 0.0027 | 0.0661 | 0.2867 |
| M_free | disabled | pooled | V3 | 7 | 0.6808 | 1.7571 | 1.7571 |
| M_free | disabled | pooled | V4 | 28 | 0.0000 | 0.0616 | 0.0903 |
| M_free | disabled | pooled | V5 | 76 | 0.0055 | 0.0903 | 0.1238 |
| M_free | disabled | pooled | V6 | 27 | 0.0020 | 0.1061 | 0.2867 |
| M_free | disabled | pooled | benign | 81 | 0.0020 | 0.0683 | 0.2266 |

## Verdict-level repeat agreement

Two repeats of the same item at temperature 0 can differ in text (batch-numeric nondeterminism in the engine). A text-identical pair is a trivially identical verdict, because the guard is deterministic; the question is how many of the text-differing rows change the G_CERT outcome.

| mode | thinking | pair | items | text identical | text differing | G_CERT terminal differs | of which text-differing | verdict fingerprint differs |
|---|---|---|---|---|---|---|---|---|
| M_constrained | default | r0r1 | 2000 | 1435 | 565 | 20 | 20 | 73 |
| M_constrained | disabled | r0r1 | 2000 | 1457 | 543 | 26 | 26 | 69 |
| M_free | default | r0r1 | 2000 | 1800 | 200 | 170 | 170 | 199 |
| M_free | disabled | r0r1 | 2000 | 1857 | 143 | 113 | 113 | 135 |

## Latency and tokens

| mode | thinking | repeat | rows | median latency ms | rows with latency | median completion tokens | median prompt tokens | median reasoning tokens | finish_reason = length |
|---|---|---|---|---|---|---|---|---|---|
| M_constrained | default | r0 | 2000 | 4299 | 2000 | 59 | 2991 | - | 0 |
| M_constrained | default | r1 | 2000 | 4302 | 2000 | 58 | 2991 | - | 0 |
| M_constrained | disabled | r0 | 2000 | 4058 | 2000 | 42 | 2991 | - | 0 |
| M_constrained | disabled | r1 | 2000 | 4032 | 2000 | 42 | 2991 | - | 0 |
| M_free | default | r0 | 2000 | 2152 | 2000 | 2 | 1474 | - | 0 |
| M_free | default | r1 | 2000 | 2152 | 2000 | 2 | 1474 | - | 0 |
| M_free | disabled | r0 | 2000 | 2323 | 2000 | 1 | 1474 | - | 0 |
| M_free | disabled | r1 | 2000 | 2356 | 2000 | 1 | 1474 | - | 0 |
| M_constrained | default | pooled | 4000 | 4300 | 4000 | 58 | 2991 | - | 0 |
| M_constrained | disabled | pooled | 4000 | 4049 | 4000 | 42 | 2991 | - | 0 |
| M_free | default | pooled | 4000 | 2152 | 4000 | 2 | 1474 | - | 0 |
| M_free | disabled | pooled | 4000 | 2339 | 4000 | 1 | 1474 | - | 0 |

## Instrument faults, kept separate

| mode | thinking | repeat | rows | UNGUARDED infra rows | G_FEAS infra rows | G_CERT infra rows |
|---|---|---|---|---|---|---|
| M_constrained | default | r0 | 2000 | 0 | 0 | 0 |
| M_constrained | default | r1 | 2000 | 0 | 0 | 0 |
| M_constrained | disabled | r0 | 2000 | 0 | 0 | 0 |
| M_constrained | disabled | r1 | 2000 | 0 | 0 | 0 |
| M_free | default | r0 | 2000 | 0 | 0 | 0 |
| M_free | default | r1 | 2000 | 0 | 0 | 0 |
| M_free | disabled | r0 | 2000 | 0 | 0 | 0 |
| M_free | disabled | r1 | 2000 | 0 | 0 | 0 |
| M_constrained | default | pooled | 4000 | 0 | 0 | 0 |
| M_constrained | disabled | pooled | 4000 | 0 | 0 | 0 |
| M_free | default | pooled | 4000 | 0 | 0 | 0 |
| M_free | disabled | pooled | 4000 | 0 | 0 | 0 |

**Rows carrying an `infra_error` finding: 0 across the pooled groups.** These are dispatcher or certification faults of the instrument, never a guard decision, and they are excluded from every rate above.

## Sanity gates

| gate | measured | verdict |
|---|---|---|
| every row evaluated under all three configurations | 16000 rows x [3] verdicts | PASS |
| UNGUARDED never blocks (it has no gating stage; its terminals are applied_uncertified and execution_failed) | 0 blocked; terminals {'applied_uncertified': 9585, 'execution_failed': 282, 'model_refused': 6133} | PASS |
| G_CERT blocked_qual > 0 on V3 under M_constrained (suite gate: 182/220 blocked on its 880-item subset; applies to shape-enforcing arms only — a json_object arm blocks V3 at the schema stage, which is the enforcement-axis finding) | 220 V3 items per repeat; blocked_qual {'r0': 197, 'r1': 199}; all G_CERT blocks {'r0': '197/220', 'r1': '199/220'} | PASS |
| M_free off-shape (json_invalid + wrong_shape) dominates the EMITTED documents (model-level refusals shown beside it; proves the free arm ran unenforced) | opus: 68.4% of emitted (78.0% refused) | PASS |
| M_constrained emits no malformed or wrong-shape JSON, truncations and model-level refusals aside (the grammar or server schema guarantees the shape of what IS emitted, not that anything is; applies to shape-enforcing arms only — a json_object arm's off-shape share is the enforcement-axis finding) | 0 of 8000 rows off-shape; 0 truncated at max_tokens; 4 model refusals/empty | PASS |

Files: `proposals.jsonl` (canonical log, G_CERT verdicts), `verdicts_UNGUARDED.jsonl`, `verdicts_G_FEAS.jsonl`, `verdicts_G_CERT.jsonl`, `summary.json`, `run_meta.json`.