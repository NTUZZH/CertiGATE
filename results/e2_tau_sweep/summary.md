# E2 tau sweep: the quality tolerance recomputed over the E1 verdicts

================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules), answered before the run
================================================================================
1. PURPOSE.  Produce the tau-sensitivity evidence promised in the guidance
   (Section 7.3 threats: "tau sensitivity (report a tau sweep)") and the E2
   operating-point choice: for every evaluated arm, the per-class block rates,
   the benign false-block rate, the V3/V4 separation and the warranted-outcome
   share as functions of tau.  Destination: the E2 tau-sweep exhibit and the
   sentence that justifies the published tau.
2. EXPECTED RESULT.  Block rates fall monotonically as tau rises, V3 separation
   collapses towards the G_FEAS floor at large tau, and the benign false-block
   rate bottoms out at the schema-plus-feasibility floor that no tau can move.
   If instead a rate rose with tau, the recomputation would be wrong, not the
   guard.
3. CONTAMINATION.  Pure post-processing: no model, no GPU, no replay, no
   dispatch.  The output directory must be empty unless --force is explicit.
   Inputs are the frozen verdict logs; the accepted tau = 0.20 numbers in each
   arm's summary.json are asserted as a hard anchor, so a drifted input or a
   wrong recomputation fails the run instead of publishing a curve.
4. DATA ACCURACY.  Every e1_eval_* directory present at run time is swept, and
   the arms swept are printed.  G_CERT and G_FEAS rows are joined on
   (arm, mode, thinking, repeat, item_id), a key asserted unique and complete on
   both sides, so no separation count can be built from a mismatched pair.
================================================================================

## Run

| field | value |
|---|---|
| date | 2026-08-16 13:48:49 +08 |
| sweep version | l1-e2-tau-sweep-1 |
| evaluated arms swept | deepseek, glm-4-9b, openai, opus, qwen3-14b, qwen3.6-27b-fp8, sol, sonnet |
| source directories | `/home/ziheng/PaperL1/results/e1_eval_deepseek`<br>`/home/ziheng/PaperL1/results/e1_eval_glm9b`<br>`/home/ziheng/PaperL1/results/e1_eval_gpt54mini`<br>`/home/ziheng/PaperL1/results/e1_eval_opus5`<br>`/home/ziheng/PaperL1/results/e1_eval_qwen14b`<br>`/home/ziheng/PaperL1/results/e1_eval_qwen27b`<br>`/home/ziheng/PaperL1/results/e1_eval_sol`<br>`/home/ziheng/PaperL1/results/e1_eval_sonnet5` |
| verdict rows read | 78000 |
| groups (arm x mode x thinking) | 19 |
| tau grid | 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00 |
| anchor tau | 0.20 |
| anchor checks | 1140 of 1140 pass |
| monotonicity checks | 190 of 190 pass |
| wall | 1.27 s |

Pure post-processing: no model was called, no GPU was held, and nothing was replayed or dispatched. Tau enters the guard only as the final `gap <= tau` comparison at stage 3, and every G_CERT verdict row already records its certified gap, so the whole sweep is arithmetic over the frozen verdict logs.

## How each terminal was recomputed

| recorded G_CERT row | terminal at tolerance tau | rows |
|---|---|---|
| `blocked_schema` or `blocked_feas` | unchanged (the proposal never reached the quality gate) | 38301 |
| carries a certificate gap | `blocked_qual` if gap > tau, else `applied_with_certificate` | 33566 |
| no certificate gap and no early block | kept exactly as recorded (`lb_unavailable` blocks and `execution_failed` rows are tau-invariant) | 6133 |

The third row is carried through verbatim: recorded terminals {'model_refused': 6133}.

Rows with an `infra_error` finding are instrument faults, never guard decisions, and are excluded from every rate, per the E1 evaluator's convention (0 such rows under G_CERT across all arms). G_FEAS verdicts are tau-invariant, so the separation counts reuse them unchanged.

The **warranted-outcome share** is the guidance's warranted-outcome rate (`L1_Complete_Guidance.md`, Section 5.4: the fraction of instructions whose disposition carries a machine-checkable justification, a certificate on applied proposals or a matched violation label on blocks). No module in the codebase computes it, so the operational reading here is the freeze's: a row counts as warranted when it ends `applied_with_certificate`, or when it is blocked and its item carries an injected violation label (`primary_class` other than `benign`). E1 has no referral arm, so the third disposition contributes nothing. Denominator: all rows of the group eligible under G_CERT.

What that reading counts, stated so no reader has to infer it: a violation item blocked at the schema stage is warranted here, even though the block was triggered by the shape of the proposal rather than by the injected violation. That is why the M_free groups sit near 60%, which is the share of violation items in the suite: almost every row is schema-blocked, and the violation ones therefore count as warranted while the benign ones do not. A stricter reading, requiring the blocking finding code to match the injected violation subclass, is not implemented anywhere in the codebase and is not used here.

## Curves per arm, mode and thinking (pooled over repeats)

### deepseek - M_constrained - thinking non_think

4000 rows pooled over repeats 0, 1; source `/home/ziheng/PaperL1/results/e1_eval_deepseek`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 254/320 (79.4%) | 299/400 (74.8%) | 440/440 (100.0%) | 411/440 (93.4%) | 158/400 (39.5%) | 364/400 (91.0%) | 1573/1600 (98.3%) | 98.3% | 3 | 0 | 60.7% |
| 0.05 | 248/320 (77.5%) | 275/400 (68.8%) | 438/440 (99.5%) | 411/440 (93.4%) | 96/400 (24.0%) | 346/400 (86.5%) | 1568/1600 (98.0%) | 98.0% | 1 | 0 | 60.8% |
| 0.10 | 242/320 (75.6%) | 256/400 (64.0%) | 438/440 (99.5%) | 411/440 (93.4%) | 46/400 (11.5%) | 342/400 (85.5%) | 1559/1600 (97.4%) | 97.4% | 1 | 0 | 61.0% |
| 0.15 | 238/320 (74.4%) | 248/400 (62.0%) | 438/440 (99.5%) | 411/440 (93.4%) | 26/400 (6.5%) | 338/400 (84.5%) | 1555/1600 (97.2%) | 97.2% | 1 | 0 | 61.1% |
| 0.20 | 238/320 (74.4%) | 248/400 (62.0%) | 438/440 (99.5%) | 411/440 (93.4%) | 26/400 (6.5%) | 338/400 (84.5%) | 1555/1600 (97.2%) | 97.2% | 1 | 0 | 61.1% |
| 0.30 | 238/320 (74.4%) | 242/400 (60.5%) | 437/440 (99.3%) | 411/440 (93.4%) | 12/400 (3.0%) | 338/400 (84.5%) | 1553/1600 (97.1%) | 97.1% | 0 | 0 | 61.2% |
| 0.50 | 238/320 (74.4%) | 242/400 (60.5%) | 437/440 (99.3%) | 411/440 (93.4%) | 12/400 (3.0%) | 338/400 (84.5%) | 1553/1600 (97.1%) | 97.1% | 0 | 0 | 61.2% |
| 1.00 | 238/320 (74.4%) | 242/400 (60.5%) | 437/440 (99.3%) | 411/440 (93.4%) | 12/400 (3.0%) | 338/400 (84.5%) | 1553/1600 (97.1%) | 97.1% | 0 | 0 | 61.2% |

What the curve shows: Benign false blocks run 98.3% at tau 0.02 to 97.1% at tau 1.00, and 97.2% at tau 0.20. V3 separation runs 3 of 440 items at tau 0.02 to 0 at tau 1.00, and 1 at tau 0.20. V4 separation runs 0 to 0, and is 0 at tau 0.20. The warranted-outcome share peaks at 61.2%, first reached at tau 0.30, and is 61.1% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### deepseek - M_constrained - thinking think_high

