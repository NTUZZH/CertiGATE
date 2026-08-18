# E1 evaluation: deepseek

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
| date | 2026-08-16 13:20:20 +08 |
| raw log | `/home/ziheng/PaperL1/results/grid_e1_hosted_deepseek/proposals_raw.dedup.jsonl` |
| rows | 16000 |
| arms | deepseek |
| models | `deepseek-v4-pro` |
| modes | M_constrained, M_free |
| repeats | 0, 1 |
| thinking | non_think, think_high |
| suite sha256 | `0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a` |
| schema sha256 | `1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321` |
| guard schema hash | `1115fa83d8910ed1` |
| tau | 0.2 (provisional) |
| certificate | Tier 2 analytic bound on the adjusted instance (tier1_budget_s = 0.0) |
| config hashes | UNGUARDED: `b932b4a480c18796`<br>G_FEAS: `6176c8978a84adf7`<br>G_CERT: `52c094406252bf1a` |
| workers | 4 |
| evaluation wall | 485.3 s |
| instance loads / baseline dispatches | 60 / 57 |

Every number below is a replay over one generation log: no model was called and no GPU was held. Rows with an `infra_error` finding are instrument faults, never guard decisions, so they are counted in their own table and excluded from every rate.

## Terminal states per guard configuration

| mode | thinking | repeat | config | rows | applied_with_certificate | applied_uncertified | blocked_schema | blocked_qual | execution_failed |
|---|---|---|---|---|---|---|---|---|---|
| M_constrained | non_think | r0 | UNGUARDED | 2000 | 0 | 2000 | 0 | 0 | 0 |
| M_constrained | non_think | r0 | G_FEAS | 2000 | 0 | 385 | 1615 | 0 | 0 |
| M_constrained | non_think | r0 | G_CERT | 2000 | 374 | 0 | 1615 | 11 | 0 |
| M_constrained | non_think | r1 | UNGUARDED | 2000 | 0 | 2000 | 0 | 0 | 0 |
| M_constrained | non_think | r1 | G_FEAS | 2000 | 0 | 384 | 1616 | 0 | 0 |
| M_constrained | non_think | r1 | G_CERT | 2000 | 372 | 0 | 1616 | 12 | 0 |
| M_constrained | think_high | r0 | UNGUARDED | 2000 | 0 | 1959 | 0 | 0 | 41 |
| M_constrained | think_high | r0 | G_FEAS | 2000 | 0 | 292 | 1708 | 0 | 0 |
| M_constrained | think_high | r0 | G_CERT | 2000 | 284 | 0 | 1708 | 8 | 0 |
| M_constrained | think_high | r1 | UNGUARDED | 2000 | 0 | 1964 | 0 | 0 | 36 |
| M_constrained | think_high | r1 | G_FEAS | 2000 | 0 | 288 | 1712 | 0 | 0 |
| M_constrained | think_high | r1 | G_CERT | 2000 | 279 | 0 | 1712 | 9 | 0 |
| M_free | non_think | r0 | UNGUARDED | 2000 | 0 | 2000 | 0 | 0 | 0 |
| M_free | non_think | r0 | G_FEAS | 2000 | 0 | 346 | 1654 | 0 | 0 |
| M_free | non_think | r0 | G_CERT | 2000 | 336 | 0 | 1654 | 10 | 0 |
| M_free | non_think | r1 | UNGUARDED | 2000 | 0 | 2000 | 0 | 0 | 0 |
| M_free | non_think | r1 | G_FEAS | 2000 | 0 | 344 | 1656 | 0 | 0 |
| M_free | non_think | r1 | G_CERT | 2000 | 334 | 0 | 1656 | 10 | 0 |
| M_free | think_high | r0 | UNGUARDED | 2000 | 0 | 1981 | 0 | 0 | 19 |
| M_free | think_high | r0 | G_FEAS | 2000 | 0 | 289 | 1711 | 0 | 0 |
| M_free | think_high | r0 | G_CERT | 2000 | 282 | 0 | 1711 | 7 | 0 |
| M_free | think_high | r1 | UNGUARDED | 2000 | 0 | 1986 | 0 | 0 | 14 |
| M_free | think_high | r1 | G_FEAS | 2000 | 0 | 286 | 1714 | 0 | 0 |
| M_free | think_high | r1 | G_CERT | 2000 | 278 | 0 | 1714 | 8 | 0 |
| M_constrained | non_think | pooled | UNGUARDED | 4000 | 0 | 4000 | 0 | 0 | 0 |
| M_constrained | non_think | pooled | G_FEAS | 4000 | 0 | 769 | 3231 | 0 | 0 |
| M_constrained | non_think | pooled | G_CERT | 4000 | 746 | 0 | 3231 | 23 | 0 |
| M_constrained | think_high | pooled | UNGUARDED | 4000 | 0 | 3923 | 0 | 0 | 77 |
| M_constrained | think_high | pooled | G_FEAS | 4000 | 0 | 580 | 3420 | 0 | 0 |
| M_constrained | think_high | pooled | G_CERT | 4000 | 563 | 0 | 3420 | 17 | 0 |
| M_free | non_think | pooled | UNGUARDED | 4000 | 0 | 4000 | 0 | 0 | 0 |
| M_free | non_think | pooled | G_FEAS | 4000 | 0 | 690 | 3310 | 0 | 0 |
| M_free | non_think | pooled | G_CERT | 4000 | 670 | 0 | 3310 | 20 | 0 |
| M_free | think_high | pooled | UNGUARDED | 4000 | 0 | 3967 | 0 | 0 | 33 |
| M_free | think_high | pooled | G_FEAS | 4000 | 0 | 575 | 3425 | 0 | 0 |
| M_free | think_high | pooled | G_CERT | 4000 | 560 | 0 | 3425 | 15 | 0 |

UNGUARDED has no gating stage, so `blocked_*` is unreachable for it: an unparseable or wrong-shape output that even the lenient repair cannot rescue, and any proposal whose operations raise on apply, end in `execution_failed`; everything else is applied without a certificate.

