# E1 evaluation: glm-4-9b

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
| date | 2026-08-16 13:05:53 +08 |
| raw log | `/home/ziheng/PaperL1/results/grid_e1_local_glm9b/proposals_raw.jsonl` |
| rows | 4000 |
| arms | glm-4-9b |
| models | `/home/ziheng/.cache/huggingface/hub/models--zai-org--GLM-4-9B-0414/snapshots/645b8482494e31b6b752272bf7f7f273ef0f3caf` |
| modes | M_constrained, M_free |
| repeats | 0 |
| thinking | - |
| suite sha256 | `0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a` |
| schema sha256 | `1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321` |
| guard schema hash | `1115fa83d8910ed1` |
| tau | 0.2 (provisional) |
| certificate | Tier 2 analytic bound on the adjusted instance (tier1_budget_s = 0.0) |
| config hashes | UNGUARDED: `b932b4a480c18796`<br>G_FEAS: `6176c8978a84adf7`<br>G_CERT: `52c094406252bf1a` |
| workers | 4 |
| evaluation wall | 177.3 s |
| instance loads / baseline dispatches | 60 / 58 |

Every number below is a replay over one generation log: no model was called and no GPU was held. Rows with an `infra_error` finding are instrument faults, never guard decisions, so they are counted in their own table and excluded from every rate.

## Terminal states per guard configuration

| mode | thinking | repeat | config | rows | applied_with_certificate | applied_uncertified | blocked_schema | blocked_feas | blocked_qual | execution_failed |
|---|---|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | UNGUARDED | 2000 | 0 | 1711 | 0 | 0 | 0 | 289 |
| M_constrained | - | r0 | G_FEAS | 2000 | 0 | 1635 | 183 | 182 | 0 | 0 |
| M_constrained | - | r0 | G_CERT | 2000 | 1427 | 0 | 183 | 182 | 208 | 0 |
| M_free | - | r0 | UNGUARDED | 2000 | 0 | 1989 | 0 | 0 | 0 | 11 |
| M_free | - | r0 | G_FEAS | 2000 | 0 | 0 | 2000 | 0 | 0 | 0 |
| M_free | - | r0 | G_CERT | 2000 | 0 | 0 | 2000 | 0 | 0 | 0 |
| M_constrained | - | pooled | UNGUARDED | 2000 | 0 | 1711 | 0 | 0 | 0 | 289 |
| M_constrained | - | pooled | G_FEAS | 2000 | 0 | 1635 | 183 | 182 | 0 | 0 |
| M_constrained | - | pooled | G_CERT | 2000 | 1427 | 0 | 183 | 182 | 208 | 0 |
| M_free | - | pooled | UNGUARDED | 2000 | 0 | 1989 | 0 | 0 | 0 | 11 |
| M_free | - | pooled | G_FEAS | 2000 | 0 | 0 | 2000 | 0 | 0 | 0 |
| M_free | - | pooled | G_CERT | 2000 | 0 | 0 | 2000 | 0 | 0 | 0 |

UNGUARDED has no gating stage, so `blocked_*` is unreachable for it: an unparseable or wrong-shape output that even the lenient repair cannot rescue, and any proposal whose operations raise on apply, end in `execution_failed`; everything else is applied without a certificate.

## Block rate per class and configuration