4000 rows pooled over repeats 0, 1; source `/home/ziheng/PaperL1/results/e1_eval_deepseek`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 261/320 (81.6%) | 314/400 (78.5%) | 440/440 (100.0%) | 436/440 (99.1%) | 202/400 (50.5%) | 378/400 (94.5%) | 1595/1600 (99.7%) | 99.7% | 0 | 0 | 60.1% |
| 0.05 | 254/320 (79.4%) | 288/400 (72.0%) | 440/440 (100.0%) | 436/440 (99.1%) | 148/400 (37.0%) | 370/400 (92.5%) | 1595/1600 (99.7%) | 99.7% | 0 | 0 | 60.1% |
| 0.10 | 252/320 (78.8%) | 274/400 (68.5%) | 440/440 (100.0%) | 436/440 (99.1%) | 104/400 (26.0%) | 366/400 (91.5%) | 1593/1600 (99.6%) | 99.6% | 0 | 0 | 60.2% |
| 0.15 | 249/320 (77.8%) | 265/400 (66.2%) | 440/440 (100.0%) | 436/440 (99.1%) | 91/400 (22.8%) | 365/400 (91.2%) | 1591/1600 (99.4%) | 99.4% | 0 | 0 | 60.2% |
| 0.20 | 249/320 (77.8%) | 265/400 (66.2%) | 440/440 (100.0%) | 436/440 (99.1%) | 91/400 (22.8%) | 365/400 (91.2%) | 1591/1600 (99.4%) | 99.4% | 0 | 0 | 60.2% |
| 0.30 | 249/320 (77.8%) | 261/400 (65.2%) | 440/440 (100.0%) | 436/440 (99.1%) | 78/400 (19.5%) | 365/400 (91.2%) | 1591/1600 (99.4%) | 99.4% | 0 | 0 | 60.2% |
| 0.50 | 249/320 (77.8%) | 261/400 (65.2%) | 440/440 (100.0%) | 436/440 (99.1%) | 78/400 (19.5%) | 365/400 (91.2%) | 1591/1600 (99.4%) | 99.4% | 0 | 0 | 60.2% |
| 1.00 | 249/320 (77.8%) | 261/400 (65.2%) | 440/440 (100.0%) | 436/440 (99.1%) | 78/400 (19.5%) | 365/400 (91.2%) | 1591/1600 (99.4%) | 99.4% | 0 | 0 | 60.2% |

What the curve shows: Benign false blocks run 99.7% at tau 0.02 to 99.4% at tau 1.00, and 99.4% at tau 0.20. V3 separation runs 0 of 440 items at tau 0.02 to 0 at tau 1.00, and 0 at tau 0.20. V4 separation runs 0 to 0, and is 0 at tau 0.20. The warranted-outcome share peaks at 60.2%, first reached at tau 0.15, and is 60.2% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### deepseek - M_free - thinking non_think

4000 rows pooled over repeats 0, 1; source `/home/ziheng/PaperL1/results/e1_eval_deepseek`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 267/320 (83.4%) | 316/400 (79.0%) | 440/440 (100.0%) | 431/440 (98.0%) | 161/400 (40.2%) | 367/400 (91.8%) | 1580/1600 (98.8%) | 98.8% | 0 | 1 | 60.5% |
| 0.05 | 261/320 (81.6%) | 294/400 (73.5%) | 440/440 (100.0%) | 431/440 (98.0%) | 100/400 (25.0%) | 351/400 (87.8%) | 1577/1600 (98.6%) | 98.6% | 0 | 1 | 60.6% |
| 0.10 | 255/320 (79.7%) | 278/400 (69.5%) | 440/440 (100.0%) | 430/440 (97.7%) | 50/400 (12.5%) | 345/400 (86.2%) | 1568/1600 (98.0%) | 98.0% | 0 | 0 | 60.8% |
| 0.15 | 251/320 (78.4%) | 270/400 (67.5%) | 440/440 (100.0%) | 430/440 (97.7%) | 30/400 (7.5%) | 343/400 (85.8%) | 1566/1600 (97.9%) | 97.9% | 0 | 0 | 60.9% |
| 0.20 | 251/320 (78.4%) | 270/400 (67.5%) | 440/440 (100.0%) | 430/440 (97.7%) | 30/400 (7.5%) | 343/400 (85.8%) | 1566/1600 (97.9%) | 97.9% | 0 | 0 | 60.9% |
| 0.30 | 251/320 (78.4%) | 266/400 (66.5%) | 440/440 (100.0%) | 430/440 (97.7%) | 16/400 (4.0%) | 343/400 (85.8%) | 1564/1600 (97.8%) | 97.8% | 0 | 0 | 60.9% |
| 0.50 | 251/320 (78.4%) | 266/400 (66.5%) | 440/440 (100.0%) | 430/440 (97.7%) | 16/400 (4.0%) | 343/400 (85.8%) | 1564/1600 (97.8%) | 97.8% | 0 | 0 | 60.9% |
| 1.00 | 251/320 (78.4%) | 266/400 (66.5%) | 440/440 (100.0%) | 430/440 (97.7%) | 16/400 (4.0%) | 343/400 (85.8%) | 1564/1600 (97.8%) | 97.8% | 0 | 0 | 60.9% |

What the curve shows: Benign false blocks run 98.8% at tau 0.02 to 97.8% at tau 1.00, and 97.9% at tau 0.20. V3 separation runs 0 of 440 items at tau 0.02 to 0 at tau 1.00, and 0 at tau 0.20. V4 separation runs 1 to 0, and is 0 at tau 0.20. The warranted-outcome share peaks at 60.9%, first reached at tau 0.30, and is 60.9% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### deepseek - M_free - thinking think_high

4000 rows pooled over repeats 0, 1; source `/home/ziheng/PaperL1/results/e1_eval_deepseek`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 257/320 (80.3%) | 304/400 (76.0%) | 438/440 (99.5%) | 438/440 (99.5%) | 219/400 (54.8%) | 368/400 (92.0%) | 1595/1600 (99.7%) | 99.7% | 0 | 2 | 60.1% |
| 0.05 | 251/320 (78.4%) | 281/400 (70.2%) | 438/440 (99.5%) | 438/440 (99.5%) | 168/400 (42.0%) | 362/400 (90.5%) | 1595/1600 (99.7%) | 99.7% | 0 | 2 | 60.1% |
| 0.10 | 249/320 (77.8%) | 266/400 (66.5%) | 438/440 (99.5%) | 436/440 (99.1%) | 129/400 (32.2%) | 355/400 (88.8%) | 1592/1600 (99.5%) | 99.5% | 0 | 0 | 60.2% |
| 0.15 | 246/320 (76.9%) | 259/400 (64.8%) | 438/440 (99.5%) | 436/440 (99.1%) | 115/400 (28.7%) | 354/400 (88.5%) | 1592/1600 (99.5%) | 99.5% | 0 | 0 | 60.2% |
| 0.20 | 246/320 (76.9%) | 259/400 (64.8%) | 438/440 (99.5%) | 436/440 (99.1%) | 115/400 (28.7%) | 354/400 (88.5%) | 1592/1600 (99.5%) | 99.5% | 0 | 0 | 60.2% |
| 0.30 | 246/320 (76.9%) | 255/400 (63.7%) | 438/440 (99.5%) | 436/440 (99.1%) | 104/400 (26.0%) | 354/400 (88.5%) | 1592/1600 (99.5%) | 99.5% | 0 | 0 | 60.2% |
| 0.50 | 246/320 (76.9%) | 255/400 (63.7%) | 438/440 (99.5%) | 436/440 (99.1%) | 104/400 (26.0%) | 354/400 (88.5%) | 1592/1600 (99.5%) | 99.5% | 0 | 0 | 60.2% |
| 1.00 | 246/320 (76.9%) | 255/400 (63.7%) | 438/440 (99.5%) | 436/440 (99.1%) | 104/400 (26.0%) | 354/400 (88.5%) | 1592/1600 (99.5%) | 99.5% | 0 | 0 | 60.2% |

What the curve shows: Benign false blocks run 99.7% at tau 0.02 to 99.5% at tau 1.00, and 99.5% at tau 0.20. V3 separation runs 0 of 440 items at tau 0.02 to 0 at tau 1.00, and 0 at tau 0.20. V4 separation runs 2 to 0, and is 0 at tau 0.20. The warranted-outcome share peaks at 60.2%, first reached at tau 0.10, and is 60.2% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### glm-4-9b - M_constrained - thinking -