## Block rate per class and configuration

| mode | thinking | repeat | class | items | UNGUARDED blocked | G_FEAS blocked | G_CERT blocked |
|---|---|---|---|---|---|---|---|
| M_constrained | non_think | r0 | V1 | 160 | 0 (0.0%) | 119 (74.4%) | 119 (74.4%) |
| M_constrained | non_think | r0 | V2 | 200 | 0 (0.0%) | 121 (60.5%) | 124 (62.0%) |
| M_constrained | non_think | r0 | V3 | 220 | 0 (0.0%) | 219 (99.5%) | 219 (99.5%) |
| M_constrained | non_think | r0 | V4 | 220 | 0 (0.0%) | 205 (93.2%) | 205 (93.2%) |
| M_constrained | non_think | r0 | V5 | 200 | 0 (0.0%) | 6 (3.0%) | 13 (6.5%) |
| M_constrained | non_think | r0 | V6 | 200 | 0 (0.0%) | 169 (84.5%) | 169 (84.5%) |
| M_constrained | non_think | r0 | benign | 800 | 0 (0.0%) | 776 (97.0%) | 777 (97.1%) |
| M_constrained | non_think | r1 | V1 | 160 | 0 (0.0%) | 119 (74.4%) | 119 (74.4%) |
| M_constrained | non_think | r1 | V2 | 200 | 0 (0.0%) | 121 (60.5%) | 124 (62.0%) |
| M_constrained | non_think | r1 | V3 | 220 | 0 (0.0%) | 218 (99.1%) | 219 (99.5%) |
| M_constrained | non_think | r1 | V4 | 220 | 0 (0.0%) | 206 (93.6%) | 206 (93.6%) |
| M_constrained | non_think | r1 | V5 | 200 | 0 (0.0%) | 6 (3.0%) | 13 (6.5%) |
| M_constrained | non_think | r1 | V6 | 200 | 0 (0.0%) | 169 (84.5%) | 169 (84.5%) |
| M_constrained | non_think | r1 | benign | 800 | 0 (0.0%) | 777 (97.1%) | 778 (97.2%) |
| M_constrained | think_high | r0 | V1 | 160 | 0 (0.0%) | 122 (76.2%) | 122 (76.2%) |
| M_constrained | think_high | r0 | V2 | 200 | 0 (0.0%) | 130 (65.0%) | 132 (66.0%) |
| M_constrained | think_high | r0 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_constrained | think_high | r0 | V4 | 220 | 0 (0.0%) | 218 (99.1%) | 218 (99.1%) |
| M_constrained | think_high | r0 | V5 | 200 | 0 (0.0%) | 39 (19.5%) | 45 (22.5%) |
| M_constrained | think_high | r0 | V6 | 200 | 0 (0.0%) | 182 (91.0%) | 182 (91.0%) |
| M_constrained | think_high | r0 | benign | 800 | 0 (0.0%) | 797 (99.6%) | 797 (99.6%) |
| M_constrained | think_high | r1 | V1 | 160 | 0 (0.0%) | 127 (79.4%) | 127 (79.4%) |
| M_constrained | think_high | r1 | V2 | 200 | 0 (0.0%) | 131 (65.5%) | 133 (66.5%) |
| M_constrained | think_high | r1 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_constrained | think_high | r1 | V4 | 220 | 0 (0.0%) | 218 (99.1%) | 218 (99.1%) |
| M_constrained | think_high | r1 | V5 | 200 | 0 (0.0%) | 39 (19.5%) | 46 (23.0%) |
| M_constrained | think_high | r1 | V6 | 200 | 0 (0.0%) | 183 (91.5%) | 183 (91.5%) |
| M_constrained | think_high | r1 | benign | 800 | 0 (0.0%) | 794 (99.2%) | 794 (99.2%) |
| M_free | non_think | r0 | V1 | 160 | 0 (0.0%) | 125 (78.1%) | 125 (78.1%) |
| M_free | non_think | r0 | V2 | 200 | 0 (0.0%) | 133 (66.5%) | 135 (67.5%) |
| M_free | non_think | r0 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | non_think | r0 | V4 | 220 | 0 (0.0%) | 215 (97.7%) | 215 (97.7%) |
| M_free | non_think | r0 | V5 | 200 | 0 (0.0%) | 8 (4.0%) | 15 (7.5%) |
| M_free | non_think | r0 | V6 | 200 | 0 (0.0%) | 171 (85.5%) | 171 (85.5%) |
| M_free | non_think | r0 | benign | 800 | 0 (0.0%) | 782 (97.8%) | 783 (97.9%) |
| M_free | non_think | r1 | V1 | 160 | 0 (0.0%) | 126 (78.8%) | 126 (78.8%) |
| M_free | non_think | r1 | V2 | 200 | 0 (0.0%) | 133 (66.5%) | 135 (67.5%) |
| M_free | non_think | r1 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | non_think | r1 | V4 | 220 | 0 (0.0%) | 215 (97.7%) | 215 (97.7%) |
| M_free | non_think | r1 | V5 | 200 | 0 (0.0%) | 8 (4.0%) | 15 (7.5%) |
| M_free | non_think | r1 | V6 | 200 | 0 (0.0%) | 172 (86.0%) | 172 (86.0%) |
| M_free | non_think | r1 | benign | 800 | 0 (0.0%) | 782 (97.8%) | 783 (97.9%) |
| M_free | think_high | r0 | V1 | 160 | 0 (0.0%) | 124 (77.5%) | 124 (77.5%) |
| M_free | think_high | r0 | V2 | 200 | 0 (0.0%) | 129 (64.5%) | 131 (65.5%) |
| M_free | think_high | r0 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | think_high | r0 | V4 | 220 | 0 (0.0%) | 218 (99.1%) | 218 (99.1%) |
| M_free | think_high | r0 | V5 | 200 | 0 (0.0%) | 50 (25.0%) | 55 (27.5%) |
| M_free | think_high | r0 | V6 | 200 | 0 (0.0%) | 174 (87.0%) | 174 (87.0%) |
| M_free | think_high | r0 | benign | 800 | 0 (0.0%) | 796 (99.5%) | 796 (99.5%) |
| M_free | think_high | r1 | V1 | 160 | 0 (0.0%) | 122 (76.2%) | 122 (76.2%) |
| M_free | think_high | r1 | V2 | 200 | 0 (0.0%) | 126 (63.0%) | 128 (64.0%) |
| M_free | think_high | r1 | V3 | 220 | 0 (0.0%) | 218 (99.1%) | 218 (99.1%) |
| M_free | think_high | r1 | V4 | 220 | 0 (0.0%) | 218 (99.1%) | 218 (99.1%) |
| M_free | think_high | r1 | V5 | 200 | 0 (0.0%) | 54 (27.0%) | 60 (30.0%) |
| M_free | think_high | r1 | V6 | 200 | 0 (0.0%) | 180 (90.0%) | 180 (90.0%) |
| M_free | think_high | r1 | benign | 800 | 0 (0.0%) | 796 (99.5%) | 796 (99.5%) |
| M_constrained | non_think | pooled | V1 | 320 | 0 (0.0%) | 238 (74.4%) | 238 (74.4%) |
| M_constrained | non_think | pooled | V2 | 400 | 0 (0.0%) | 242 (60.5%) | 248 (62.0%) |
| M_constrained | non_think | pooled | V3 | 440 | 0 (0.0%) | 437 (99.3%) | 438 (99.5%) |
| M_constrained | non_think | pooled | V4 | 440 | 0 (0.0%) | 411 (93.4%) | 411 (93.4%) |
| M_constrained | non_think | pooled | V5 | 400 | 0 (0.0%) | 12 (3.0%) | 26 (6.5%) |
| M_constrained | non_think | pooled | V6 | 400 | 0 (0.0%) | 338 (84.5%) | 338 (84.5%) |
| M_constrained | non_think | pooled | benign | 1600 | 0 (0.0%) | 1553 (97.1%) | 1555 (97.2%) |
| M_constrained | think_high | pooled | V1 | 320 | 0 (0.0%) | 249 (77.8%) | 249 (77.8%) |
| M_constrained | think_high | pooled | V2 | 400 | 0 (0.0%) | 261 (65.2%) | 265 (66.2%) |
| M_constrained | think_high | pooled | V3 | 440 | 0 (0.0%) | 440 (100.0%) | 440 (100.0%) |
| M_constrained | think_high | pooled | V4 | 440 | 0 (0.0%) | 436 (99.1%) | 436 (99.1%) |
| M_constrained | think_high | pooled | V5 | 400 | 0 (0.0%) | 78 (19.5%) | 91 (22.8%) |
| M_constrained | think_high | pooled | V6 | 400 | 0 (0.0%) | 365 (91.2%) | 365 (91.2%) |
| M_constrained | think_high | pooled | benign | 1600 | 0 (0.0%) | 1591 (99.4%) | 1591 (99.4%) |
| M_free | non_think | pooled | V1 | 320 | 0 (0.0%) | 251 (78.4%) | 251 (78.4%) |
| M_free | non_think | pooled | V2 | 400 | 0 (0.0%) | 266 (66.5%) | 270 (67.5%) |
| M_free | non_think | pooled | V3 | 440 | 0 (0.0%) | 440 (100.0%) | 440 (100.0%) |
| M_free | non_think | pooled | V4 | 440 | 0 (0.0%) | 430 (97.7%) | 430 (97.7%) |
| M_free | non_think | pooled | V5 | 400 | 0 (0.0%) | 16 (4.0%) | 30 (7.5%) |
| M_free | non_think | pooled | V6 | 400 | 0 (0.0%) | 343 (85.8%) | 343 (85.8%) |
| M_free | non_think | pooled | benign | 1600 | 0 (0.0%) | 1564 (97.8%) | 1566 (97.9%) |
| M_free | think_high | pooled | V1 | 320 | 0 (0.0%) | 246 (76.9%) | 246 (76.9%) |
| M_free | think_high | pooled | V2 | 400 | 0 (0.0%) | 255 (63.7%) | 259 (64.8%) |
| M_free | think_high | pooled | V3 | 440 | 0 (0.0%) | 438 (99.5%) | 438 (99.5%) |
| M_free | think_high | pooled | V4 | 440 | 0 (0.0%) | 436 (99.1%) | 436 (99.1%) |
| M_free | think_high | pooled | V5 | 400 | 0 (0.0%) | 104 (26.0%) | 115 (28.7%) |
| M_free | think_high | pooled | V6 | 400 | 0 (0.0%) | 354 (88.5%) | 354 (88.5%) |
| M_free | think_high | pooled | benign | 1600 | 0 (0.0%) | 1592 (99.5%) | 1592 (99.5%) |

