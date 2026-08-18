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
| date | 2026-08-12 00:18:00 +08 |
| sweep version | l1-e2-tau-sweep-1 |
| evaluated arms swept | openai, qwen3-14b, qwen3.6-27b-fp8 |
| source directories | `/home/ziheng/PaperL1/results/e1_eval_gpt54mini`<br>`/home/ziheng/PaperL1/results/e1_eval_qwen14b`<br>`/home/ziheng/PaperL1/results/e1_eval_qwen27b` |
| verdict rows read | 32000 |
| groups (arm x mode x thinking) | 6 |
| tau grid | 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00 |
| anchor tau | 0.20 |
| anchor checks | 360 of 360 pass |
| monotonicity checks | 60 of 60 pass |
| wall | 0.55 s |

Pure post-processing: no model was called, no GPU was held, and nothing was replayed or dispatched. Tau enters the guard only as the final `gap <= tau` comparison at stage 3, and every G_CERT verdict row already records its certified gap, so the whole sweep is arithmetic over the frozen verdict logs.

## How each terminal was recomputed

| recorded G_CERT row | terminal at tolerance tau | rows |
|---|---|---|
| `blocked_schema` or `blocked_feas` | unchanged (the proposal never reached the quality gate) | 16863 |
| carries a certificate gap | `blocked_qual` if gap > tau, else `applied_with_certificate` | 15137 |
| no certificate gap and no early block | kept exactly as recorded (`lb_unavailable` blocks and `execution_failed` rows are tau-invariant) | 0 |

The third row is empty in every arm swept here: no evaluated proposal reached stage 3 without producing a certificate, and no arm carries an instrument fault, so no verdict had to be carried through by fiat.

Rows with an `infra_error` finding are instrument faults, never guard decisions, and are excluded from every rate, per the E1 evaluator's convention (0 such rows under G_CERT across all arms). G_FEAS verdicts are tau-invariant, so the separation counts reuse them unchanged.

The **warranted-outcome share** is the guidance's warranted-outcome rate (`L1_Complete_Guidance.md`, Section 5.4: the fraction of instructions whose disposition carries a machine-checkable justification, a certificate on applied proposals or a matched violation label on blocks). No module in the codebase computes it, so the operational reading here is the freeze's: a row counts as warranted when it ends `applied_with_certificate`, or when it is blocked and its item carries an injected violation label (`primary_class` other than `benign`). E1 has no referral arm, so the third disposition contributes nothing. Denominator: all rows of the group eligible under G_CERT.

What that reading counts, stated so no reader has to infer it: a violation item blocked at the schema stage is warranted here, even though the block was triggered by the shape of the proposal rather than by the injected violation. That is why the M_free groups sit near 60%, which is the share of violation items in the suite: almost every row is schema-blocked, and the violation ones therefore count as warranted while the benign ones do not. A stricter reading, requiring the blocking finding code to match the injected violation subclass, is not implemented anywhere in the codebase and is not used here.

## Curves per arm, mode and thinking (pooled over repeats)

### openai - M_constrained - thinking -

4000 rows pooled over repeats 0, 1; source `/home/ziheng/PaperL1/results/e1_eval_gpt54mini`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 247/320 (77.2%) | 312/400 (78.0%) | 404/440 (91.8%) | 143/440 (32.5%) | 192/400 (48.0%) | 157/400 (39.2%) | 544/1600 (34.0%) | 34.0% | 397 | 140 | 86.4% |
| 0.05 | 237/320 (74.1%) | 295/400 (73.8%) | 394/440 (89.5%) | 87/440 (19.8%) | 140/400 (35.0%) | 97/400 (24.2%) | 311/1600 (19.4%) | 19.4% | 387 | 84 | 92.2% |
| 0.10 | 233/320 (72.8%) | 275/400 (68.8%) | 368/440 (83.6%) | 33/440 (7.5%) | 97/400 (24.2%) | 43/400 (10.8%) | 135/1600 (8.4%) | 8.4% | 361 | 30 | 96.6% |
| 0.15 | 230/320 (71.9%) | 271/400 (67.8%) | 363/440 (82.5%) | 15/440 (3.4%) | 80/400 (20.0%) | 21/400 (5.2%) | 65/1600 (4.1%) | 4.1% | 356 | 12 | 98.4% |
| 0.20 | 230/320 (71.9%) | 271/400 (67.8%) | 349/440 (79.3%) | 15/440 (3.4%) | 80/400 (20.0%) | 19/400 (4.8%) | 63/1600 (3.9%) | 3.9% | 342 | 12 | 98.4% |
| 0.30 | 229/320 (71.6%) | 264/400 (66.0%) | 305/440 (69.3%) | 3/440 (0.7%) | 68/400 (17.0%) | 7/400 (1.8%) | 21/1600 (1.3%) | 1.3% | 298 | 0 | 99.5% |
| 0.50 | 229/320 (71.6%) | 264/400 (66.0%) | 223/440 (50.7%) | 3/440 (0.7%) | 65/400 (16.2%) | 6/400 (1.5%) | 21/1600 (1.3%) | 1.3% | 216 | 0 | 99.5% |
| 1.00 | 229/320 (71.6%) | 264/400 (66.0%) | 105/440 (23.9%) | 3/440 (0.7%) | 65/400 (16.2%) | 6/400 (1.5%) | 21/1600 (1.3%) | 1.3% | 98 | 0 | 99.5% |

