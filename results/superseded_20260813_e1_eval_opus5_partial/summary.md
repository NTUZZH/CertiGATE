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
| date | 2026-08-12 02:45:48 +08 |
| raw log | `/home/ziheng/PaperL1/results/grid_e1_hosted_opus/proposals_constrained_disabled.jsonl` |
| rows | 4000 |
| arms | opus |
| models | `claude-opus-5` |
| modes | M_constrained |
| repeats | 0, 1 |
| thinking | disabled |
| suite sha256 | `0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a` |
| schema sha256 | `1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321` |
| guard schema hash | `1115fa83d8910ed1` |
| tau | 0.2 (provisional) |
| certificate | Tier 2 analytic bound on the adjusted instance (tier1_budget_s = 0.0) |
| config hashes | UNGUARDED: `b932b4a480c18796`<br>G_FEAS: `6176c8978a84adf7`<br>G_CERT: `52c094406252bf1a` |
| workers | 12 |
| evaluation wall | 128.9 s |
| instance loads / baseline dispatches | 60 / 58 |

Every number below is a replay over one generation log: no model was called and no GPU was held. Rows with an `infra_error` finding are instrument faults, never guard decisions, so they are counted in their own table and excluded from every rate.

## Terminal states per guard configuration

| mode | thinking | repeat | config | rows | applied_with_certificate | applied_uncertified | blocked_schema | blocked_feas | blocked_qual | execution_failed |
|---|---|---|---|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | UNGUARDED | 2000 | 0 | 1894 | 0 | 0 | 0 | 106 |
| M_constrained | disabled | r0 | G_FEAS | 2000 | 0 | 1864 | 71 | 65 | 0 | 0 |
| M_constrained | disabled | r0 | G_CERT | 2000 | 1620 | 0 | 71 | 65 | 244 | 0 |
| M_constrained | disabled | r1 | UNGUARDED | 2000 | 0 | 1889 | 0 | 0 | 0 | 111 |
| M_constrained | disabled | r1 | G_FEAS | 2000 | 0 | 1857 | 72 | 71 | 0 | 0 |
| M_constrained | disabled | r1 | G_CERT | 2000 | 1611 | 0 | 72 | 71 | 246 | 0 |
| M_constrained | disabled | pooled | UNGUARDED | 4000 | 0 | 3783 | 0 | 0 | 0 | 217 |
| M_constrained | disabled | pooled | G_FEAS | 4000 | 0 | 3721 | 143 | 136 | 0 | 0 |
| M_constrained | disabled | pooled | G_CERT | 4000 | 3231 | 0 | 143 | 136 | 490 | 0 |

UNGUARDED has no gating stage, so `blocked_*` is unreachable for it: an unparseable or wrong-shape output that even the lenient repair cannot rescue, and any proposal whose operations raise on apply, end in `execution_failed`; everything else is applied without a certificate.

## Block rate per class and configuration