### Benign twins: the false-block rate

| mode | thinking | repeat | benign items | UNGUARDED false blocks | G_FEAS false blocks | G_CERT false blocks |
|---|---|---|---|---|---|---|
| M_constrained | non_think | r0 | 800 | 0 (0.0%) | 776 (97.0%) | 777 (97.1%) |
| M_constrained | non_think | r1 | 800 | 0 (0.0%) | 777 (97.1%) | 778 (97.2%) |
| M_constrained | think_high | r0 | 800 | 0 (0.0%) | 797 (99.6%) | 797 (99.6%) |
| M_constrained | think_high | r1 | 800 | 0 (0.0%) | 794 (99.2%) | 794 (99.2%) |
| M_free | non_think | r0 | 800 | 0 (0.0%) | 782 (97.8%) | 783 (97.9%) |
| M_free | non_think | r1 | 800 | 0 (0.0%) | 782 (97.8%) | 783 (97.9%) |
| M_free | think_high | r0 | 800 | 0 (0.0%) | 796 (99.5%) | 796 (99.5%) |
| M_free | think_high | r1 | 800 | 0 (0.0%) | 796 (99.5%) | 796 (99.5%) |
| M_constrained | non_think | pooled | 1600 | 0 (0.0%) | 1553 (97.1%) | 1555 (97.2%) |
| M_constrained | think_high | pooled | 1600 | 0 (0.0%) | 1591 (99.4%) | 1591 (99.4%) |
| M_free | non_think | pooled | 1600 | 0 (0.0%) | 1564 (97.8%) | 1566 (97.9%) |
| M_free | think_high | pooled | 1600 | 0 (0.0%) | 1592 (99.5%) | 1592 (99.5%) |