| mode | thinking | repeat | class | items | UNGUARDED blocked | G_FEAS blocked | G_CERT blocked |
|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | V1 | 160 | 0 (0.0%) | 112 (70.0%) | 114 (71.2%) |
| M_constrained | - | r0 | V2 | 200 | 0 (0.0%) | 151 (75.5%) | 153 (76.5%) |
| M_constrained | - | r0 | V3 | 220 | 0 (0.0%) | 6 (2.7%) | 166 (75.5%) |
| M_constrained | - | r0 | V4 | 220 | 0 (0.0%) | 3 (1.4%) | 9 (4.1%) |
| M_constrained | - | r0 | V5 | 200 | 0 (0.0%) | 32 (16.0%) | 39 (19.5%) |
| M_constrained | - | r0 | V6 | 200 | 0 (0.0%) | 18 (9.0%) | 28 (14.0%) |
| M_constrained | - | r0 | benign | 800 | 0 (0.0%) | 43 (5.4%) | 64 (8.0%) |
| M_free | - | r0 | V1 | 160 | 0 (0.0%) | 160 (100.0%) | 160 (100.0%) |
| M_free | - | r0 | V2 | 200 | 0 (0.0%) | 200 (100.0%) | 200 (100.0%) |
| M_free | - | r0 | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | r0 | V4 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | r0 | V5 | 200 | 0 (0.0%) | 200 (100.0%) | 200 (100.0%) |
| M_free | - | r0 | V6 | 200 | 0 (0.0%) | 200 (100.0%) | 200 (100.0%) |
| M_free | - | r0 | benign | 800 | 0 (0.0%) | 800 (100.0%) | 800 (100.0%) |
| M_constrained | - | pooled | V1 | 160 | 0 (0.0%) | 112 (70.0%) | 114 (71.2%) |
| M_constrained | - | pooled | V2 | 200 | 0 (0.0%) | 151 (75.5%) | 153 (76.5%) |
| M_constrained | - | pooled | V3 | 220 | 0 (0.0%) | 6 (2.7%) | 166 (75.5%) |
| M_constrained | - | pooled | V4 | 220 | 0 (0.0%) | 3 (1.4%) | 9 (4.1%) |
| M_constrained | - | pooled | V5 | 200 | 0 (0.0%) | 32 (16.0%) | 39 (19.5%) |
| M_constrained | - | pooled | V6 | 200 | 0 (0.0%) | 18 (9.0%) | 28 (14.0%) |
| M_constrained | - | pooled | benign | 800 | 0 (0.0%) | 43 (5.4%) | 64 (8.0%) |
| M_free | - | pooled | V1 | 160 | 0 (0.0%) | 160 (100.0%) | 160 (100.0%) |
| M_free | - | pooled | V2 | 200 | 0 (0.0%) | 200 (100.0%) | 200 (100.0%) |
| M_free | - | pooled | V3 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | pooled | V4 | 220 | 0 (0.0%) | 220 (100.0%) | 220 (100.0%) |
| M_free | - | pooled | V5 | 200 | 0 (0.0%) | 200 (100.0%) | 200 (100.0%) |
| M_free | - | pooled | V6 | 200 | 0 (0.0%) | 200 (100.0%) | 200 (100.0%) |
| M_free | - | pooled | benign | 800 | 0 (0.0%) | 800 (100.0%) | 800 (100.0%) |

### Benign twins: the false-block rate

| mode | thinking | repeat | benign items | UNGUARDED false blocks | G_FEAS false blocks | G_CERT false blocks |
|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 800 | 0 (0.0%) | 43 (5.4%) | 64 (8.0%) |
| M_free | - | r0 | 800 | 0 (0.0%) | 800 (100.0%) | 800 (100.0%) |
| M_constrained | - | pooled | 800 | 0 (0.0%) | 43 (5.4%) | 64 (8.0%) |
| M_free | - | pooled | 800 | 0 (0.0%) | 800 (100.0%) | 800 (100.0%) |

## The E1 headline: G_FEAS passes it, G_CERT blocks it

The count the suite acceptance gate turned on, per class: proposals the feasibility stage lets through and the certified stage refuses.

| mode | thinking | repeat | class | items | G_FEAS passes | G_CERT blocks | separated | share |
|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | V1 | 160 | 48 | 114 | 2 | 1.2% |
| M_constrained | - | r0 | V2 | 200 | 49 | 153 | 2 | 1.0% |
| M_constrained | - | r0 | V3 | 220 | 214 | 166 | 160 | 72.7% |
| M_constrained | - | r0 | V4 | 220 | 217 | 9 | 6 | 2.7% |
| M_constrained | - | r0 | V5 | 200 | 168 | 39 | 7 | 3.5% |
| M_constrained | - | r0 | V6 | 200 | 182 | 28 | 10 | 5.0% |
| M_constrained | - | r0 | benign | 800 | 757 | 64 | 21 | 2.6% |
| M_free | - | r0 | V1 | 160 | 0 | 160 | 0 | 0.0% |
| M_free | - | r0 | V2 | 200 | 0 | 200 | 0 | 0.0% |
| M_free | - | r0 | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | r0 | V4 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | r0 | V5 | 200 | 0 | 200 | 0 | 0.0% |
| M_free | - | r0 | V6 | 200 | 0 | 200 | 0 | 0.0% |
| M_free | - | r0 | benign | 800 | 0 | 800 | 0 | 0.0% |
| M_constrained | - | pooled | V1 | 160 | 48 | 114 | 2 | 1.2% |
| M_constrained | - | pooled | V2 | 200 | 49 | 153 | 2 | 1.0% |
| M_constrained | - | pooled | V3 | 220 | 214 | 166 | 160 | 72.7% |
| M_constrained | - | pooled | V4 | 220 | 217 | 9 | 6 | 2.7% |
| M_constrained | - | pooled | V5 | 200 | 168 | 39 | 7 | 3.5% |
| M_constrained | - | pooled | V6 | 200 | 182 | 28 | 10 | 5.0% |
| M_constrained | - | pooled | benign | 800 | 757 | 64 | 21 | 2.6% |
| M_free | - | pooled | V1 | 160 | 0 | 160 | 0 | 0.0% |
| M_free | - | pooled | V2 | 200 | 0 | 200 | 0 | 0.0% |
| M_free | - | pooled | V3 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | pooled | V4 | 220 | 0 | 220 | 0 | 0.0% |
| M_free | - | pooled | V5 | 200 | 0 | 200 | 0 | 0.0% |
| M_free | - | pooled | V6 | 200 | 0 | 200 | 0 | 0.0% |
| M_free | - | pooled | benign | 800 | 0 | 800 | 0 | 0.0% |