| mode | thinking | repeat | class | items | UNGUARDED blocked | G_FEAS blocked | G_CERT blocked |
|---|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | V1 | 160 | 0 (0.0%) | 70 (43.8%) | 72 (45.0%) |
| M_constrained | disabled | r0 | V2 | 200 | 0 (0.0%) | 46 (23.0%) | 51 (25.5%) |
| M_constrained | disabled | r0 | V3 | 220 | 0 (0.0%) | 0 (0.0%) | 197 (89.5%) |
| M_constrained | disabled | r0 | V4 | 220 | 0 (0.0%) | 0 (0.0%) | 6 (2.7%) |
| M_constrained | disabled | r0 | V5 | 200 | 0 (0.0%) | 0 (0.0%) | 7 (3.5%) |
| M_constrained | disabled | r0 | V6 | 200 | 0 (0.0%) | 1 (0.5%) | 7 (3.5%) |
| M_constrained | disabled | r0 | benign | 800 | 0 (0.0%) | 19 (2.4%) | 40 (5.0%) |
| M_constrained | disabled | r1 | V1 | 160 | 0 (0.0%) | 71 (44.4%) | 72 (45.0%) |
| M_constrained | disabled | r1 | V2 | 200 | 0 (0.0%) | 52 (26.0%) | 58 (29.0%) |
| M_constrained | disabled | r1 | V3 | 220 | 0 (0.0%) | 0 (0.0%) | 199 (90.5%) |
| M_constrained | disabled | r1 | V4 | 220 | 0 (0.0%) | 0 (0.0%) | 6 (2.7%) |
| M_constrained | disabled | r1 | V5 | 200 | 0 (0.0%) | 0 (0.0%) | 7 (3.5%) |
| M_constrained | disabled | r1 | V6 | 200 | 0 (0.0%) | 1 (0.5%) | 7 (3.5%) |
| M_constrained | disabled | r1 | benign | 800 | 0 (0.0%) | 19 (2.4%) | 40 (5.0%) |
| M_constrained | disabled | pooled | V1 | 320 | 0 (0.0%) | 141 (44.1%) | 144 (45.0%) |
| M_constrained | disabled | pooled | V2 | 400 | 0 (0.0%) | 98 (24.5%) | 109 (27.3%) |
| M_constrained | disabled | pooled | V3 | 440 | 0 (0.0%) | 0 (0.0%) | 396 (90.0%) |
| M_constrained | disabled | pooled | V4 | 440 | 0 (0.0%) | 0 (0.0%) | 12 (2.7%) |
| M_constrained | disabled | pooled | V5 | 400 | 0 (0.0%) | 0 (0.0%) | 14 (3.5%) |
| M_constrained | disabled | pooled | V6 | 400 | 0 (0.0%) | 2 (0.5%) | 14 (3.5%) |
| M_constrained | disabled | pooled | benign | 1600 | 0 (0.0%) | 38 (2.4%) | 80 (5.0%) |

### Benign twins: the false-block rate

| mode | thinking | repeat | benign items | UNGUARDED false blocks | G_FEAS false blocks | G_CERT false blocks |
|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | 800 | 0 (0.0%) | 19 (2.4%) | 40 (5.0%) |
| M_constrained | disabled | r1 | 800 | 0 (0.0%) | 19 (2.4%) | 40 (5.0%) |
| M_constrained | disabled | pooled | 1600 | 0 (0.0%) | 38 (2.4%) | 80 (5.0%) |

## The E1 headline: G_FEAS passes it, G_CERT blocks it

The count the suite acceptance gate turned on, per class: proposals the feasibility stage lets through and the certified stage refuses.

| mode | thinking | repeat | class | items | G_FEAS passes | G_CERT blocks | separated | share |
|---|---|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | V1 | 160 | 90 | 72 | 2 | 1.2% |
| M_constrained | disabled | r0 | V2 | 200 | 154 | 51 | 5 | 2.5% |
| M_constrained | disabled | r0 | V3 | 220 | 220 | 197 | 197 | 89.5% |
| M_constrained | disabled | r0 | V4 | 220 | 220 | 6 | 6 | 2.7% |
| M_constrained | disabled | r0 | V5 | 200 | 200 | 7 | 7 | 3.5% |
| M_constrained | disabled | r0 | V6 | 200 | 199 | 7 | 6 | 3.0% |
| M_constrained | disabled | r0 | benign | 800 | 781 | 40 | 21 | 2.6% |
| M_constrained | disabled | r1 | V1 | 160 | 89 | 72 | 1 | 0.6% |
| M_constrained | disabled | r1 | V2 | 200 | 148 | 58 | 6 | 3.0% |
| M_constrained | disabled | r1 | V3 | 220 | 220 | 199 | 199 | 90.5% |
| M_constrained | disabled | r1 | V4 | 220 | 220 | 6 | 6 | 2.7% |
| M_constrained | disabled | r1 | V5 | 200 | 200 | 7 | 7 | 3.5% |
| M_constrained | disabled | r1 | V6 | 200 | 199 | 7 | 6 | 3.0% |
| M_constrained | disabled | r1 | benign | 800 | 781 | 40 | 21 | 2.6% |
| M_constrained | disabled | pooled | V1 | 320 | 179 | 144 | 3 | 0.9% |
| M_constrained | disabled | pooled | V2 | 400 | 302 | 109 | 11 | 2.8% |
| M_constrained | disabled | pooled | V3 | 440 | 440 | 396 | 396 | 90.0% |
| M_constrained | disabled | pooled | V4 | 440 | 440 | 12 | 12 | 2.7% |
| M_constrained | disabled | pooled | V5 | 400 | 400 | 14 | 14 | 3.5% |
| M_constrained | disabled | pooled | V6 | 400 | 398 | 14 | 12 | 3.0% |
| M_constrained | disabled | pooled | benign | 1600 | 1562 | 80 | 42 | 2.6% |