## The E1 headline: G_FEAS passes it, G_CERT blocks it

The count the suite acceptance gate turned on, per class: proposals the feasibility stage lets through and the certified stage refuses.

| mode | thinking | repeat | class | items | G_FEAS passes | G_CERT blocks | separated | share |
|---|---|---|---|---|---|---|---|---|
| M_constrained | non_think | r0 | V1 | 160 | 41 | 119 | 0 | 0.0% |
| M_constrained | non_think | r0 | V2 | 200 | 79 | 124 | 3 | 1.5% |
| M_constrained | non_think | r0 | V3 | 220 | 1 | 219 | 0 | 0.0% |
| M_constrained | non_think | r0 | V4 | 220 | 15 | 205 | 0 | 0.0% |
| M_constrained | non_think | r0 | V5 | 200 | 194 | 13 | 7 | 3.5% |
| M_constrained | non_think | r0 | V6 | 200 | 31 | 169 | 0 | 0.0% |
| M_constrained | non_think | r0 | benign | 800 | 24 | 777 | 1 | 0.1% |
| M_constrained | non_think | r1 | V1 | 160 | 41 | 119 | 0 | 0.0% |
| M_constrained | non_think | r1 | V2 | 200 | 79 | 124 | 3 | 1.5% |
| M_constrained | non_think | r1 | V3 | 220 | 2 | 219 | 1 | 0.5% |
| M_constrained | non_think | r1 | V4 | 220 | 14 | 206 | 0 | 0.0% |
| M_constrained | non_think | r1 | V5 | 200 | 194 | 13 | 7 | 3.5% |
| M_constrained | non_think | r1 | V6 | 200 | 31 | 169 | 0 | 0.0% |
| M_constrained | non_think | r1 | benign | 800 | 23 | 778 | 1 | 0.1% |
| M_constrained | think_high | r0 | V1 | 160 | 38 | 122 | 0 | 0.0% |
| M_constrained | think_high | r0 | V2 | 200 | 70 | 132 | 2 | 1.0% |
| M_constrained | think_high | r0 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_constrained | think_high | r0 | V4 | 220 | 2 | 218 | 0 | 0.0% |
| M_constrained | think_high | r0 | V5 | 200 | 161 | 45 | 6 | 3.0% |
| M_constrained | think_high | r0 | V6 | 200 | 18 | 182 | 0 | 0.0% |
| M_constrained | think_high | r0 | benign | 800 | 3 | 797 | 0 | 0.0% |
| M_constrained | think_high | r1 | V1 | 160 | 33 | 127 | 0 | 0.0% |
| M_constrained | think_high | r1 | V2 | 200 | 69 | 133 | 2 | 1.0% |
| M_constrained | think_high | r1 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_constrained | think_high | r1 | V4 | 220 | 2 | 218 | 0 | 0.0% |
| M_constrained | think_high | r1 | V5 | 200 | 161 | 46 | 7 | 3.5% |
| M_constrained | think_high | r1 | V6 | 200 | 17 | 183 | 0 | 0.0% |
| M_constrained | think_high | r1 | benign | 800 | 6 | 794 | 0 | 0.0% |
| M_free | non_think | r0 | V1 | 160 | 35 | 125 | 0 | 0.0% |
| M_free | non_think | r0 | V2 | 200 | 67 | 135 | 2 | 1.0% |
| M_free | non_think | r0 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | non_think | r0 | V4 | 220 | 5 | 215 | 0 | 0.0% |
| M_free | non_think | r0 | V5 | 200 | 192 | 15 | 7 | 3.5% |
| M_free | non_think | r0 | V6 | 200 | 29 | 171 | 0 | 0.0% |
| M_free | non_think | r0 | benign | 800 | 18 | 783 | 1 | 0.1% |
| M_free | non_think | r1 | V1 | 160 | 34 | 126 | 0 | 0.0% |
| M_free | non_think | r1 | V2 | 200 | 67 | 135 | 2 | 1.0% |
| M_free | non_think | r1 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | non_think | r1 | V4 | 220 | 5 | 215 | 0 | 0.0% |
| M_free | non_think | r1 | V5 | 200 | 192 | 15 | 7 | 3.5% |
| M_free | non_think | r1 | V6 | 200 | 28 | 172 | 0 | 0.0% |
| M_free | non_think | r1 | benign | 800 | 18 | 783 | 1 | 0.1% |
| M_free | think_high | r0 | V1 | 160 | 36 | 124 | 0 | 0.0% |
| M_free | think_high | r0 | V2 | 200 | 71 | 131 | 2 | 1.0% |
| M_free | think_high | r0 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | think_high | r0 | V4 | 220 | 2 | 218 | 0 | 0.0% |
| M_free | think_high | r0 | V5 | 200 | 150 | 55 | 5 | 2.5% |
| M_free | think_high | r0 | V6 | 200 | 26 | 174 | 0 | 0.0% |
| M_free | think_high | r0 | benign | 800 | 4 | 796 | 0 | 0.0% |
| M_free | think_high | r1 | V1 | 160 | 38 | 122 | 0 | 0.0% |
| M_free | think_high | r1 | V2 | 200 | 74 | 128 | 2 | 1.0% |
| M_free | think_high | r1 | V3 | 220 | 2 | 218 | 0 | 0.0% |
| M_free | think_high | r1 | V4 | 220 | 2 | 218 | 0 | 0.0% |
| M_free | think_high | r1 | V5 | 200 | 146 | 60 | 6 | 3.0% |
| M_free | think_high | r1 | V6 | 200 | 20 | 180 | 0 | 0.0% |
| M_free | think_high | r1 | benign | 800 | 4 | 796 | 0 | 0.0% |
| M_constrained | non_think | pooled | V1 | 320 | 82 | 238 | 0 | 0.0% |
| M_constrained | non_think | pooled | V2 | 400 | 158 | 248 | 6 | 1.5% |
| M_constrained | non_think | pooled | V3 | 440 | 3 | 438 | 1 | 0.2% |
| M_constrained | non_think | pooled | V4 | 440 | 29 | 411 | 0 | 0.0% |
| M_constrained | non_think | pooled | V5 | 400 | 388 | 26 | 14 | 3.5% |
| M_constrained | non_think | pooled | V6 | 400 | 62 | 338 | 0 | 0.0% |
| M_constrained | non_think | pooled | benign | 1600 | 47 | 1555 | 2 | 0.1% |
| M_constrained | think_high | pooled | V1 | 320 | 71 | 249 | 0 | 0.0% |
| M_constrained | think_high | pooled | V2 | 400 | 139 | 265 | 4 | 1.0% |
| M_constrained | think_high | pooled | V3 | 440 | 0 | 440 | 0 | 0.0% |
| M_constrained | think_high | pooled | V4 | 440 | 4 | 436 | 0 | 0.0% |
| M_constrained | think_high | pooled | V5 | 400 | 322 | 91 | 13 | 3.2% |
| M_constrained | think_high | pooled | V6 | 400 | 35 | 365 | 0 | 0.0% |
| M_constrained | think_high | pooled | benign | 1600 | 9 | 1591 | 0 | 0.0% |
| M_free | non_think | pooled | V1 | 320 | 69 | 251 | 0 | 0.0% |
| M_free | non_think | pooled | V2 | 400 | 134 | 270 | 4 | 1.0% |
| M_free | non_think | pooled | V3 | 440 | 0 | 440 | 0 | 0.0% |
| M_free | non_think | pooled | V4 | 440 | 10 | 430 | 0 | 0.0% |
| M_free | non_think | pooled | V5 | 400 | 384 | 30 | 14 | 3.5% |
| M_free | non_think | pooled | V6 | 400 | 57 | 343 | 0 | 0.0% |
| M_free | non_think | pooled | benign | 1600 | 36 | 1566 | 2 | 0.1% |
| M_free | think_high | pooled | V1 | 320 | 74 | 246 | 0 | 0.0% |
| M_free | think_high | pooled | V2 | 400 | 145 | 259 | 4 | 1.0% |
| M_free | think_high | pooled | V3 | 440 | 2 | 438 | 0 | 0.0% |
| M_free | think_high | pooled | V4 | 440 | 4 | 436 | 0 | 0.0% |
| M_free | think_high | pooled | V5 | 400 | 296 | 115 | 11 | 2.8% |
| M_free | think_high | pooled | V6 | 400 | 46 | 354 | 0 | 0.0% |
| M_free | think_high | pooled | benign | 1600 | 8 | 1592 | 0 | 0.0% |