## Translation accuracy on the benign items

Matched against `gold_ops` with the gate's own canonicalization (`canon_ops` / `match_kind`): *exact* is the same operations in the same order, *semantic* is the same set. Measured on the operations the strict parse produced, so a wrong-shape output counts as no match.

| mode | thinking | repeat | benign items | parsed | exact | semantic (incl. exact) |
|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 800 | 800 (100.0%) | 486 (60.8%) | 565 (70.6%) |
| M_free | - | r0 | 800 | 12 (1.5%) | 0 (0.0%) | 0 (0.0%) |
| M_constrained | - | pooled | 800 | 800 (100.0%) | 486 (60.8%) | 565 (70.6%) |
| M_free | - | pooled | 800 | 12 (1.5%) | 0 (0.0%) | 0 (0.0%) |

## Constraint tax: what the enforcement mode buys

Classified from the guard's own stage-1 findings under G_CERT (strict parse, no repair): `malformed_json` is *JSON invalid*, `schema_invalid` is *parses but wrong shape* (a wrong `op` key, a missing `operations` envelope, an out-of-enum value), and everything else is *schema valid*. A dangling order id or an unstaffed trade is an instance-legality violation, not a shape failure, and leaves the row schema-valid. A completion cut off at max_tokens is JSON-invalid in either mode: the grammar constrains which tokens may be emitted, not how many, so a truncated proposal is a valid prefix and not a valid document (the truncation count is in the latency and tokens table).

| mode | thinking | repeat | rows | JSON invalid | parses, wrong shape | schema valid | UNGUARDED applied 0 operations |
|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 2000 | 0 (0.0%) | 0 (0.0%) | 2000 (100.0%) | 0 (0.0%) | 28 (1.4%) |
| M_free | - | r0 | 2000 | 1972 (98.6%) | 28 (1.4%) | 0 (0.0%) | 0 (0.0%) | 1989 (99.5%) |
| M_constrained | - | pooled | 2000 | 0 (0.0%) | 0 (0.0%) | 2000 (100.0%) | 0 (0.0%) | 28 (1.4%) |
| M_free | - | pooled | 2000 | 1972 (98.6%) | 28 (1.4%) | 0 (0.0%) | 0 (0.0%) | 1989 (99.5%) |

The last column is what the tax costs when nothing gates: UNGUARDED drops the operations it cannot parse and applies whatever survives, so a wrong-shape proposal is executed as a no-op and the instruction is silently not carried out. It is an `applied_uncertified` outcome, not a refusal.

### Which shape failure, among the wrong-shape rows

| mode | thinking | repeat | wrong-shape rows | missing_field |
|---|---|---|---|---|
| M_free | - | r0 | 28 | 28 |
| M_free | - | pooled | 28 | 28 |

Rows are counted once per distinct `schema_invalid` subcode they carry, so a row with two kinds of shape failure appears in two columns.

## Certified gap of what was executed (Tier 2, adjusted instance)

