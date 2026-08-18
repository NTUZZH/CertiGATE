# E1 evaluation: sol

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
| date | 2026-08-16 13:40:47 +08 |
| raw log | `/home/ziheng/PaperL1/results/grid_e1_hosted_sol/proposals_raw.dedup.jsonl` |
| rows | 2000 |
| arms | sol |
| models | `gpt-5.6-sol` |
| modes | M_constrained |
| repeats | 0 |
| thinking | none |
| suite sha256 | `0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a` |
| schema sha256 | `1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321` |
| guard schema hash | `1115fa83d8910ed1` |
| tau | 0.2 (provisional) |
| certificate | Tier 2 analytic bound on the adjusted instance (tier1_budget_s = 0.0) |
| config hashes | UNGUARDED: `b932b4a480c18796`<br>G_FEAS: `6176c8978a84adf7`<br>G_CERT: `52c094406252bf1a` |
| workers | 4 |
| evaluation wall | 146.9 s |
| instance loads / baseline dispatches | 60 / 58 |

Every number below is a replay over one generation log: no model was called and no GPU was held. Rows with an `infra_error` finding are instrument faults, never guard decisions, so they are counted in their own table and excluded from every rate.

## Terminal states per guard configuration

| mode | thinking | repeat | config | rows | applied_with_certificate | applied_uncertified | blocked_schema | blocked_feas | blocked_qual | execution_failed |
|---|---|---|---|---|---|---|---|---|---|---|
| M_constrained | none | r0 | UNGUARDED | 2000 | 0 | 1871 | 0 | 0 | 0 | 129 |
| M_constrained | none | r0 | G_FEAS | 2000 | 0 | 1835 | 84 | 81 | 0 | 0 |
| M_constrained | none | r0 | G_CERT | 2000 | 1605 | 0 | 84 | 81 | 230 | 0 |
| M_constrained | none | pooled | UNGUARDED | 2000 | 0 | 1871 | 0 | 0 | 0 | 129 |
| M_constrained | none | pooled | G_FEAS | 2000 | 0 | 1835 | 84 | 81 | 0 | 0 |
| M_constrained | none | pooled | G_CERT | 2000 | 1605 | 0 | 84 | 81 | 230 | 0 |

UNGUARDED has no gating stage, so `blocked_*` is unreachable for it: an unparseable or wrong-shape output that even the lenient repair cannot rescue, and any proposal whose operations raise on apply, end in `execution_failed`; everything else is applied without a certificate.

## Block rate per class and configuration

| mode | thinking | repeat | class | items | UNGUARDED blocked | G_FEAS blocked | G_CERT blocked |
|---|---|---|---|---|---|---|---|
| M_constrained | none | r0 | V1 | 160 | 0 (0.0%) | 48 (30.0%) | 50 (31.2%) |
| M_constrained | none | r0 | V2 | 200 | 0 (0.0%) | 47 (23.5%) | 52 (26.0%) |
| M_constrained | none | r0 | V3 | 220 | 0 (0.0%) | 13 (5.9%) | 194 (88.2%) |
| M_constrained | none | r0 | V4 | 220 | 0 (0.0%) | 9 (4.1%) | 17 (7.7%) |
| M_constrained | none | r0 | V5 | 200 | 0 (0.0%) | 0 (0.0%) | 7 (3.5%) |
| M_constrained | none | r0 | V6 | 200 | 0 (0.0%) | 0 (0.0%) | 6 (3.0%) |
| M_constrained | none | r0 | benign | 800 | 0 (0.0%) | 48 (6.0%) | 69 (8.6%) |
| M_constrained | none | pooled | V1 | 160 | 0 (0.0%) | 48 (30.0%) | 50 (31.2%) |
| M_constrained | none | pooled | V2 | 200 | 0 (0.0%) | 47 (23.5%) | 52 (26.0%) |
| M_constrained | none | pooled | V3 | 220 | 0 (0.0%) | 13 (5.9%) | 194 (88.2%) |
| M_constrained | none | pooled | V4 | 220 | 0 (0.0%) | 9 (4.1%) | 17 (7.7%) |
| M_constrained | none | pooled | V5 | 200 | 0 (0.0%) | 0 (0.0%) | 7 (3.5%) |
| M_constrained | none | pooled | V6 | 200 | 0 (0.0%) | 0 (0.0%) | 6 (3.0%) |
| M_constrained | none | pooled | benign | 800 | 0 (0.0%) | 48 (6.0%) | 69 (8.6%) |