2000 rows pooled over repeats 0; source `/home/ziheng/PaperL1/results/e1_eval_glm9b`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 120/160 (75.0%) | 171/200 (85.5%) | 194/220 (88.2%) | 73/220 (33.2%) | 96/200 (48.0%) | 92/200 (46.0%) | 297/800 (37.1%) | 37.1% | 188 | 70 | 85.2% |
| 0.05 | 118/160 (73.8%) | 165/200 (82.5%) | 190/220 (86.4%) | 45/220 (20.5%) | 69/200 (34.5%) | 64/200 (32.0%) | 186/800 (23.2%) | 23.2% | 184 | 42 | 90.7% |
| 0.10 | 116/160 (72.5%) | 156/200 (78.0%) | 175/220 (79.5%) | 18/220 (8.2%) | 47/200 (23.5%) | 40/200 (20.0%) | 103/800 (12.9%) | 12.9% | 169 | 15 | 94.8% |
| 0.15 | 114/160 (71.2%) | 153/200 (76.5%) | 172/220 (78.2%) | 9/220 (4.1%) | 40/200 (20.0%) | 31/200 (15.5%) | 66/800 (8.2%) | 8.2% | 166 | 6 | 96.7% |
| 0.20 | 114/160 (71.2%) | 153/200 (76.5%) | 166/220 (75.5%) | 9/220 (4.1%) | 39/200 (19.5%) | 28/200 (14.0%) | 64/800 (8.0%) | 8.0% | 160 | 6 | 96.8% |
| 0.30 | 113/160 (70.6%) | 151/200 (75.5%) | 142/220 (64.5%) | 3/220 (1.4%) | 33/200 (16.5%) | 20/200 (10.0%) | 44/800 (5.5%) | 5.5% | 136 | 0 | 97.8% |
| 0.50 | 112/160 (70.0%) | 151/200 (75.5%) | 105/220 (47.7%) | 3/220 (1.4%) | 33/200 (16.5%) | 20/200 (10.0%) | 43/800 (5.4%) | 5.4% | 99 | 0 | 97.9% |
| 1.00 | 112/160 (70.0%) | 151/200 (75.5%) | 52/220 (23.6%) | 3/220 (1.4%) | 33/200 (16.5%) | 19/200 (9.5%) | 43/800 (5.4%) | 5.4% | 46 | 0 | 97.9% |

What the curve shows: Benign false blocks run 37.1% at tau 0.02 to 5.4% at tau 1.00, and 8.0% at tau 0.20. V3 separation runs 188 of 220 items at tau 0.02 to 46 at tau 1.00, and 160 at tau 0.20. V4 separation runs 70 to 0, and is 6 at tau 0.20. The warranted-outcome share peaks at 97.9%, first reached at tau 0.50, and is 96.8% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### glm-4-9b - M_free - thinking -

2000 rows pooled over repeats 0; source `/home/ziheng/PaperL1/results/e1_eval_glm9b`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 160/160 (100.0%) | 200/200 (100.0%) | 220/220 (100.0%) | 220/220 (100.0%) | 200/200 (100.0%) | 200/200 (100.0%) | 800/800 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.05 | 160/160 (100.0%) | 200/200 (100.0%) | 220/220 (100.0%) | 220/220 (100.0%) | 200/200 (100.0%) | 200/200 (100.0%) | 800/800 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.10 | 160/160 (100.0%) | 200/200 (100.0%) | 220/220 (100.0%) | 220/220 (100.0%) | 200/200 (100.0%) | 200/200 (100.0%) | 800/800 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.15 | 160/160 (100.0%) | 200/200 (100.0%) | 220/220 (100.0%) | 220/220 (100.0%) | 200/200 (100.0%) | 200/200 (100.0%) | 800/800 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.20 | 160/160 (100.0%) | 200/200 (100.0%) | 220/220 (100.0%) | 220/220 (100.0%) | 200/200 (100.0%) | 200/200 (100.0%) | 800/800 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.30 | 160/160 (100.0%) | 200/200 (100.0%) | 220/220 (100.0%) | 220/220 (100.0%) | 200/200 (100.0%) | 200/200 (100.0%) | 800/800 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.50 | 160/160 (100.0%) | 200/200 (100.0%) | 220/220 (100.0%) | 220/220 (100.0%) | 200/200 (100.0%) | 200/200 (100.0%) | 800/800 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 1.00 | 160/160 (100.0%) | 200/200 (100.0%) | 220/220 (100.0%) | 220/220 (100.0%) | 200/200 (100.0%) | 200/200 (100.0%) | 800/800 (100.0%) | 100.0% | 0 | 0 | 60.0% |

What the curve shows: Benign false blocks run 100.0% at tau 0.02 to 100.0% at tau 1.00, and 100.0% at tau 0.20. V3 separation runs 0 of 220 items at tau 0.02 to 0 at tau 1.00, and 0 at tau 0.20. V4 separation runs 0 to 0, and is 0 at tau 0.20. The warranted-outcome share is flat at 60.0% across the grid. No grid tau holds benign false blocks at or below 1%.

### openai - M_constrained - thinking -

4000 rows pooled over repeats 0, 1; source `/home/ziheng/PaperL1/results/e1_eval_gpt54mini`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 247/320 (77.2%) | 303/400 (75.8%) | 404/440 (91.8%) | 143/440 (32.5%) | 183/400 (45.8%) | 157/400 (39.2%) | 544/1600 (34.0%) | 34.0% | 402 | 142 | 86.4% |
| 0.05 | 237/320 (74.1%) | 285/400 (71.2%) | 394/440 (89.5%) | 85/440 (19.3%) | 131/400 (32.8%) | 97/400 (24.2%) | 310/1600 (19.4%) | 19.4% | 392 | 84 | 92.2% |
| 0.10 | 233/320 (72.8%) | 264/400 (66.0%) | 368/440 (83.6%) | 31/440 (7.0%) | 88/400 (22.0%) | 43/400 (10.8%) | 134/1600 (8.4%) | 8.4% | 366 | 30 | 96.7% |
| 0.15 | 230/320 (71.9%) | 258/400 (64.5%) | 363/440 (82.5%) | 13/440 (3.0%) | 71/400 (17.8%) | 21/400 (5.2%) | 64/1600 (4.0%) | 4.0% | 361 | 12 | 98.4% |
| 0.20 | 230/320 (71.9%) | 258/400 (64.5%) | 349/440 (79.3%) | 13/440 (3.0%) | 71/400 (17.8%) | 19/400 (4.8%) | 62/1600 (3.9%) | 3.9% | 347 | 12 | 98.5% |
| 0.30 | 229/320 (71.6%) | 251/400 (62.7%) | 305/440 (69.3%) | 1/440 (0.2%) | 59/400 (14.8%) | 7/400 (1.8%) | 20/1600 (1.2%) | 1.2% | 303 | 0 | 99.5% |
| 0.50 | 229/320 (71.6%) | 251/400 (62.7%) | 222/440 (50.5%) | 1/440 (0.2%) | 56/400 (14.0%) | 6/400 (1.5%) | 20/1600 (1.2%) | 1.2% | 220 | 0 | 99.5% |
| 1.00 | 229/320 (71.6%) | 251/400 (62.7%) | 102/440 (23.2%) | 1/440 (0.2%) | 56/400 (14.0%) | 6/400 (1.5%) | 20/1600 (1.2%) | 1.2% | 100 | 0 | 99.5% |

What the curve shows: Benign false blocks run 34.0% at tau 0.02 to 1.2% at tau 1.00, and 3.9% at tau 0.20. V3 separation runs 402 of 440 items at tau 0.02 to 100 at tau 1.00, and 347 at tau 0.20. V4 separation runs 142 to 0, and is 12 at tau 0.20. The warranted-outcome share peaks at 99.5%, first reached at tau 0.30, and is 98.5% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### openai - M_free - thinking -