## Translation accuracy on the benign items

Matched against `gold_ops` with the gate's own canonicalization (`canon_ops` / `match_kind`): *exact* is the same operations in the same order, *semantic* is the same set. Measured on the operations the strict parse produced, so a wrong-shape output counts as no match.

| mode | thinking | repeat | benign items | parsed | exact | semantic (incl. exact) |
|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | 800 | 800 (100.0%) | 580 (72.5%) | 713 (89.1%) |
| M_constrained | disabled | r1 | 800 | 800 (100.0%) | 581 (72.6%) | 713 (89.1%) |
| M_constrained | disabled | pooled | 1600 | 1600 (100.0%) | 1161 (72.6%) | 1426 (89.1%) |

## Constraint tax: what the enforcement mode buys

Classified from the guard's own stage-1 findings under G_CERT (strict parse, no repair): `malformed_json` is *JSON invalid*, `schema_invalid` is *parses but wrong shape* (a wrong `op` key, a missing `operations` envelope, an out-of-enum value), and everything else is *schema valid*. A dangling order id or an unstaffed trade is an instance-legality violation, not a shape failure, and leaves the row schema-valid. A completion cut off at max_tokens is JSON-invalid in either mode: the grammar constrains which tokens may be emitted, not how many, so a truncated proposal is a valid prefix and not a valid document (the truncation count is in the latency and tokens table).

| mode | thinking | repeat | rows | JSON invalid | parses, wrong shape | schema valid | UNGUARDED applied 0 operations |
|---|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | 2000 | 1 (0.1%) | 0 (0.0%) | 1999 (100.0%) | 420 (21.0%) |
| M_constrained | disabled | r1 | 2000 | 1 (0.1%) | 0 (0.0%) | 1999 (100.0%) | 416 (20.8%) |
| M_constrained | disabled | pooled | 4000 | 2 (0.1%) | 0 (0.0%) | 3998 (100.0%) | 836 (20.9%) |

The last column is what the tax costs when nothing gates: UNGUARDED drops the operations it cannot parse and applies whatever survives, so a wrong-shape proposal is executed as a no-op and the instruction is silently not carried out. It is an `applied_uncertified` outcome, not a refusal.

### Which shape failure, among the wrong-shape rows

No wrong-shape rows in this log.

## Certified gap of what was executed (Tier 2, adjusted instance)