### Benign twins: the false-block rate

| mode | thinking | repeat | benign items | UNGUARDED false blocks | G_FEAS false blocks | G_CERT false blocks |
|---|---|---|---|---|---|---|
| M_constrained | none | r0 | 800 | 0 (0.0%) | 48 (6.0%) | 69 (8.6%) |
| M_constrained | none | pooled | 800 | 0 (0.0%) | 48 (6.0%) | 69 (8.6%) |

## The E1 headline: G_FEAS passes it, G_CERT blocks it

The count the suite acceptance gate turned on, per class: proposals the feasibility stage lets through and the certified stage refuses.

| mode | thinking | repeat | class | items | G_FEAS passes | G_CERT blocks | separated | share |
|---|---|---|---|---|---|---|---|---|
| M_constrained | none | r0 | V1 | 160 | 112 | 50 | 2 | 1.2% |
| M_constrained | none | r0 | V2 | 200 | 153 | 52 | 5 | 2.5% |
| M_constrained | none | r0 | V3 | 220 | 207 | 194 | 181 | 82.3% |
| M_constrained | none | r0 | V4 | 220 | 211 | 17 | 8 | 3.6% |
| M_constrained | none | r0 | V5 | 200 | 200 | 7 | 7 | 3.5% |
| M_constrained | none | r0 | V6 | 200 | 200 | 6 | 6 | 3.0% |
| M_constrained | none | r0 | benign | 800 | 752 | 69 | 21 | 2.6% |
| M_constrained | none | pooled | V1 | 160 | 112 | 50 | 2 | 1.2% |
| M_constrained | none | pooled | V2 | 200 | 153 | 52 | 5 | 2.5% |
| M_constrained | none | pooled | V3 | 220 | 207 | 194 | 181 | 82.3% |
| M_constrained | none | pooled | V4 | 220 | 211 | 17 | 8 | 3.6% |
| M_constrained | none | pooled | V5 | 200 | 200 | 7 | 7 | 3.5% |
| M_constrained | none | pooled | V6 | 200 | 200 | 6 | 6 | 3.0% |
| M_constrained | none | pooled | benign | 800 | 752 | 69 | 21 | 2.6% |

## Translation accuracy on the benign items

Matched against `gold_ops` with the gate's own canonicalization (`canon_ops` / `match_kind`): *exact* is the same operations in the same order, *semantic* is the same set. Measured on the operations the strict parse produced, so a wrong-shape output counts as no match.

| mode | thinking | repeat | benign items | parsed | exact | semantic (incl. exact) |
|---|---|---|---|---|---|---|
| M_constrained | none | r0 | 800 | 784 (98.0%) | 553 (69.1%) | 662 (82.8%) |
| M_constrained | none | pooled | 800 | 784 (98.0%) | 553 (69.1%) | 662 (82.8%) |

## Constraint tax: what the enforcement mode buys

Classified from the guard's own stage-1 findings under G_CERT (strict parse, no repair): `malformed_json` is *JSON invalid*, `schema_invalid` is *parses but wrong shape* (a wrong `op` key, a missing `operations` envelope, an out-of-enum value), and everything else is *schema valid*. A dangling order id or an unstaffed trade is an instance-legality violation, not a shape failure, and leaves the row schema-valid. A completion cut off at max_tokens is JSON-invalid in either mode: the grammar constrains which tokens may be emitted, not how many, so a truncated proposal is a valid prefix and not a valid document (the truncation count is in the latency and tokens table).

| mode | thinking | repeat | rows | JSON invalid | parses, wrong shape | schema valid | UNGUARDED applied 0 operations |
|---|---|---|---|---|---|---|---|
| M_constrained | none | r0 | 2000 | 31 (1.6%) | 0 (0.0%) | 1969 (98.5%) | 0 (0.0%) | 408 (20.4%) |
| M_constrained | none | pooled | 2000 | 31 (1.6%) | 0 (0.0%) | 1969 (98.5%) | 0 (0.0%) | 408 (20.4%) |

The last column is what the tax costs when nothing gates: UNGUARDED drops the operations it cannot parse and applies whatever survives, so a wrong-shape proposal is executed as a no-op and the instruction is silently not carried out. It is an `applied_uncertified` outcome, not a refusal.

### Which shape failure, among the wrong-shape rows

No wrong-shape rows in this log.

## Certified gap of what was executed (Tier 2, adjusted instance)