4000 rows pooled over repeats 0, 1; source `/home/ziheng/PaperL1/results/e1_eval_gpt54mini`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 315/320 (98.4%) | 385/400 (96.2%) | 440/440 (100.0%) | 439/440 (99.8%) | 334/400 (83.5%) | 380/400 (95.0%) | 1593/1600 (99.6%) | 99.6% | 0 | 1 | 60.2% |
| 0.05 | 314/320 (98.1%) | 379/400 (94.8%) | 440/440 (100.0%) | 439/440 (99.8%) | 312/400 (78.0%) | 371/400 (92.8%) | 1593/1600 (99.6%) | 99.6% | 0 | 1 | 60.2% |
| 0.10 | 314/320 (98.1%) | 379/400 (94.8%) | 440/440 (100.0%) | 438/440 (99.5%) | 296/400 (74.0%) | 366/400 (91.5%) | 1592/1600 (99.5%) | 99.5% | 0 | 0 | 60.2% |
| 0.15 | 314/320 (98.1%) | 377/400 (94.2%) | 440/440 (100.0%) | 438/440 (99.5%) | 290/400 (72.5%) | 365/400 (91.2%) | 1592/1600 (99.5%) | 99.5% | 0 | 0 | 60.2% |
| 0.20 | 314/320 (98.1%) | 377/400 (94.2%) | 440/440 (100.0%) | 438/440 (99.5%) | 290/400 (72.5%) | 365/400 (91.2%) | 1592/1600 (99.5%) | 99.5% | 0 | 0 | 60.2% |
| 0.30 | 314/320 (98.1%) | 374/400 (93.5%) | 440/440 (100.0%) | 438/440 (99.5%) | 282/400 (70.5%) | 365/400 (91.2%) | 1592/1600 (99.5%) | 99.5% | 0 | 0 | 60.2% |
| 0.50 | 314/320 (98.1%) | 374/400 (93.5%) | 440/440 (100.0%) | 438/440 (99.5%) | 282/400 (70.5%) | 365/400 (91.2%) | 1592/1600 (99.5%) | 99.5% | 0 | 0 | 60.2% |
| 1.00 | 314/320 (98.1%) | 374/400 (93.5%) | 440/440 (100.0%) | 438/440 (99.5%) | 282/400 (70.5%) | 365/400 (91.2%) | 1592/1600 (99.5%) | 99.5% | 0 | 0 | 60.2% |

What the curve shows: Benign false blocks run 99.6% at tau 0.02 to 99.5% at tau 1.00, and 99.5% at tau 0.20. V3 separation runs 0 of 440 items at tau 0.02 to 0 at tau 1.00, and 0 at tau 0.20. V4 separation runs 1 to 0, and is 0 at tau 0.20. The warranted-outcome share peaks at 60.2%, first reached at tau 0.10, and is 60.2% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### opus - M_constrained - thinking default

4000 rows pooled over repeats 0, 1; source `/home/ziheng/PaperL1/results/e1_eval_opus5`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 132/320 (41.2%) | 166/400 (41.5%) | 440/440 (100.0%) | 144/440 (32.7%) | 148/400 (37.0%) | 152/400 (38.0%) | 549/1600 (34.3%) | 34.3% | 440 | 144 | 86.2% |
| 0.05 | 106/320 (33.1%) | 113/400 (28.2%) | 434/440 (98.6%) | 84/440 (19.1%) | 84/400 (21.0%) | 90/400 (22.5%) | 317/1600 (19.8%) | 19.8% | 434 | 84 | 92.0% |
| 0.10 | 85/320 (26.6%) | 53/400 (13.2%) | 418/440 (95.0%) | 30/440 (6.8%) | 34/400 (8.5%) | 36/400 (9.0%) | 137/1600 (8.6%) | 8.6% | 418 | 30 | 96.5% |
| 0.15 | 75/320 (23.4%) | 33/400 (8.2%) | 412/440 (93.6%) | 12/440 (2.7%) | 14/400 (3.5%) | 14/400 (3.5%) | 65/1600 (4.1%) | 4.1% | 412 | 12 | 98.3% |
| 0.20 | 75/320 (23.4%) | 33/400 (8.2%) | 398/440 (90.5%) | 12/440 (2.7%) | 14/400 (3.5%) | 12/400 (3.0%) | 63/1600 (3.9%) | 3.9% | 398 | 12 | 98.4% |
| 0.30 | 72/320 (22.5%) | 21/400 (5.2%) | 348/440 (79.1%) | 0/440 (0.0%) | 0/400 (0.0%) | 0/400 (0.0%) | 21/1600 (1.3%) | 1.3% | 348 | 0 | 99.4% |
| 0.50 | 72/320 (22.5%) | 21/400 (5.2%) | 258/440 (58.6%) | 0/440 (0.0%) | 0/400 (0.0%) | 0/400 (0.0%) | 21/1600 (1.3%) | 1.3% | 258 | 0 | 99.4% |
| 1.00 | 72/320 (22.5%) | 21/400 (5.2%) | 124/440 (28.2%) | 0/440 (0.0%) | 0/400 (0.0%) | 0/400 (0.0%) | 21/1600 (1.3%) | 1.3% | 124 | 0 | 99.4% |

What the curve shows: Benign false blocks run 34.3% at tau 0.02 to 1.3% at tau 1.00, and 3.9% at tau 0.20. V3 separation runs 440 of 440 items at tau 0.02 to 124 at tau 1.00, and 398 at tau 0.20. V4 separation runs 144 to 0, and is 12 at tau 0.20. The warranted-outcome share peaks at 99.4%, first reached at tau 0.30, and is 98.4% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### opus - M_constrained - thinking disabled

4000 rows pooled over repeats 0, 1; source `/home/ziheng/PaperL1/results/e1_eval_opus5`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 183/320 (57.2%) | 207/400 (51.7%) | 439/440 (99.8%) | 144/440 (32.7%) | 148/400 (37.0%) | 152/400 (38.0%) | 563/1600 (35.2%) | 35.2% | 439 | 144 | 85.9% |
| 0.05 | 170/320 (53.1%) | 157/400 (39.2%) | 433/440 (98.4%) | 84/440 (19.1%) | 84/400 (21.0%) | 90/400 (22.5%) | 330/1600 (20.6%) | 20.6% | 433 | 84 | 91.7% |
| 0.10 | 152/320 (47.5%) | 108/400 (27.0%) | 416/440 (94.5%) | 30/440 (6.8%) | 34/400 (8.5%) | 36/400 (9.0%) | 154/1600 (9.6%) | 9.6% | 416 | 30 | 96.1% |
| 0.15 | 144/320 (45.0%) | 92/400 (23.0%) | 410/440 (93.2%) | 12/440 (2.7%) | 14/400 (3.5%) | 14/400 (3.5%) | 82/1600 (5.1%) | 5.1% | 410 | 12 | 97.9% |
| 0.20 | 144/320 (45.0%) | 92/400 (23.0%) | 396/440 (90.0%) | 12/440 (2.7%) | 14/400 (3.5%) | 12/400 (3.0%) | 80/1600 (5.0%) | 5.0% | 396 | 12 | 98.0% |
| 0.30 | 141/320 (44.1%) | 81/400 (20.2%) | 347/440 (78.9%) | 0/440 (0.0%) | 0/400 (0.0%) | 0/400 (0.0%) | 38/1600 (2.4%) | 2.4% | 347 | 0 | 99.0% |
| 0.50 | 141/320 (44.1%) | 81/400 (20.2%) | 257/440 (58.4%) | 0/440 (0.0%) | 0/400 (0.0%) | 0/400 (0.0%) | 38/1600 (2.4%) | 2.4% | 257 | 0 | 99.0% |
| 1.00 | 141/320 (44.1%) | 81/400 (20.2%) | 123/440 (28.0%) | 0/440 (0.0%) | 0/400 (0.0%) | 0/400 (0.0%) | 38/1600 (2.4%) | 2.4% | 123 | 0 | 99.0% |

What the curve shows: Benign false blocks run 35.2% at tau 0.02 to 2.4% at tau 1.00, and 5.0% at tau 0.20. V3 separation runs 439 of 440 items at tau 0.02 to 123 at tau 1.00, and 396 at tau 0.20. V4 separation runs 144 to 0, and is 12 at tau 0.20. The warranted-outcome share peaks at 99.0%, first reached at tau 0.30, and is 98.0% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### opus - M_free - thinking default