## Translation accuracy on the benign items

Matched against `gold_ops` with the gate's own canonicalization (`canon_ops` / `match_kind`): *exact* is the same operations in the same order, *semantic* is the same set. Measured on the operations the strict parse produced, so a wrong-shape output counts as no match.

| mode | thinking | repeat | benign items | parsed | exact | semantic (incl. exact) |
|---|---|---|---|---|---|---|
| M_constrained | non_think | r0 | 800 | 800 (100.0%) | 0 (0.0%) | 0 (0.0%) |
| M_constrained | non_think | r1 | 800 | 800 (100.0%) | 0 (0.0%) | 0 (0.0%) |
| M_constrained | think_high | r0 | 800 | 795 (99.4%) | 0 (0.0%) | 0 (0.0%) |
| M_constrained | think_high | r1 | 800 | 793 (99.1%) | 0 (0.0%) | 0 (0.0%) |
| M_free | non_think | r0 | 800 | 800 (100.0%) | 0 (0.0%) | 0 (0.0%) |
| M_free | non_think | r1 | 800 | 800 (100.0%) | 0 (0.0%) | 0 (0.0%) |
| M_free | think_high | r0 | 800 | 797 (99.6%) | 0 (0.0%) | 0 (0.0%) |
| M_free | think_high | r1 | 800 | 796 (99.5%) | 0 (0.0%) | 0 (0.0%) |
| M_constrained | non_think | pooled | 1600 | 1600 (100.0%) | 0 (0.0%) | 0 (0.0%) |
| M_constrained | think_high | pooled | 1600 | 1588 (99.2%) | 0 (0.0%) | 0 (0.0%) |
| M_free | non_think | pooled | 1600 | 1600 (100.0%) | 0 (0.0%) | 0 (0.0%) |
| M_free | think_high | pooled | 1600 | 1593 (99.6%) | 0 (0.0%) | 0 (0.0%) |

## Constraint tax: what the enforcement mode buys

Classified from the guard's own stage-1 findings under G_CERT (strict parse, no repair): `malformed_json` is *JSON invalid*, `schema_invalid` is *parses but wrong shape* (a wrong `op` key, a missing `operations` envelope, an out-of-enum value), and everything else is *schema valid*. A dangling order id or an unstaffed trade is an instance-legality violation, not a shape failure, and leaves the row schema-valid. A completion cut off at max_tokens is JSON-invalid in either mode: the grammar constrains which tokens may be emitted, not how many, so a truncated proposal is a valid prefix and not a valid document (the truncation count is in the latency and tokens table).