What the curve shows: Benign false blocks run 34.0% at tau 0.02 to 1.3% at tau 1.00, and 3.9% at tau 0.20. V3 separation runs 397 of 440 items at tau 0.02 to 98 at tau 1.00, and 342 at tau 0.20. V4 separation runs 140 to 0, and is 12 at tau 0.20. The warranted-outcome share peaks at 99.5%, first reached at tau 0.30, and is 98.4% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

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

### qwen3-14b - M_constrained - thinking -

6000 rows pooled over repeats 0, 1, 2; source `/home/ziheng/PaperL1/results/e1_eval_qwen14b`.

| tau | V1 blocked | V2 blocked | V3 blocked | V4 blocked | V5 blocked | V6 blocked | benign blocked | benign false-block rate | V3 separated | V4 separated | warranted share |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.02 | 349/480 (72.7%) | 467/600 (77.8%) | 621/660 (94.1%) | 235/660 (35.6%) | 239/600 (39.8%) | 269/600 (44.8%) | 835/2400 (34.8%) | 34.8% | 618 | 228 | 86.1% |
| 0.05 | 341/480 (71.0%) | 443/600 (73.8%) | 609/660 (92.3%) | 145/660 (22.0%) | 146/600 (24.3%) | 191/600 (31.8%) | 475/2400 (19.8%) | 19.8% | 606 | 138 | 92.1% |
| 0.10 | 323/480 (67.3%) | 413/600 (68.8%) | 573/660 (86.8%) | 67/660 (10.2%) | 77/600 (12.8%) | 116/600 (19.3%) | 220/2400 (9.2%) | 9.2% | 570 | 60 | 96.3% |
| 0.15 | 320/480 (66.7%) | 395/600 (65.8%) | 567/660 (85.9%) | 40/660 (6.1%) | 45/600 (7.5%) | 81/600 (13.5%) | 114/2400 (4.8%) | 4.8% | 564 | 33 | 98.1% |
| 0.20 | 320/480 (66.7%) | 392/600 (65.3%) | 546/660 (82.7%) | 40/660 (6.1%) | 42/600 (7.0%) | 75/600 (12.5%) | 111/2400 (4.6%) | 4.6% | 543 | 33 | 98.2% |
| 0.30 | 314/480 (65.4%) | 380/600 (63.3%) | 477/660 (72.3%) | 22/660 (3.3%) | 18/600 (3.0%) | 54/600 (9.0%) | 42/2400 (1.8%) | 1.8% | 474 | 15 | 99.3% |
| 0.50 | 314/480 (65.4%) | 377/600 (62.8%) | 345/660 (52.3%) | 22/660 (3.3%) | 18/600 (3.0%) | 54/600 (9.0%) | 36/2400 (1.5%) | 1.5% | 342 | 15 | 99.4% |
| 1.00 | 311/480 (64.8%) | 377/600 (62.8%) | 156/660 (23.6%) | 22/660 (3.3%) | 18/600 (3.0%) | 54/600 (9.0%) | 28/2400 (1.2%) | 1.2% | 153 | 15 | 99.5% |

What the curve shows: Benign false blocks run 34.8% at tau 0.02 to 1.2% at tau 1.00, and 4.6% at tau 0.20. V3 separation runs 618 of 660 items at tau 0.02 to 153 at tau 1.00, and 543 at tau 0.20. V4 separation runs 228 to 15, and is 33 at tau 0.20. The warranted-outcome share peaks at 99.5%, first reached at tau 1.00, and is 98.2% at tau 0.20. No grid tau holds benign false blocks at or below 1%.

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
| 0.02 | 356/480 (74.2%) | 456/600 (76.0%) | 643/660 (97.4%) | 216/660 (32.7%) | 227/600 (37.8%) | 236/600 (39.3%) | 839/2400 (35.0%) | 35.0% | 640 | 216 | 86.0% |
| 0.05 | 344/480 (71.7%) | 433/600 (72.2%) | 634/660 (96.1%) | 126/660 (19.1%) | 128/600 (21.3%) | 147/600 (24.5%) | 497/2400 (20.7%) | 20.7% | 631 | 126 | 91.7% |
| 0.10 | 339/480 (70.6%) | 402/600 (67.0%) | 604/660 (91.5%) | 45/660 (6.8%) | 54/600 (9.0%) | 66/600 (11.0%) | 243/2400 (10.1%) | 10.1% | 601 | 45 | 96.0% |
| 0.15 | 333/480 (69.4%) | 393/600 (65.5%) | 598/660 (90.6%) | 18/660 (2.7%) | 24/600 (4.0%) | 33/600 (5.5%) | 135/2400 (5.6%) | 5.6% | 595 | 18 | 97.8% |
| 0.20 | 333/480 (69.4%) | 393/600 (65.5%) | 577/660 (87.4%) | 18/660 (2.7%) | 24/600 (4.0%) | 30/600 (5.0%) | 132/2400 (5.5%) | 5.5% | 574 | 18 | 97.8% |
| 0.30 | 330/480 (68.8%) | 384/600 (64.0%) | 508/660 (77.0%) | 0/660 (0.0%) | 3/600 (0.5%) | 12/600 (2.0%) | 69/2400 (2.9%) | 2.9% | 505 | 0 | 98.9% |
| 0.50 | 330/480 (68.8%) | 384/600 (64.0%) | 381/660 (57.7%) | 0/660 (0.0%) | 3/600 (0.5%) | 12/600 (2.0%) | 69/2400 (2.9%) | 2.9% | 378 | 0 | 98.9% |
| 1.00 | 330/480 (68.8%) | 384/600 (64.0%) | 177/660 (26.8%) | 0/660 (0.0%) | 3/600 (0.5%) | 12/600 (2.0%) | 69/2400 (2.9%) | 2.9% | 174 | 0 | 98.9% |

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