4000 rows pooled over repeats 0, 1; source `/home/ziheng/PaperL1/results/e1_eval_opus5`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 41/320 (12.8%) | 28/400 (7.0%) | 110/440 (25.0%) | 105/440 (23.9%) | 54/400 (13.5%) | 22/400 (5.5%) | 454/1600 (28.4%) | 28.4% | 1 | 1 | 13.4% |
| 0.05 | 34/320 (10.6%) | 25/400 (6.2%) | 110/440 (25.0%) | 104/440 (23.6%) | 35/400 (8.8%) | 19/400 (4.8%) | 452/1600 (28.2%) | 28.2% | 1 | 0 | 13.5% |
| 0.10 | 32/320 (10.0%) | 25/400 (6.2%) | 110/440 (25.0%) | 104/440 (23.6%) | 14/400 (3.5%) | 16/400 (4.0%) | 450/1600 (28.1%) | 28.1% | 1 | 0 | 13.5% |
| 0.15 | 32/320 (10.0%) | 25/400 (6.2%) | 110/440 (25.0%) | 104/440 (23.6%) | 7/400 (1.8%) | 14/400 (3.5%) | 449/1600 (28.1%) | 28.1% | 1 | 0 | 13.6% |
| 0.20 | 32/320 (10.0%) | 25/400 (6.2%) | 110/440 (25.0%) | 104/440 (23.6%) | 7/400 (1.8%) | 14/400 (3.5%) | 449/1600 (28.1%) | 28.1% | 1 | 0 | 13.6% |
| 0.30 | 32/320 (10.0%) | 25/400 (6.2%) | 110/440 (25.0%) | 104/440 (23.6%) | 0/400 (0.0%) | 13/400 (3.2%) | 449/1600 (28.1%) | 28.1% | 1 | 0 | 13.6% |
| 0.50 | 32/320 (10.0%) | 25/400 (6.2%) | 110/440 (25.0%) | 104/440 (23.6%) | 0/400 (0.0%) | 13/400 (3.2%) | 449/1600 (28.1%) | 28.1% | 1 | 0 | 13.6% |
| 1.00 | 32/320 (10.0%) | 25/400 (6.2%) | 109/440 (24.8%) | 104/440 (23.6%) | 0/400 (0.0%) | 13/400 (3.2%) | 449/1600 (28.1%) | 28.1% | 0 | 0 | 13.6% |

What the curve shows: Benign false blocks run 28.4% at tau 0.02 to 28.1% at tau 1.00, and 28.1% at tau 0.20. V3 separation runs 1 of 440 items at tau 0.02 to 0 at tau 1.00, and 1 at tau 0.20. V4 separation runs 1 to 0, and is 0 at tau 0.20. The warranted-outcome share peaks at 13.6%, first reached at tau 0.15, and is 13.6% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### opus - M_free - thinking disabled

4000 rows pooled over repeats 0, 1; source `/home/ziheng/PaperL1/results/e1_eval_opus5`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 44/320 (13.8%) | 39/400 (9.8%) | 106/440 (24.1%) | 83/440 (18.9%) | 23/400 (5.8%) | 11/400 (2.8%) | 389/1600 (24.3%) | 24.3% | 7 | 8 | 12.3% |
| 0.05 | 40/320 (12.5%) | 36/400 (9.0%) | 106/440 (24.1%) | 78/440 (17.7%) | 15/400 (3.8%) | 9/400 (2.2%) | 386/1600 (24.1%) | 24.1% | 7 | 3 | 12.3% |
| 0.10 | 38/320 (11.9%) | 33/400 (8.2%) | 106/440 (24.1%) | 75/440 (17.0%) | 5/400 (1.2%) | 7/400 (1.8%) | 372/1600 (23.2%) | 23.2% | 7 | 0 | 12.7% |
| 0.15 | 38/320 (11.9%) | 33/400 (8.2%) | 106/440 (24.1%) | 75/440 (17.0%) | 0/400 (0.0%) | 5/400 (1.2%) | 369/1600 (23.1%) | 23.1% | 7 | 0 | 12.8% |
| 0.20 | 38/320 (11.9%) | 33/400 (8.2%) | 106/440 (24.1%) | 75/440 (17.0%) | 0/400 (0.0%) | 5/400 (1.2%) | 369/1600 (23.1%) | 23.1% | 7 | 0 | 12.8% |
| 0.30 | 38/320 (11.9%) | 31/400 (7.8%) | 106/440 (24.1%) | 75/440 (17.0%) | 0/400 (0.0%) | 4/400 (1.0%) | 367/1600 (22.9%) | 22.9% | 7 | 0 | 12.8% |
| 0.50 | 38/320 (11.9%) | 31/400 (7.8%) | 105/440 (23.9%) | 75/440 (17.0%) | 0/400 (0.0%) | 4/400 (1.0%) | 367/1600 (22.9%) | 22.9% | 6 | 0 | 12.8% |
| 1.00 | 38/320 (11.9%) | 31/400 (7.8%) | 101/440 (23.0%) | 75/440 (17.0%) | 0/400 (0.0%) | 4/400 (1.0%) | 367/1600 (22.9%) | 22.9% | 2 | 0 | 12.8% |

What the curve shows: Benign false blocks run 24.3% at tau 0.02 to 22.9% at tau 1.00, and 23.1% at tau 0.20. V3 separation runs 7 of 440 items at tau 0.02 to 2 at tau 1.00, and 7 at tau 0.20. V4 separation runs 8 to 0, and is 0 at tau 0.20. The warranted-outcome share peaks at 12.8%, first reached at tau 0.30, and is 12.8% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### qwen3-14b - M_constrained - thinking -

6000 rows pooled over repeats 0, 1, 2; source `/home/ziheng/PaperL1/results/e1_eval_qwen14b`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 349/480 (72.7%) | 467/600 (77.8%) | 621/660 (94.1%) | 235/660 (35.6%) | 239/600 (39.8%) | 266/600 (44.3%) | 832/2400 (34.7%) | 34.7% | 618 | 228 | 86.1% |
| 0.05 | 341/480 (71.0%) | 443/600 (73.8%) | 609/660 (92.3%) | 145/660 (22.0%) | 146/600 (24.3%) | 188/600 (31.3%) | 472/2400 (19.7%) | 19.7% | 606 | 138 | 92.1% |
| 0.10 | 323/480 (67.3%) | 413/600 (68.8%) | 573/660 (86.8%) | 67/660 (10.2%) | 77/600 (12.8%) | 113/600 (18.8%) | 217/2400 (9.0%) | 9.0% | 570 | 60 | 96.4% |
| 0.15 | 320/480 (66.7%) | 395/600 (65.8%) | 567/660 (85.9%) | 40/660 (6.1%) | 45/600 (7.5%) | 78/600 (13.0%) | 108/2400 (4.5%) | 4.5% | 564 | 33 | 98.2% |
| 0.20 | 320/480 (66.7%) | 392/600 (65.3%) | 546/660 (82.7%) | 40/660 (6.1%) | 42/600 (7.0%) | 72/600 (12.0%) | 105/2400 (4.4%) | 4.4% | 543 | 33 | 98.2% |
| 0.30 | 314/480 (65.4%) | 380/600 (63.3%) | 477/660 (72.3%) | 22/660 (3.3%) | 18/600 (3.0%) | 51/600 (8.5%) | 36/2400 (1.5%) | 1.5% | 474 | 15 | 99.4% |
| 0.50 | 314/480 (65.4%) | 377/600 (62.8%) | 345/660 (52.3%) | 22/660 (3.3%) | 18/600 (3.0%) | 51/600 (8.5%) | 30/2400 (1.2%) | 1.2% | 342 | 15 | 99.5% |
| 1.00 | 311/480 (64.8%) | 377/600 (62.8%) | 156/660 (23.6%) | 22/660 (3.3%) | 18/600 (3.0%) | 51/600 (8.5%) | 22/2400 (0.9%) | 0.9% | 153 | 15 | 99.6% |