| mode | thinking | repeat | rows | JSON invalid | parses, wrong shape | schema valid | UNGUARDED applied 0 operations |
|---|---|---|---|---|---|---|---|
| M_constrained | non_think | r0 | 2000 | 0 (0.0%) | 1615 (80.8%) | 385 (19.2%) | 0 (0.0%) | 2000 (100.0%) |
| M_constrained | non_think | r1 | 2000 | 0 (0.0%) | 1616 (80.8%) | 384 (19.2%) | 0 (0.0%) | 2000 (100.0%) |
| M_constrained | think_high | r0 | 2000 | 41 (2.1%) | 1667 (83.4%) | 292 (14.6%) | 0 (0.0%) | 1953 (97.7%) |
| M_constrained | think_high | r1 | 2000 | 35 (1.8%) | 1677 (83.9%) | 288 (14.4%) | 0 (0.0%) | 1958 (97.9%) |
| M_free | non_think | r0 | 2000 | 0 (0.0%) | 1654 (82.7%) | 346 (17.3%) | 0 (0.0%) | 1996 (99.8%) |
| M_free | non_think | r1 | 2000 | 0 (0.0%) | 1656 (82.8%) | 344 (17.2%) | 0 (0.0%) | 1996 (99.8%) |
| M_free | think_high | r0 | 2000 | 23 (1.1%) | 1688 (84.4%) | 289 (14.4%) | 0 (0.0%) | 1977 (98.9%) |
| M_free | think_high | r1 | 2000 | 22 (1.1%) | 1692 (84.6%) | 286 (14.3%) | 0 (0.0%) | 1980 (99.0%) |
| M_constrained | non_think | pooled | 4000 | 0 (0.0%) | 3231 (80.8%) | 769 (19.2%) | 0 (0.0%) | 4000 (100.0%) |
| M_constrained | think_high | pooled | 4000 | 76 (1.9%) | 3344 (83.6%) | 580 (14.5%) | 0 (0.0%) | 3911 (97.8%) |
| M_free | non_think | pooled | 4000 | 0 (0.0%) | 3310 (82.8%) | 690 (17.2%) | 0 (0.0%) | 3992 (99.8%) |
| M_free | think_high | pooled | 4000 | 45 (1.1%) | 3380 (84.5%) | 575 (14.4%) | 0 (0.0%) | 3957 (98.9%) |

The last column is what the tax costs when nothing gates: UNGUARDED drops the operations it cannot parse and applies whatever survives, so a wrong-shape proposal is executed as a no-op and the instruction is silently not carried out. It is an `applied_uncertified` outcome, not a refusal.

### Which shape failure, among the wrong-shape rows

| mode | thinking | repeat | wrong-shape rows | missing_field | not_object |
|---|---|---|---|---|---|
| M_constrained | non_think | r0 | 1615 | 1615 | 0 |
| M_constrained | non_think | r1 | 1616 | 1616 | 0 |
| M_constrained | think_high | r0 | 1667 | 1667 | 0 |
| M_constrained | think_high | r1 | 1677 | 1676 | 1 |
| M_free | non_think | r0 | 1654 | 1654 | 0 |
| M_free | non_think | r1 | 1656 | 1656 | 0 |
| M_free | think_high | r0 | 1688 | 1688 | 0 |
| M_free | think_high | r1 | 1692 | 1692 | 0 |
| M_constrained | non_think | pooled | 3231 | 3231 | 0 |
| M_constrained | think_high | pooled | 3344 | 3343 | 1 |
| M_free | non_think | pooled | 3310 | 3310 | 0 |
| M_free | think_high | pooled | 3380 | 3380 | 0 |

Rows are counted once per distinct `schema_invalid` subcode they carry, so a row with two kinds of shape failure appears in two columns.

## Certified gap of what was executed (Tier 2, adjusted instance)