## Operating points

The frozen rule is the **largest** grid tau whose benign false-block rate meets the budget. Because that rate is non-increasing in tau, the largest qualifying tau is the loosest gate meeting the budget and, whenever any grid point qualifies, it is the top of the grid; the smallest qualifying tau is the tightest gate meeting the same budget and blocks the most violations. Both are printed, the frozen one first.

| arm | mode | thinking | largest tau, false blocks <= 1% | smallest tau, false blocks <= 1% | largest tau, false blocks <= 5% | smallest tau, false blocks <= 5% |
|---|---|---|---|---|---|---|
| openai | M_constrained | - | none | none | 1.00 (1.3%) | 0.15 (4.1%) |
| openai | M_free | - | none | none | none | none |
| qwen3-14b | M_constrained | - | none | none | 1.00 (1.2%) | 0.15 (4.8%) |
| qwen3-14b | M_free | - | none | none | none | none |
| qwen3.6-27b-fp8 | M_constrained | - | none | none | 1.00 (2.9%) | 0.30 (2.9%) |
| qwen3.6-27b-fp8 | M_free | - | none | none | none | none |

`none` means no grid tau meets that budget for the group: the benign false-block rate has a floor set by the schema and feasibility gates, which no value of tau can move.

### V3 separation at three tolerances

| arm | mode | thinking | V3 items | tau 0.05 | tau 0.20 | tau 0.50 |
|---|---|---|---|---|---|---|
| openai | M_constrained | - | 440 | 387 (88.0%) | 342 (77.7%) | 216 (49.1%) |
| openai | M_free | - | 440 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| qwen3-14b | M_constrained | - | 660 | 606 (91.8%) | 543 (82.3%) | 342 (51.8%) |
| qwen3-14b | M_free | - | 660 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| qwen3.6-27b-fp8 | M_constrained | - | 660 | 631 (95.6%) | 574 (87.0%) | 378 (57.3%) |
| qwen3.6-27b-fp8 | M_free | - | 660 | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |

## Hard anchor: tau = 0.20 reproduces the accepted E1 numbers

Every number this script produces at tau = 0.20 is compared to the accepted value in the arm's own `summary.json`: the G_CERT terminal counts, the per-class block counts and rates, and the separation quadruple with its share. A mismatch exits non-zero.

| arm | mode | thinking | checks | failed | verdict |
|---|---|---|---|---|---|
| openai | M_constrained | - | 60 | 0 | PASS |
| openai | M_free | - | 60 | 0 | PASS |
| qwen3-14b | M_constrained | - | 60 | 0 | PASS |
| qwen3-14b | M_free | - | 60 | 0 | PASS |
| qwen3.6-27b-fp8 | M_constrained | - | 60 | 0 | PASS |
| qwen3.6-27b-fp8 | M_free | - | 60 | 0 | PASS |

## Monotonicity: no rate rises with tau

Raising tau can only turn a `blocked_qual` into an `applied_with_certificate`, never the reverse, so every block count, the benign false-block rate and the V3/V4 separation counts must be non-increasing across the grid. Checked series by series.

| arm | mode | thinking | series checked | violations | verdict |
|---|---|---|---|---|---|
| openai | M_constrained | - | 10 | 0 | PASS |
| openai | M_free | - | 10 | 0 | PASS |
| qwen3-14b | M_constrained | - | 10 | 0 | PASS |
| qwen3-14b | M_free | - | 10 | 0 | PASS |
| qwen3.6-27b-fp8 | M_constrained | - | 10 | 0 | PASS |
| qwen3.6-27b-fp8 | M_free | - | 10 | 0 | PASS |

Files: `summary.md`, `summary.json`, `curves.csv` (long format: arm, mode, thinking, tau, class, items, blocks, block_rate, false_block_rate, v3_separated, v4_separated, warranted_share; the last four are group-level and repeat on every class row of that group and tau).