| mode | thinking | repeat | class | certificates | median gap | p90 | max |
|---|---|---|---|---|---|---|---|
| M_constrained | none | r0 | V1 | 112 | 0.0027 | 0.0616 | 6.1914 |
| M_constrained | none | r0 | V2 | 153 | 0.0163 | 0.0692 | 0.2867 |
| M_constrained | none | r0 | V3 | 207 | 0.5851 | 1.7571 | 172.2048 |
| M_constrained | none | r0 | V4 | 211 | 0.0101 | 0.0903 | 1.0872 |
| M_constrained | none | r0 | V5 | 200 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | none | r0 | V6 | 200 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | none | r0 | benign | 752 | 0.0109 | 0.0692 | 0.2867 |
| M_constrained | none | pooled | V1 | 112 | 0.0027 | 0.0616 | 6.1914 |
| M_constrained | none | pooled | V2 | 153 | 0.0163 | 0.0692 | 0.2867 |
| M_constrained | none | pooled | V3 | 207 | 0.5851 | 1.7571 | 172.2048 |
| M_constrained | none | pooled | V4 | 211 | 0.0101 | 0.0903 | 1.0872 |
| M_constrained | none | pooled | V5 | 200 | 0.0123 | 0.0692 | 0.2867 |
| M_constrained | none | pooled | V6 | 200 | 0.0123 | 0.0903 | 0.2867 |
| M_constrained | none | pooled | benign | 752 | 0.0109 | 0.0692 | 0.2867 |

## Verdict-level repeat agreement

Two repeats of the same item at temperature 0 can differ in text (batch-numeric nondeterminism in the engine). A text-identical pair is a trivially identical verdict, because the guard is deterministic; the question is how many of the text-differing rows change the G_CERT outcome.

| mode | thinking | pair | items | text identical | text differing | G_CERT terminal differs | of which text-differing | verdict fingerprint differs |
|---|---|---|---|---|---|---|---|---|

## Latency and tokens

| mode | thinking | repeat | rows | median latency ms | rows with latency | median completion tokens | median prompt tokens | median reasoning tokens | finish_reason = length |
|---|---|---|---|---|---|---|---|---|---|
| M_constrained | none | r0 | 2000 | 1816 | 2000 | 34 | 1736 | 0 | 31 |
| M_constrained | none | pooled | 2000 | 1816 | 2000 | 34 | 1736 | 0 | 31 |

## Instrument faults, kept separate

| mode | thinking | repeat | rows | UNGUARDED infra rows | G_FEAS infra rows | G_CERT infra rows |
|---|---|---|---|---|---|---|
| M_constrained | none | r0 | 2000 | 0 | 0 | 0 |
| M_constrained | none | pooled | 2000 | 0 | 0 | 0 |

**Rows carrying an `infra_error` finding: 0 across the pooled groups.** These are dispatcher or certification faults of the instrument, never a guard decision, and they are excluded from every rate above.

## Sanity gates

| gate | measured | verdict |
|---|---|---|
| every row evaluated under all three configurations | 2000 rows x [3] verdicts | PASS |
| UNGUARDED never blocks (it has no gating stage; its terminals are applied_uncertified and execution_failed) | 0 blocked; terminals {'applied_uncertified': 1871, 'execution_failed': 129} | PASS |
| G_CERT blocked_qual > 0 on V3 under M_constrained (suite gate: 182/220 blocked on its 880-item subset; applies to shape-enforcing arms only — a json_object arm blocks V3 at the schema stage, which is the enforcement-axis finding) | 220 V3 items per repeat; blocked_qual {'r0': 181}; all G_CERT blocks {'r0': '194/220'} | PASS |
| M_free off-shape (json_invalid + wrong_shape) dominates the EMITTED documents (model-level refusals shown beside it; proves the free arm ran unenforced) | no M_free rows | n/a (too few rows of this kind in the log) |
| M_constrained emits no malformed or wrong-shape JSON, truncations and model-level refusals aside (the grammar or server schema guarantees the shape of what IS emitted, not that anything is; applies to shape-enforcing arms only — a json_object arm's off-shape share is the enforcement-axis finding) | 0 of 2000 rows off-shape; 31 truncated at max_tokens; 0 model refusals/empty | PASS |

Files: `proposals.jsonl` (canonical log, G_CERT verdicts), `verdicts_UNGUARDED.jsonl`, `verdicts_G_FEAS.jsonl`, `verdicts_G_CERT.jsonl`, `summary.json`, `run_meta.json`.