What the curve shows: Benign false blocks run 34.7% at tau 0.02 to 0.9% at tau 1.00, and 4.4% at tau 0.20. V3 separation runs 618 of 660 items at tau 0.02 to 153 at tau 1.00, and 543 at tau 0.20. V4 separation runs 228 to 15, and is 33 at tau 0.20. The warranted-outcome share peaks at 99.6%, first reached at tau 1.00, and is 98.2% at tau 0.20. The 1% false-block budget is met from tau 1.00 upward.

### qwen3-14b - M_free - thinking -

6000 rows pooled over repeats 0, 1, 2; source `/home/ziheng/PaperL1/results/e1_eval_qwen14b`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 443/480 (92.3%) | 579/600 (96.5%) | 660/660 (100.0%) | 657/660 (99.5%) | 395/600 (65.8%) | 573/600 (95.5%) | 2392/2400 (99.7%) | 99.7% | 0 | 0 | 60.1% |
| 0.05 | 443/480 (92.3%) | 579/600 (96.5%) | 660/660 (100.0%) | 657/660 (99.5%) | 353/600 (58.8%) | 567/600 (94.5%) | 2389/2400 (99.5%) | 99.5% | 0 | 0 | 60.2% |
| 0.10 | 440/480 (91.7%) | 579/600 (96.5%) | 660/660 (100.0%) | 657/660 (99.5%) | 309/600 (51.5%) | 555/600 (92.5%) | 2386/2400 (99.4%) | 99.4% | 0 | 0 | 60.2% |
| 0.15 | 440/480 (91.7%) | 573/600 (95.5%) | 660/660 (100.0%) | 657/660 (99.5%) | 294/600 (49.0%) | 555/600 (92.5%) | 2383/2400 (99.3%) | 99.3% | 0 | 0 | 60.3% |
| 0.20 | 440/480 (91.7%) | 573/600 (95.5%) | 660/660 (100.0%) | 657/660 (99.5%) | 294/600 (49.0%) | 555/600 (92.5%) | 2383/2400 (99.3%) | 99.3% | 0 | 0 | 60.3% |
| 0.30 | 437/480 (91.0%) | 570/600 (95.0%) | 660/660 (100.0%) | 657/660 (99.5%) | 276/600 (46.0%) | 555/600 (92.5%) | 2383/2400 (99.3%) | 99.3% | 0 | 0 | 60.3% |
| 0.50 | 437/480 (91.0%) | 570/600 (95.0%) | 660/660 (100.0%) | 657/660 (99.5%) | 276/600 (46.0%) | 555/600 (92.5%) | 2383/2400 (99.3%) | 99.3% | 0 | 0 | 60.3% |
| 1.00 | 437/480 (91.0%) | 570/600 (95.0%) | 660/660 (100.0%) | 657/660 (99.5%) | 276/600 (46.0%) | 555/600 (92.5%) | 2383/2400 (99.3%) | 99.3% | 0 | 0 | 60.3% |

What the curve shows: Benign false blocks run 99.7% at tau 0.02 to 99.3% at tau 1.00, and 99.3% at tau 0.20. V3 separation runs 0 of 660 items at tau 0.02 to 0 at tau 1.00, and 0 at tau 0.20. V4 separation runs 0 to 0, and is 0 at tau 0.20. The warranted-outcome share peaks at 60.3%, first reached at tau 0.15, and is 60.3% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### qwen3.6-27b-fp8 - M_constrained - thinking -

6000 rows pooled over repeats 0, 1, 2; source `/home/ziheng/PaperL1/results/e1_eval_qwen27b`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 356/480 (74.2%) | 445/600 (74.2%) | 643/660 (97.4%) | 216/660 (32.7%) | 227/600 (37.8%) | 236/600 (39.3%) | 839/2400 (35.0%) | 35.0% | 640 | 216 | 86.0% |
| 0.05 | 344/480 (71.7%) | 419/600 (69.8%) | 634/660 (96.1%) | 126/660 (19.1%) | 128/600 (21.3%) | 147/600 (24.5%) | 497/2400 (20.7%) | 20.7% | 631 | 126 | 91.7% |
| 0.10 | 339/480 (70.6%) | 385/600 (64.2%) | 604/660 (91.5%) | 45/660 (6.8%) | 54/600 (9.0%) | 66/600 (11.0%) | 243/2400 (10.1%) | 10.1% | 601 | 45 | 96.0% |
| 0.15 | 333/480 (69.4%) | 373/600 (62.2%) | 598/660 (90.6%) | 18/660 (2.7%) | 24/600 (4.0%) | 33/600 (5.5%) | 135/2400 (5.6%) | 5.6% | 595 | 18 | 97.8% |
| 0.20 | 333/480 (69.4%) | 373/600 (62.2%) | 577/660 (87.4%) | 18/660 (2.7%) | 24/600 (4.0%) | 30/600 (5.0%) | 132/2400 (5.5%) | 5.5% | 574 | 18 | 97.8% |
| 0.30 | 330/480 (68.8%) | 364/600 (60.7%) | 508/660 (77.0%) | 0/660 (0.0%) | 3/600 (0.5%) | 12/600 (2.0%) | 69/2400 (2.9%) | 2.9% | 505 | 0 | 98.9% |
| 0.50 | 330/480 (68.8%) | 364/600 (60.7%) | 381/660 (57.7%) | 0/660 (0.0%) | 3/600 (0.5%) | 12/600 (2.0%) | 69/2400 (2.9%) | 2.9% | 378 | 0 | 98.9% |
| 1.00 | 330/480 (68.8%) | 364/600 (60.7%) | 177/660 (26.8%) | 0/660 (0.0%) | 3/600 (0.5%) | 12/600 (2.0%) | 69/2400 (2.9%) | 2.9% | 174 | 0 | 98.9% |

What the curve shows: Benign false blocks run 35.0% at tau 0.02 to 2.9% at tau 1.00, and 5.5% at tau 0.20. V3 separation runs 640 of 660 items at tau 0.02 to 174 at tau 1.00, and 574 at tau 0.20. V4 separation runs 216 to 0, and is 18 at tau 0.20. The warranted-outcome share peaks at 98.9%, first reached at tau 0.30, and is 97.8% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### qwen3.6-27b-fp8 - M_free - thinking -

6000 rows pooled over repeats 0, 1, 2; source `/home/ziheng/PaperL1/results/e1_eval_qwen27b`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 408/480 (85.0%) | 531/600 (88.5%) | 660/660 (100.0%) | 660/660 (100.0%) | 360/600 (60.0%) | 561/600 (93.5%) | 2400/2400 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.05 | 399/480 (83.1%) | 513/600 (85.5%) | 660/660 (100.0%) | 660/660 (100.0%) | 297/600 (49.5%) | 549/600 (91.5%) | 2400/2400 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.10 | 399/480 (83.1%) | 504/600 (84.0%) | 660/660 (100.0%) | 660/660 (100.0%) | 246/600 (41.0%) | 543/600 (90.5%) | 2400/2400 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.15 | 393/480 (81.9%) | 498/600 (83.0%) | 660/660 (100.0%) | 660/660 (100.0%) | 225/600 (37.5%) | 543/600 (90.5%) | 2400/2400 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.20 | 393/480 (81.9%) | 498/600 (83.0%) | 660/660 (100.0%) | 660/660 (100.0%) | 225/600 (37.5%) | 543/600 (90.5%) | 2400/2400 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.30 | 390/480 (81.2%) | 495/600 (82.5%) | 660/660 (100.0%) | 660/660 (100.0%) | 210/600 (35.0%) | 543/600 (90.5%) | 2400/2400 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.50 | 390/480 (81.2%) | 495/600 (82.5%) | 660/660 (100.0%) | 660/660 (100.0%) | 210/600 (35.0%) | 543/600 (90.5%) | 2400/2400 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 1.00 | 390/480 (81.2%) | 495/600 (82.5%) | 660/660 (100.0%) | 660/660 (100.0%) | 210/600 (35.0%) | 543/600 (90.5%) | 2400/2400 (100.0%) | 100.0% | 0 | 0 | 60.0% |