| mode | thinking | repeat | class | certificates | median gap | p90 | max |
|---|---|---|---|---|---|---|---|
| M_constrained | non_think | r0 | V1 | 41 | 0.0036 | 0.0560 | 0.1238 |
| M_constrained | non_think | r0 | V2 | 79 | 0.0109 | 0.0692 | 0.2867 |
| M_constrained | non_think | r0 | V3 | 1 | 0.0480 | 0.0480 | 0.0480 |
| M_constrained | non_think | r0 | V4 | 15 | 0.0000 | 0.0016 | 0.0172 |
| M_constrained | non_think | r0 | V5 | 194 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | non_think | r0 | V6 | 31 | 0.0101 | 0.0560 | 0.1061 |
| M_constrained | non_think | r0 | benign | 24 | 0.0109 | 0.1061 | 0.2266 |
| M_constrained | non_think | r1 | V1 | 41 | 0.0036 | 0.0560 | 0.1238 |
| M_constrained | non_think | r1 | V2 | 79 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | non_think | r1 | V3 | 2 | 0.0480 | 0.2867 | 0.2867 |
| M_constrained | non_think | r1 | V4 | 14 | 0.0000 | 0.0016 | 0.0172 |
| M_constrained | non_think | r1 | V5 | 194 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | non_think | r1 | V6 | 31 | 0.0101 | 0.0560 | 0.1061 |
| M_constrained | non_think | r1 | benign | 23 | 0.0109 | 0.1061 | 0.2266 |
| M_constrained | think_high | r0 | V1 | 38 | 0.0015 | 0.0426 | 0.1238 |
| M_constrained | think_high | r0 | V2 | 70 | 0.0163 | 0.0656 | 0.2867 |
| M_constrained | think_high | r0 | V3 | 0 | - | - | - |
| M_constrained | think_high | r0 | V4 | 2 | 0.0000 | 0.0000 | 0.0000 |
| M_constrained | think_high | r0 | V5 | 161 | 0.0163 | 0.0692 | 0.2867 |
| M_constrained | think_high | r0 | V6 | 18 | 0.0123 | 0.0903 | 0.1061 |
| M_constrained | think_high | r0 | benign | 3 | 0.0560 | 0.1238 | 0.1238 |
| M_constrained | think_high | r1 | V1 | 33 | 0.0027 | 0.0483 | 0.1238 |
| M_constrained | think_high | r1 | V2 | 69 | 0.0123 | 0.1061 | 0.2867 |
| M_constrained | think_high | r1 | V3 | 0 | - | - | - |
| M_constrained | think_high | r1 | V4 | 2 | 0.0000 | 0.0123 | 0.0123 |
| M_constrained | think_high | r1 | V5 | 161 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | think_high | r1 | V6 | 17 | 0.0170 | 0.0508 | 0.0903 |
| M_constrained | think_high | r1 | benign | 6 | 0.0015 | 0.1238 | 0.1238 |
| M_free | non_think | r0 | V1 | 35 | 0.0036 | 0.0560 | 0.1238 |
| M_free | non_think | r0 | V2 | 67 | 0.0123 | 0.0692 | 0.2867 |
| M_free | non_think | r0 | V3 | 0 | - | - | - |
| M_free | non_think | r0 | V4 | 5 | 0.0015 | 0.0616 | 0.0616 |
| M_free | non_think | r0 | V5 | 192 | 0.0123 | 0.0903 | 0.2867 |
| M_free | non_think | r0 | V6 | 29 | 0.0101 | 0.0616 | 0.1061 |
| M_free | non_think | r0 | benign | 18 | 0.0123 | 0.1238 | 0.2266 |
| M_free | non_think | r1 | V1 | 34 | 0.0036 | 0.0560 | 0.1238 |
| M_free | non_think | r1 | V2 | 67 | 0.0123 | 0.0692 | 0.2867 |
| M_free | non_think | r1 | V3 | 0 | - | - | - |
| M_free | non_think | r1 | V4 | 5 | 0.0000 | 0.0016 | 0.0016 |
| M_free | non_think | r1 | V5 | 192 | 0.0123 | 0.0903 | 0.2867 |
| M_free | non_think | r1 | V6 | 28 | 0.0101 | 0.0616 | 0.1061 |
| M_free | non_think | r1 | benign | 18 | 0.0123 | 0.1238 | 0.2266 |
| M_free | think_high | r0 | V1 | 36 | 0.0015 | 0.0483 | 0.1238 |
| M_free | think_high | r0 | V2 | 71 | 0.0123 | 0.0692 | 0.2867 |
| M_free | think_high | r0 | V3 | 0 | - | - | - |
| M_free | think_high | r0 | V4 | 2 | 0.0000 | 0.0055 | 0.0055 |
| M_free | think_high | r0 | V5 | 150 | 0.0123 | 0.0692 | 0.2867 |
| M_free | think_high | r0 | V6 | 26 | 0.0123 | 0.0616 | 0.0903 |
| M_free | think_high | r0 | benign | 4 | 0.0015 | 0.0560 | 0.0560 |
| M_free | think_high | r1 | V1 | 38 | 0.0004 | 0.0426 | 0.1238 |
| M_free | think_high | r1 | V2 | 74 | 0.0109 | 0.0656 | 0.2867 |
| M_free | think_high | r1 | V3 | 2 | 0.0000 | 0.0000 | 0.0000 |
| M_free | think_high | r1 | V4 | 2 | 0.0508 | 0.0616 | 0.0616 |
| M_free | think_high | r1 | V5 | 146 | 0.0163 | 0.0903 | 0.2867 |
| M_free | think_high | r1 | V6 | 20 | 0.0101 | 0.0656 | 0.1238 |
| M_free | think_high | r1 | benign | 4 | 0.0015 | 0.0616 | 0.0616 |
| M_constrained | non_think | pooled | V1 | 82 | 0.0036 | 0.0560 | 0.1238 |
| M_constrained | non_think | pooled | V2 | 158 | 0.0109 | 0.0692 | 0.2867 |
| M_constrained | non_think | pooled | V3 | 3 | 0.0480 | 0.2867 | 0.2867 |
| M_constrained | non_think | pooled | V4 | 29 | 0.0000 | 0.0016 | 0.0172 |
| M_constrained | non_think | pooled | V5 | 388 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | non_think | pooled | V6 | 62 | 0.0101 | 0.0560 | 0.1061 |
| M_constrained | non_think | pooled | benign | 47 | 0.0109 | 0.1061 | 0.2266 |
| M_constrained | think_high | pooled | V1 | 71 | 0.0017 | 0.0426 | 0.1238 |
| M_constrained | think_high | pooled | V2 | 139 | 0.0163 | 0.0903 | 0.2867 |
| M_constrained | think_high | pooled | V3 | 0 | - | - | - |
| M_constrained | think_high | pooled | V4 | 4 | 0.0000 | 0.0123 | 0.0123 |
| M_constrained | think_high | pooled | V5 | 322 | 0.0163 | 0.0692 | 0.2867 |
| M_constrained | think_high | pooled | V6 | 35 | 0.0170 | 0.0560 | 0.1061 |
| M_constrained | think_high | pooled | benign | 9 | 0.0172 | 0.1238 | 0.1238 |
| M_free | non_think | pooled | V1 | 69 | 0.0036 | 0.0560 | 0.1238 |
| M_free | non_think | pooled | V2 | 134 | 0.0123 | 0.0692 | 0.2867 |
| M_free | non_think | pooled | V3 | 0 | - | - | - |
| M_free | non_think | pooled | V4 | 10 | 0.0000 | 0.0016 | 0.0616 |
| M_free | non_think | pooled | V5 | 384 | 0.0123 | 0.0903 | 0.2867 |
| M_free | non_think | pooled | V6 | 57 | 0.0101 | 0.0616 | 0.1061 |
| M_free | non_think | pooled | benign | 36 | 0.0123 | 0.1238 | 0.2266 |
| M_free | think_high | pooled | V1 | 74 | 0.0015 | 0.0426 | 0.1238 |
| M_free | think_high | pooled | V2 | 145 | 0.0123 | 0.0692 | 0.2867 |
| M_free | think_high | pooled | V3 | 2 | 0.0000 | 0.0000 | 0.0000 |
| M_free | think_high | pooled | V4 | 4 | 0.0055 | 0.0616 | 0.0616 |
| M_free | think_high | pooled | V5 | 296 | 0.0123 | 0.0903 | 0.2867 |
| M_free | think_high | pooled | V6 | 46 | 0.0101 | 0.0656 | 0.1238 |
| M_free | think_high | pooled | benign | 8 | 0.0015 | 0.0616 | 0.0616 |