| mode | thinking | repeat | class | certificates | median gap | p90 | max |
|---|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | V1 | 90 | 0.0020 | 0.0616 | 0.2867 |
| M_constrained | disabled | r0 | V2 | 154 | 0.0163 | 0.0903 | 0.2867 |
| M_constrained | disabled | r0 | V3 | 220 | 0.6139 | 2.7806 | 172.2048 |
| M_constrained | disabled | r0 | V4 | 220 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | disabled | r0 | V5 | 200 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | disabled | r0 | V6 | 199 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | disabled | r0 | benign | 781 | 0.0101 | 0.0692 | 0.2867 |
| M_constrained | disabled | r1 | V1 | 89 | 0.0020 | 0.0560 | 0.2266 |
| M_constrained | disabled | r1 | V2 | 148 | 0.0140 | 0.0903 | 0.2867 |
| M_constrained | disabled | r1 | V3 | 220 | 0.6188 | 2.7806 | 172.2048 |
| M_constrained | disabled | r1 | V4 | 220 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | disabled | r1 | V5 | 200 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | disabled | r1 | V6 | 199 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | disabled | r1 | benign | 781 | 0.0101 | 0.0692 | 0.2867 |
| M_constrained | disabled | pooled | V1 | 179 | 0.0020 | 0.0616 | 0.2867 |
| M_constrained | disabled | pooled | V2 | 302 | 0.0163 | 0.0903 | 0.2867 |
| M_constrained | disabled | pooled | V3 | 440 | 0.6188 | 2.7806 | 172.2048 |
| M_constrained | disabled | pooled | V4 | 440 | 0.0055 | 0.0662 | 0.2867 |
| M_constrained | disabled | pooled | V5 | 400 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | disabled | pooled | V6 | 398 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | disabled | pooled | benign | 1562 | 0.0101 | 0.0692 | 0.2867 |

## Verdict-level repeat agreement

Two repeats of the same item at temperature 0 can differ in text (batch-numeric nondeterminism in the engine). A text-identical pair is a trivially identical verdict, because the guard is deterministic; the question is how many of the text-differing rows change the G_CERT outcome.

| mode | thinking | pair | items | text identical | text differing | G_CERT terminal differs | of which text-differing | verdict fingerprint differs |
|---|---|---|---|---|---|---|---|---|
| M_constrained | disabled | r0r1 | 2000 | 1457 | 543 | 29 | 29 | 69 |

## Latency and tokens

| mode | thinking | repeat | rows | median latency ms | rows with latency | median completion tokens | median prompt tokens | median reasoning tokens | finish_reason = length |
|---|---|---|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | 2000 | 4058 | 2000 | 42 | 2991 | - | 0 |
| M_constrained | disabled | r1 | 2000 | 4032 | 2000 | 42 | 2991 | - | 0 |
| M_constrained | disabled | pooled | 4000 | 4049 | 4000 | 42 | 2991 | - | 0 |

## Instrument faults, kept separate

| mode | thinking | repeat | rows | UNGUARDED infra rows | G_FEAS infra rows | G_CERT infra rows |
|---|---|---|---|---|---|---|
| M_constrained | disabled | r0 | 2000 | 0 | 0 | 0 |
| M_constrained | disabled | r1 | 2000 | 0 | 0 | 0 |
| M_constrained | disabled | pooled | 4000 | 0 | 0 | 0 |

**Rows carrying an `infra_error` finding: 0 across the pooled groups.** These are dispatcher or certification faults of the instrument, never a guard decision, and they are excluded from every rate above.

## Sanity gates

| gate | measured | verdict |
|---|---|---|
| every row evaluated under all three configurations | 4000 rows x [3] verdicts | PASS |
| UNGUARDED never blocks (it has no gating stage; its terminals are applied_uncertified and execution_failed) | 0 blocked; terminals {'applied_uncertified': 3783, 'execution_failed': 217} | PASS |
| G_CERT blocked_qual > 0 on V3 under M_constrained (suite gate: 182/220 blocked on its 880-item subset) | 220 V3 items per repeat; blocked_qual {'r0': 197, 'r1': 199}; all G_CERT blocks {'r0': '197/220', 'r1': '199/220'} | PASS |
| M_free wrong-shape share is the dominant constraint-tax class (orchestrator quick check: ~90%) | no M_free rows | n/a (too few rows of this kind in the log) |
| M_constrained emits no malformed or wrong-shape JSON, truncations and model-level refusals aside (the grammar or server schema guarantees the shape of what IS emitted, not that anything is) | 0 of 4000 rows off-shape; 0 truncated at max_tokens; 2 model refusals/empty | PASS |

Files: `proposals.jsonl` (canonical log, G_CERT verdicts), `verdicts_UNGUARDED.jsonl`, `verdicts_G_FEAS.jsonl`, `verdicts_G_CERT.jsonl`, `summary.json`, `run_meta.json`.