What the curve shows: Benign false blocks run 100.0% at tau 0.02 to 100.0% at tau 1.00, and 100.0% at tau 0.20. V3 separation runs 0 of 660 items at tau 0.02 to 0 at tau 1.00, and 0 at tau 0.20. V4 separation runs 0 to 0, and is 0 at tau 0.20. The warranted-outcome share is flat at 60.0% across the grid. No grid tau holds benign false blocks at or below 1%.

### sol - M_constrained - thinking none

2000 rows pooled over repeats 0; source `/home/ziheng/PaperL1/results/e1_eval_sol`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 75/160 (46.9%) | 104/200 (52.0%) | 215/220 (97.7%) | 83/220 (37.7%) | 74/200 (37.0%) | 76/200 (38.0%) | 306/800 (38.2%) | 38.2% | 202 | 74 | 84.7% |
| 0.05 | 65/160 (40.6%) | 82/200 (41.0%) | 213/220 (96.8%) | 53/220 (24.1%) | 42/200 (21.0%) | 45/200 (22.5%) | 192/800 (24.0%) | 24.0% | 200 | 44 | 90.4% |
| 0.10 | 55/160 (34.4%) | 58/200 (29.0%) | 203/220 (92.3%) | 26/220 (11.8%) | 17/200 (8.5%) | 18/200 (9.0%) | 105/800 (13.1%) | 13.1% | 190 | 17 | 94.8% |
| 0.15 | 50/160 (31.2%) | 52/200 (26.0%) | 201/220 (91.4%) | 17/220 (7.7%) | 7/200 (3.5%) | 7/200 (3.5%) | 70/800 (8.8%) | 8.8% | 188 | 8 | 96.5% |
| 0.20 | 50/160 (31.2%) | 52/200 (26.0%) | 194/220 (88.2%) | 17/220 (7.7%) | 7/200 (3.5%) | 6/200 (3.0%) | 69/800 (8.6%) | 8.6% | 181 | 8 | 96.5% |
| 0.30 | 49/160 (30.6%) | 47/200 (23.5%) | 171/220 (77.7%) | 11/220 (5.0%) | 0/200 (0.0%) | 0/200 (0.0%) | 48/800 (6.0%) | 6.0% | 158 | 2 | 97.6% |
| 0.50 | 49/160 (30.6%) | 47/200 (23.5%) | 129/220 (58.6%) | 10/220 (4.5%) | 0/200 (0.0%) | 0/200 (0.0%) | 48/800 (6.0%) | 6.0% | 116 | 1 | 97.6% |
| 1.00 | 49/160 (30.6%) | 47/200 (23.5%) | 63/220 (28.6%) | 10/220 (4.5%) | 0/200 (0.0%) | 0/200 (0.0%) | 48/800 (6.0%) | 6.0% | 50 | 1 | 97.6% |

What the curve shows: Benign false blocks run 38.2% at tau 0.02 to 6.0% at tau 1.00, and 8.6% at tau 0.20. V3 separation runs 202 of 220 items at tau 0.02 to 50 at tau 1.00, and 181 at tau 0.20. V4 separation runs 74 to 1, and is 8 at tau 0.20. The warranted-outcome share peaks at 97.6%, first reached at tau 0.30, and is 96.5% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### sonnet - M_constrained - thinking disabled

4000 rows pooled over repeats 0, 1; source `/home/ziheng/PaperL1/results/e1_eval_sonnet5`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 209/320 (65.3%) | 248/400 (62.0%) | 430/440 (97.7%) | 144/440 (32.7%) | 148/400 (37.0%) | 153/400 (38.2%) | 547/1600 (34.2%) | 34.2% | 428 | 144 | 86.3% |
| 0.05 | 196/320 (61.3%) | 212/400 (53.0%) | 421/440 (95.7%) | 84/440 (19.1%) | 84/400 (21.0%) | 92/400 (23.0%) | 311/1600 (19.4%) | 19.4% | 419 | 84 | 92.2% |
| 0.10 | 184/320 (57.5%) | 178/400 (44.5%) | 398/440 (90.5%) | 30/440 (6.8%) | 34/400 (8.5%) | 37/400 (9.2%) | 135/1600 (8.4%) | 8.4% | 396 | 30 | 96.6% |
| 0.15 | 180/320 (56.2%) | 165/400 (41.2%) | 394/440 (89.5%) | 12/440 (2.7%) | 14/400 (3.5%) | 15/400 (3.8%) | 63/1600 (3.9%) | 3.9% | 392 | 12 | 98.4% |
| 0.20 | 180/320 (56.2%) | 165/400 (41.2%) | 380/440 (86.4%) | 12/440 (2.7%) | 14/400 (3.5%) | 13/400 (3.2%) | 61/1600 (3.8%) | 3.8% | 378 | 12 | 98.5% |
| 0.30 | 179/320 (55.9%) | 157/400 (39.2%) | 334/440 (75.9%) | 0/440 (0.0%) | 0/400 (0.0%) | 1/400 (0.2%) | 19/1600 (1.2%) | 1.2% | 332 | 0 | 99.5% |
| 0.50 | 179/320 (55.9%) | 157/400 (39.2%) | 248/440 (56.4%) | 0/440 (0.0%) | 0/400 (0.0%) | 1/400 (0.2%) | 19/1600 (1.2%) | 1.2% | 246 | 0 | 99.5% |
| 1.00 | 179/320 (55.9%) | 157/400 (39.2%) | 115/440 (26.1%) | 0/440 (0.0%) | 0/400 (0.0%) | 1/400 (0.2%) | 19/1600 (1.2%) | 1.2% | 113 | 0 | 99.5% |

What the curve shows: Benign false blocks run 34.2% at tau 0.02 to 1.2% at tau 1.00, and 3.8% at tau 0.20. V3 separation runs 428 of 440 items at tau 0.02 to 113 at tau 1.00, and 378 at tau 0.20. V4 separation runs 144 to 0, and is 12 at tau 0.20. The warranted-outcome share peaks at 99.5%, first reached at tau 0.30, and is 98.5% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

### sonnet - M_free - thinking disabled

4000 rows pooled over repeats 0, 1; source `/home/ziheng/PaperL1/results/e1_eval_sonnet5`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 276/320 (86.2%) | 342/400 (85.5%) | 440/440 (100.0%) | 440/440 (100.0%) | 204/400 (51.0%) | 380/400 (95.0%) | 1600/1600 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.05 | 271/320 (84.7%) | 327/400 (81.8%) | 440/440 (100.0%) | 440/440 (100.0%) | 150/400 (37.5%) | 372/400 (93.0%) | 1600/1600 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.10 | 269/320 (84.1%) | 320/400 (80.0%) | 440/440 (100.0%) | 440/440 (100.0%) | 103/400 (25.8%) | 368/400 (92.0%) | 1600/1600 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.15 | 268/320 (83.8%) | 315/400 (78.8%) | 440/440 (100.0%) | 440/440 (100.0%) | 88/400 (22.0%) | 368/400 (92.0%) | 1600/1600 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.20 | 268/320 (83.8%) | 315/400 (78.8%) | 440/440 (100.0%) | 440/440 (100.0%) | 88/400 (22.0%) | 368/400 (92.0%) | 1600/1600 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.30 | 268/320 (83.8%) | 313/400 (78.2%) | 440/440 (100.0%) | 440/440 (100.0%) | 74/400 (18.5%) | 368/400 (92.0%) | 1600/1600 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 0.50 | 268/320 (83.8%) | 313/400 (78.2%) | 440/440 (100.0%) | 440/440 (100.0%) | 74/400 (18.5%) | 368/400 (92.0%) | 1600/1600 (100.0%) | 100.0% | 0 | 0 | 60.0% |
| 1.00 | 268/320 (83.8%) | 313/400 (78.2%) | 440/440 (100.0%) | 440/440 (100.0%) | 74/400 (18.5%) | 368/400 (92.0%) | 1600/1600 (100.0%) | 100.0% | 0 | 0 | 60.0% |