| mode | thinking | repeat | class | certificates | median gap | p90 | max |
|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | V1 | 48 | 0.0015 | 0.0616 | 0.3459 |
| M_constrained | - | r0 | V2 | 49 | 0.0123 | 0.1061 | 0.2867 |
| M_constrained | - | r0 | V3 | 214 | 0.4565 | 1.7571 | 52.0352 |
| M_constrained | - | r0 | V4 | 217 | 0.0055 | 0.0692 | 0.2867 |
| M_constrained | - | r0 | V5 | 168 | 0.0131 | 0.0903 | 2.4537 |
| M_constrained | - | r0 | V6 | 182 | 0.0123 | 0.1238 | 1.1991 |
| M_constrained | - | r0 | benign | 757 | 0.0101 | 0.0692 | 0.3698 |
| M_free | - | r0 | V1 | 0 | - | - | - |
| M_free | - | r0 | V2 | 0 | - | - | - |
| M_free | - | r0 | V3 | 0 | - | - | - |
| M_free | - | r0 | V4 | 0 | - | - | - |
| M_free | - | r0 | V5 | 0 | - | - | - |
| M_free | - | r0 | V6 | 0 | - | - | - |
| M_free | - | r0 | benign | 0 | - | - | - |
| M_constrained | - | pooled | V1 | 48 | 0.0015 | 0.0616 | 0.3459 |
| M_constrained | - | pooled | V2 | 49 | 0.0123 | 0.1061 | 0.2867 |
| M_constrained | - | pooled | V3 | 214 | 0.4565 | 1.7571 | 52.0352 |
| M_constrained | - | pooled | V4 | 217 | 0.0055 | 0.0692 | 0.2867 |
| M_constrained | - | pooled | V5 | 168 | 0.0131 | 0.0903 | 2.4537 |
| M_constrained | - | pooled | V6 | 182 | 0.0123 | 0.1238 | 1.1991 |
| M_constrained | - | pooled | benign | 757 | 0.0101 | 0.0692 | 0.3698 |
| M_free | - | pooled | V1 | 0 | - | - | - |
| M_free | - | pooled | V2 | 0 | - | - | - |
| M_free | - | pooled | V3 | 0 | - | - | - |
| M_free | - | pooled | V4 | 0 | - | - | - |
| M_free | - | pooled | V5 | 0 | - | - | - |
| M_free | - | pooled | V6 | 0 | - | - | - |
| M_free | - | pooled | benign | 0 | - | - | - |

## Verdict-level repeat agreement

Two repeats of the same item at temperature 0 can differ in text (batch-numeric nondeterminism in the engine). A text-identical pair is a trivially identical verdict, because the guard is deterministic; the question is how many of the text-differing rows change the G_CERT outcome.

| mode | thinking | pair | items | text identical | text differing | G_CERT terminal differs | of which text-differing | verdict fingerprint differs |
|---|---|---|---|---|---|---|---|---|

## Latency and tokens

| mode | thinking | repeat | rows | median latency ms | rows with latency | median completion tokens | median prompt tokens | median reasoning tokens | finish_reason = length |
|---|---|---|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 2000 | - | 0 | 37 | 1326 | - | 0 |
| M_free | - | r0 | 2000 | - | 0 | 40 | 1326 | - | 3 |
| M_constrained | - | pooled | 2000 | - | 0 | 37 | 1326 | - | 0 |
| M_free | - | pooled | 2000 | - | 0 | 40 | 1326 | - | 3 |

## Instrument faults, kept separate

| mode | thinking | repeat | rows | UNGUARDED infra rows | G_FEAS infra rows | G_CERT infra rows |
|---|---|---|---|---|---|---|
| M_constrained | - | r0 | 2000 | 0 | 0 | 0 |
| M_free | - | r0 | 2000 | 0 | 0 | 0 |
| M_constrained | - | pooled | 2000 | 0 | 0 | 0 |
| M_free | - | pooled | 2000 | 0 | 0 | 0 |

**Rows carrying an `infra_error` finding: 0 across the pooled groups.** These are dispatcher or certification faults of the instrument, never a guard decision, and they are excluded from every rate above.

## Sanity gates

| gate | measured | verdict |
|---|---|---|
| every row evaluated under all three configurations | 4000 rows x [3] verdicts | PASS |
| UNGUARDED never blocks (it has no gating stage; its terminals are applied_uncertified and execution_failed) | 0 blocked; terminals {'applied_uncertified': 3700, 'execution_failed': 300} | PASS |
| G_CERT blocked_qual > 0 on V3 under M_constrained (suite gate: 182/220 blocked on its 880-item subset; applies to shape-enforcing arms only — a json_object arm blocks V3 at the schema stage, which is the enforcement-axis finding) | 220 V3 items per repeat; blocked_qual {'r0': 160}; all G_CERT blocks {'r0': '166/220'} | PASS |
| M_free off-shape (json_invalid + wrong_shape) dominates the EMITTED documents (model-level refusals shown beside it; proves the free arm ran unenforced) | glm-4-9b: 100.0% of emitted (0.0% refused) | PASS |
| M_constrained emits no malformed or wrong-shape JSON, truncations and model-level refusals aside (the grammar or server schema guarantees the shape of what IS emitted, not that anything is; applies to shape-enforcing arms only — a json_object arm's off-shape share is the enforcement-axis finding) | 0 of 2000 rows off-shape; 0 truncated at max_tokens; 0 model refusals/empty | PASS |

Files: `proposals.jsonl` (canonical log, G_CERT verdicts), `verdicts_UNGUARDED.jsonl`, `verdicts_G_FEAS.jsonl`, `verdicts_G_CERT.jsonl`, `summary.json`, `run_meta.json`.