## Verdict-level repeat agreement

Two repeats of the same item at temperature 0 can differ in text (batch-numeric nondeterminism in the engine). A text-identical pair is a trivially identical verdict, because the guard is deterministic; the question is how many of the text-differing rows change the G_CERT outcome.

| mode | thinking | pair | items | text identical | text differing | G_CERT terminal differs | of which text-differing | verdict fingerprint differs |
|---|---|---|---|---|---|---|---|---|
| M_constrained | non_think | r0r1 | 2000 | 1843 | 157 | 9 | 9 | 73 |
| M_constrained | think_high | r0r1 | 2000 | 848 | 1152 | 110 | 110 | 1073 |
| M_free | non_think | r0r1 | 2000 | 1825 | 175 | 12 | 12 | 162 |
| M_free | think_high | r0r1 | 2000 | 816 | 1184 | 127 | 127 | 1128 |

## Latency and tokens

| mode | thinking | repeat | rows | median latency ms | rows with latency | median completion tokens | median prompt tokens | median reasoning tokens | finish_reason = length |
|---|---|---|---|---|---|---|---|---|---|
| M_constrained | non_think | r0 | 2000 | 1460 | 2000 | 34 | 1207 | - | 0 |
| M_constrained | non_think | r1 | 2000 | 1294 | 2000 | 34 | 1207 | - | 0 |
| M_constrained | think_high | r0 | 2000 | 13150 | 2000 | 870 | 1207 | 839 | 39 |
| M_constrained | think_high | r1 | 2000 | 14841 | 2000 | 915 | 1207 | 878 | 32 |
| M_free | non_think | r0 | 2000 | 1465 | 2000 | 29 | 1187 | - | 0 |
| M_free | non_think | r1 | 2000 | 1352 | 2000 | 29 | 1187 | - | 0 |
| M_free | think_high | r0 | 2000 | 10834 | 2000 | 814 | 1187 | 779 | 19 |
| M_free | think_high | r1 | 2000 | 11196 | 2000 | 816 | 1187 | 783 | 13 |
| M_constrained | non_think | pooled | 4000 | 1359 | 4000 | 34 | 1207 | - | 0 |
| M_constrained | think_high | pooled | 4000 | 13937 | 4000 | 892 | 1207 | 858 | 71 |
| M_free | non_think | pooled | 4000 | 1408 | 4000 | 29 | 1187 | - | 0 |
| M_free | think_high | pooled | 4000 | 11057 | 4000 | 815 | 1187 | 782 | 32 |

## Instrument faults, kept separate

| mode | thinking | repeat | rows | UNGUARDED infra rows | G_FEAS infra rows | G_CERT infra rows |
|---|---|---|---|---|---|---|
| M_constrained | non_think | r0 | 2000 | 0 | 0 | 0 |
| M_constrained | non_think | r1 | 2000 | 0 | 0 | 0 |
| M_constrained | think_high | r0 | 2000 | 0 | 0 | 0 |
| M_constrained | think_high | r1 | 2000 | 0 | 0 | 0 |
| M_free | non_think | r0 | 2000 | 0 | 0 | 0 |
| M_free | non_think | r1 | 2000 | 0 | 0 | 0 |
| M_free | think_high | r0 | 2000 | 0 | 0 | 0 |
| M_free | think_high | r1 | 2000 | 0 | 0 | 0 |
| M_constrained | non_think | pooled | 4000 | 0 | 0 | 0 |
| M_constrained | think_high | pooled | 4000 | 0 | 0 | 0 |
| M_free | non_think | pooled | 4000 | 0 | 0 | 0 |
| M_free | think_high | pooled | 4000 | 0 | 0 | 0 |

**Rows carrying an `infra_error` finding: 0 across the pooled groups.** These are dispatcher or certification faults of the instrument, never a guard decision, and they are excluded from every rate above.

## Sanity gates

| gate | measured | verdict |
|---|---|---|
| every row evaluated under all three configurations | 16000 rows x [3] verdicts | PASS |
| UNGUARDED never blocks (it has no gating stage; its terminals are applied_uncertified and execution_failed) | 0 blocked; terminals {'applied_uncertified': 15890, 'execution_failed': 110} | PASS |
| G_CERT blocked_qual > 0 on V3 under M_constrained (suite gate: 182/220 blocked on its 880-item subset; applies to shape-enforcing arms only — a json_object arm blocks V3 at the schema stage, which is the enforcement-axis finding) | 220 V3 items per repeat; blocked_qual {'r0': 0, 'r1': 0}; all G_CERT blocks {'r0': '220/220', 'r1': '220/220'} | n/a (too few rows of this kind in the log) |
| M_free off-shape (json_invalid + wrong_shape) dominates the EMITTED documents (model-level refusals shown beside it; proves the free arm ran unenforced) | deepseek: 85.6% of emitted (0.0% refused) | PASS |
| M_constrained emits no malformed or wrong-shape JSON, truncations and model-level refusals aside (the grammar or server schema guarantees the shape of what IS emitted, not that anything is; applies to shape-enforcing arms only — a json_object arm's off-shape share is the enforcement-axis finding) | 6576 of 8000 rows off-shape; 71 truncated at max_tokens; 70 model refusals/empty | n/a (too few rows of this kind in the log) |

Files: `proposals.jsonl` (canonical log, G_CERT verdicts), `verdicts_UNGUARDED.jsonl`, `verdicts_G_FEAS.jsonl`, `verdicts_G_CERT.jsonl`, `summary.json`, `run_meta.json`.