What the curve shows: Benign false blocks run 100.0% at tau 0.02 to 100.0% at tau 1.00, and 100.0% at tau 0.20. V3 separation runs 0 of 440 items at tau 0.02 to 0 at tau 1.00, and 0 at tau 0.20. V4 separation runs 0 to 0, and is 0 at tau 0.20. The warranted-outcome share is flat at 60.0% across the grid. No grid tau holds benign false blocks at or below 1%.

## Operating points

The frozen rule is the **largest** grid tau whose benign false-block rate meets the budget. Because that rate is non-increasing in tau, the largest qualifying tau is the loosest gate meeting the budget and, whenever any grid point qualifies, it is the top of the grid; the smallest qualifying tau is the tightest gate meeting the same budget and blocks the most violations. Both are printed, the frozen one first.

| arm | mode | thinking | largest tau, false blocks <= 1% | smallest tau, false blocks <= 1% | largest tau, false blocks <= 5% | smallest tau, false blocks <= 5% |
|---|---|---|---|---|---|---|
| deepseek | M_constrained | non_think | none | none | none | none |
| deepseek | M_constrained | think_high | none | none | none | none |
| deepseek | M_free | non_think | none | none | none | none |
| deepseek | M_free | think_high | none | none | none | none |
| glm-4-9b | M_constrained | - | none | none | none | none |
| glm-4-9b | M_free | - | none | none | none | none |
| openai | M_constrained | - | none | none | 1.00 (1.2%) | 0.15 (4.0%) |
| openai | M_free | - | none | none | none | none |
| opus | M_constrained | default | none | none | 1.00 (1.3%) | 0.15 (4.1%) |
| opus | M_constrained | disabled | none | none | 1.00 (2.4%) | 0.20 (5.0%) |
| opus | M_free | default | none | none | none | none |
| opus | M_free | disabled | none | none | none | none |
| qwen3-14b | M_constrained | - | 1.00 (0.9%) | 1.00 (0.9%) | 1.00 (0.9%) | 0.15 (4.5%) |
| qwen3-14b | M_free | - | none | none | none | none |
| qwen3.6-27b-fp8 | M_constrained | - | none | none | 1.00 (2.9%) | 0.30 (2.9%) |
| qwen3.6-27b-fp8 | M_free | - | none | none | none | none |
| sol | M_constrained | none | none | none | none | none |
| sonnet | M_constrained | disabled | none | none | 1.00 (1.2%) | 0.15 (3.9%) |
| sonnet | M_free | disabled | none | none | none | none |

`none` means no grid tau meets that budget for the group: the benign false-block rate has a floor set by the schema and feasibility gates, which no value of tau can move.

### V3 separation at three tolerances

| arm | mode | thinking | V3 items | tau 0.05 | tau 0.20 | tau 0.50 |
|---|---|---|---|---|---|---|
| deepseek | M_constrained | non_think | 440 | 1 (0.2%) | 1 (0.2%) | 0 (0.0%) |
| deepseek | M_constrained | think_high | 440 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| deepseek | M_free | non_think | 440 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| deepseek | M_free | think_high | 440 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| glm-4-9b | M_constrained | - | 220 | 184 (83.6%) | 160 (72.7%) | 99 (45.0%) |
| glm-4-9b | M_free | - | 220 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| openai | M_constrained | - | 440 | 392 (89.1%) | 347 (78.9%) | 220 (50.0%) |
| openai | M_free | - | 440 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| opus | M_constrained | default | 440 | 434 (98.6%) | 398 (90.5%) | 258 (58.6%) |
| opus | M_constrained | disabled | 440 | 433 (98.4%) | 396 (90.0%) | 257 (58.4%) |
| opus | M_free | default | 440 | 1 (0.2%) | 1 (0.2%) | 1 (0.2%) |
| opus | M_free | disabled | 440 | 7 (1.6%) | 7 (1.6%) | 6 (1.4%) |
| qwen3-14b | M_constrained | - | 660 | 606 (91.8%) | 543 (82.3%) | 342 (51.8%) |
| qwen3-14b | M_free | - | 660 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| qwen3.6-27b-fp8 | M_constrained | - | 660 | 631 (95.6%) | 574 (87.0%) | 378 (57.3%) |
| qwen3.6-27b-fp8 | M_free | - | 660 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| sol | M_constrained | none | 220 | 200 (90.9%) | 181 (82.3%) | 116 (52.7%) |
| sonnet | M_constrained | disabled | 440 | 419 (95.2%) | 378 (85.9%) | 246 (55.9%) |
| sonnet | M_free | disabled | 440 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |

## Hard anchor: tau = 0.20 reproduces the accepted E1 numbers

Every number this script produces at tau = 0.20 is compared to the accepted value in the arm's own `summary.json`: the G_CERT terminal counts, the per-class block counts and rates, and the separation quadruple with its share. A mismatch exits non-zero.

| arm | mode | thinking | checks | failed | verdict |
|---|---|---|---|---|---|
| deepseek | M_constrained | non_think | 60 | 0 | PASS |
| deepseek | M_constrained | think_high | 60 | 0 | PASS |
| deepseek | M_free | non_think | 60 | 0 | PASS |
| deepseek | M_free | think_high | 60 | 0 | PASS |
| glm-4-9b | M_constrained | - | 60 | 0 | PASS |
| glm-4-9b | M_free | - | 60 | 0 | PASS |
| openai | M_constrained | - | 60 | 0 | PASS |
| openai | M_free | - | 60 | 0 | PASS |
| opus | M_constrained | default | 60 | 0 | PASS |
| opus | M_constrained | disabled | 60 | 0 | PASS |
| opus | M_free | default | 60 | 0 | PASS |
| opus | M_free | disabled | 60 | 0 | PASS |
| qwen3-14b | M_constrained | - | 60 | 0 | PASS |
| qwen3-14b | M_free | - | 60 | 0 | PASS |
| qwen3.6-27b-fp8 | M_constrained | - | 60 | 0 | PASS |
| qwen3.6-27b-fp8 | M_free | - | 60 | 0 | PASS |
| sol | M_constrained | none | 60 | 0 | PASS |
| sonnet | M_constrained | disabled | 60 | 0 | PASS |
| sonnet | M_free | disabled | 60 | 0 | PASS |

## Monotonicity: no rate rises with tau

Raising tau can only turn a `blocked_qual` into an `applied_with_certificate`, never the reverse, so every block count, the benign false-block rate and the V3/V4 separation counts must be non-increasing across the grid. Checked series by series.

| arm | mode | thinking | series checked | violations | verdict |
|---|---|---|---|---|---|
| deepseek | M_constrained | non_think | 10 | 0 | PASS |
| deepseek | M_constrained | think_high | 10 | 0 | PASS |
| deepseek | M_free | non_think | 10 | 0 | PASS |
| deepseek | M_free | think_high | 10 | 0 | PASS |
| glm-4-9b | M_constrained | - | 10 | 0 | PASS |
| glm-4-9b | M_free | - | 10 | 0 | PASS |
| openai | M_constrained | - | 10 | 0 | PASS |
| openai | M_free | - | 10 | 0 | PASS |
| opus | M_constrained | default | 10 | 0 | PASS |
| opus | M_constrained | disabled | 10 | 0 | PASS |
| opus | M_free | default | 10 | 0 | PASS |
| opus | M_free | disabled | 10 | 0 | PASS |
| qwen3-14b | M_constrained | - | 10 | 0 | PASS |
| qwen3-14b | M_free | - | 10 | 0 | PASS |
| qwen3.6-27b-fp8 | M_constrained | - | 10 | 0 | PASS |
| qwen3.6-27b-fp8 | M_free | - | 10 | 0 | PASS |
| sol | M_constrained | none | 10 | 0 | PASS |
| sonnet | M_constrained | disabled | 10 | 0 | PASS |
| sonnet | M_free | disabled | 10 | 0 | PASS |

Files: `summary.md`, `summary.json`, `curves.csv` (long format: arm, mode, thinking, tau, class, items, blocks, block_rate, false_block_rate, v3_separated, v4_separated, warranted_share; the last four are group-level and repeat on every class row of that group and tau).