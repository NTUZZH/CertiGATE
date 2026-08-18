# E3 replay: guard variants over the logged trajectories

================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules), answered before the run
================================================================================
1. PURPOSE.  Turn one E3 trajectory log into every E3 number: the terminal-state
   profile per arm x budget level x guard variant, the warranted-outcome rate,
   the violation pass-through rate, the conditional certified gap, the
   cap-binding share, the 120 twin pairs' block and false-block counts, and the
   register-stratified split.  These are the agent-layer family of the paper.
2. EXPECTED RESULT.  SINGLE+G and MULTI-G differ little at a matched budget, or
   MULTI-G is behind once its inter-agent messages are charged: that is the
   adjudication E3 exists for, and either direction is a result.  A DEFECT, not
   a finding: a variant whose verdicts disagree with the guard verdict logged
   live (printed as replay mismatches, and expected to be zero), a cap that
   binds in one pipeline and not the other at the same level, or trajectories
   with no first final at all.
3. CONTAMINATION.  No model, no GPU, no network.  The guard is deterministic, so
   this script reproduces every number from the same log.  The output directory
   must be empty unless --force.  The last row per (arm, budget level, pipeline,
   repeat, item_id) is the one that counts; earlier rows are superseded attempts
   and error rows are reported separately, never mixed into a rate.
4. DATA ACCURACY.  Suite sha256 and schema sha256 asserted fatal at start.  The
   guard configuration is E1's own object (e1_evaluate.guard_configs), and its
   hash is printed; a trajectory whose dispatch seed differs from it is fatal
   rather than silently evaluated at seed 0.
================================================================================

## Run

| field | value |
|---|---|
| date | 2026-08-16 12:45:10 +08 |
| trajectory rows read | 1920 (0 superseded attempts, 0 torn lines) |
| trajectories evaluated | 1920 |
| trajectories whose last row is an API error | 0 |
| guard configurations | UNGUARDED `b932b4a480c18796` / G_CERT `52c094406252bf1a` |
| replay == the verdict logged live | NO: 14 mismatch(es), e.g. {'source': 'first_final', 'logged': '8274d5158c0d99253bbb6b5c7f6a3a7203df00fb8f2cee06ef43ac0ce2e3685c', 'replayed': '48e308d10c4c4e207fa665e11227aa4f90808850cdb45973472f4892860153da'} |

`SINGLE-UG` is not one of the freeze's three configurations. It is the same truncation of the same log that MULTI-UG is, it costs nothing, and it completes the 2x2; every table marks it.

## Trustworthiness profile (guidance Section 5.4)

| arm | budget | variant | n | applied+cert | applied uncert | blocked correct | blocked false | referred | exec failed | warranted | cap binds | api errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen14b | loose | MULTI-G | 480 | 336 | 0 | 5 | 2 | 137 | 0 | 99.6% | 4.2% | 0 |
| qwen14b | loose | MULTI-UG | 480 | 0 | 392 | 0 | 0 | 45 | 43 | 9.4% | 4.2% | 0 |
| qwen14b | loose | SINGLE+G | 480 | 318 | 0 | 8 | 2 | 152 | 0 | 99.6% | 3.8% | 0 |
| qwen14b | loose | SINGLE-UG * | 480 | 0 | 376 | 0 | 0 | 72 | 32 | 15.0% | 3.8% | 0 |
| qwen14b | tight | MULTI-G | 480 | 9 | 0 | 0 | 1 | 470 | 0 | 99.8% | 100.0% | 0 |
| qwen14b | tight | MULTI-UG | 480 | 0 | 10 | 0 | 0 | 470 | 0 | 97.9% | 100.0% | 0 |
| qwen14b | tight | SINGLE+G | 480 | 171 | 0 | 61 | 5 | 243 | 0 | 99.0% | 57.1% | 0 |
| qwen14b | tight | SINGLE-UG * | 480 | 0 | 216 | 0 | 0 | 241 | 23 | 50.2% | 57.1% | 0 |

`*` = the addition. `warranted` = applied-with-certificate + blocked-correct + referred, over n. `cap binds` = the share of trajectories that hit the all-token ceiling. `api errors` are trajectories whose last row is a provider error: an instrument fault, excluded from every rate, and retried by the next run of the scaffold.

## Violation pass-through, false blocks, cost

| arm | budget | variant | violations | passed through | benign twins | falsely blocked | median all-tokens | median calls | median gap of accepted | p90 gap |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen14b | loose | MULTI-G | 288 | 55.9% | 192 | 1.0% | 10284 | 6.0 | 0.0089 | 0.1061 |
| qwen14b | loose | MULTI-UG | 288 | 73.6% | 192 | 0.0% | 10284 | 6.0 | - | - |
| qwen14b | loose | SINGLE+G | 288 | 47.2% | 192 | 1.0% | 4434 | 3.0 | 0.0089 | 0.1061 |
| qwen14b | loose | SINGLE-UG * | 288 | 66.0% | 192 | 0.0% | 4434 | 3.0 | - | - |
| qwen14b | tight | MULTI-G | 288 | 2.1% | 192 | 0.5% | 3646 | 2.0 | 0.0089 | 0.0903 |
| qwen14b | tight | MULTI-UG | 288 | 2.1% | 192 | 0.0% | 3646 | 2.0 | - | - |
| qwen14b | tight | SINGLE+G | 288 | 25.0% | 192 | 2.6% | 3005 | 2.0 | 0.0101 | 0.1351 |
| qwen14b | tight | SINGLE-UG * | 288 | 39.2% | 192 | 0.0% | 3005 | 2.0 | - | - |

## The matched twin pairs (the McNemar input; the test is downstream)

| arm | budget | variant | pairs | both blocked | violation only | benign only | neither |
|---|---|---|---|---|---|---|---|
| qwen14b | loose | MULTI-G | 96 | 1 | 2 | 0 | 93 |
| qwen14b | loose | MULTI-UG | 96 | 0 | 0 | 0 | 96 |
| qwen14b | loose | SINGLE+G | 96 | 1 | 2 | 0 | 93 |
| qwen14b | loose | SINGLE-UG | 96 | 0 | 0 | 0 | 96 |
| qwen14b | tight | MULTI-G | 96 | 0 | 0 | 1 | 95 |
| qwen14b | tight | MULTI-UG | 96 | 0 | 0 | 0 | 96 |
| qwen14b | tight | SINGLE+G | 96 | 1 | 29 | 1 | 65 |
| qwen14b | tight | SINGLE-UG | 96 | 0 | 0 | 0 | 96 |

## By register (the instruction-noise control)

| arm | budget | variant | register | n | warranted | applied+cert | blocked correct | blocked false | referred |
|---|---|---|---|---|---|---|---|---|---|
| qwen14b | loose | MULTI-G | conversational | 138 | 100.0% | 104 | 0 | 0 | 34 |
| qwen14b | loose | MULTI-G | formal | 196 | 100.0% | 130 | 3 | 0 | 63 |
| qwen14b | loose | MULTI-G | terse | 146 | 98.6% | 102 | 2 | 2 | 40 |
| qwen14b | loose | MULTI-UG | conversational | 138 | 7.2% | 0 | 0 | 0 | 10 |
| qwen14b | loose | MULTI-UG | formal | 196 | 12.2% | 0 | 0 | 0 | 24 |
| qwen14b | loose | MULTI-UG | terse | 146 | 7.5% | 0 | 0 | 0 | 11 |
| qwen14b | loose | SINGLE+G | conversational | 138 | 100.0% | 98 | 0 | 0 | 40 |
| qwen14b | loose | SINGLE+G | formal | 196 | 100.0% | 128 | 6 | 0 | 62 |
| qwen14b | loose | SINGLE+G | terse | 146 | 98.6% | 92 | 2 | 2 | 50 |
| qwen14b | loose | SINGLE-UG * | conversational | 138 | 15.9% | 0 | 0 | 0 | 22 |
| qwen14b | loose | SINGLE-UG * | formal | 196 | 18.4% | 0 | 0 | 0 | 36 |
| qwen14b | loose | SINGLE-UG * | terse | 146 | 9.6% | 0 | 0 | 0 | 14 |
| qwen14b | tight | MULTI-G | conversational | 138 | 99.3% | 0 | 0 | 1 | 137 |
| qwen14b | tight | MULTI-G | formal | 196 | 100.0% | 5 | 0 | 0 | 191 |
| qwen14b | tight | MULTI-G | terse | 146 | 100.0% | 4 | 0 | 0 | 142 |
| qwen14b | tight | MULTI-UG | conversational | 138 | 99.3% | 0 | 0 | 0 | 137 |
| qwen14b | tight | MULTI-UG | formal | 196 | 97.4% | 0 | 0 | 0 | 191 |
| qwen14b | tight | MULTI-UG | terse | 146 | 97.3% | 0 | 0 | 0 | 142 |
| qwen14b | tight | SINGLE+G | conversational | 138 | 97.8% | 30 | 12 | 3 | 93 |
| qwen14b | tight | SINGLE+G | formal | 196 | 100.0% | 73 | 19 | 0 | 104 |
| qwen14b | tight | SINGLE+G | terse | 146 | 98.6% | 68 | 30 | 2 | 46 |
| qwen14b | tight | SINGLE-UG * | conversational | 138 | 67.4% | 0 | 0 | 0 | 93 |
| qwen14b | tight | SINGLE-UG * | formal | 196 | 53.1% | 0 | 0 | 0 | 104 |
| qwen14b | tight | SINGLE-UG * | terse | 146 | 30.1% | 0 | 0 | 0 | 44 |

## By violation class

| arm | budget | variant | class | n | applied+cert | applied uncert | blocked correct | blocked false | referred | exec failed |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen14b | loose | MULTI-G | V1 | 38 | 13 | 0 | 0 | 0 | 25 | 0 |
| qwen14b | loose | MULTI-G | V2 | 48 | 20 | 0 | 0 | 0 | 28 | 0 |
| qwen14b | loose | MULTI-G | V3 | 54 | 10 | 0 | 3 | 0 | 41 | 0 |
| qwen14b | loose | MULTI-G | V4 | 52 | 47 | 0 | 2 | 0 | 3 | 0 |
| qwen14b | loose | MULTI-G | V5 | 48 | 26 | 0 | 0 | 0 | 22 | 0 |
| qwen14b | loose | MULTI-G | V6 | 48 | 45 | 0 | 0 | 0 | 3 | 0 |
| qwen14b | loose | MULTI-G | benign | 192 | 175 | 0 | 0 | 2 | 15 | 0 |
| qwen14b | loose | MULTI-UG | V1 | 38 | 0 | 14 | 0 | 0 | 4 | 20 |
| qwen14b | loose | MULTI-UG | V2 | 48 | 0 | 26 | 0 | 0 | 5 | 17 |
| qwen14b | loose | MULTI-UG | V3 | 54 | 0 | 50 | 0 | 0 | 3 | 1 |
| qwen14b | loose | MULTI-UG | V4 | 52 | 0 | 49 | 0 | 0 | 3 | 0 |
| qwen14b | loose | MULTI-UG | V5 | 48 | 0 | 26 | 0 | 0 | 20 | 2 |
| qwen14b | loose | MULTI-UG | V6 | 48 | 0 | 47 | 0 | 0 | 1 | 0 |
| qwen14b | loose | MULTI-UG | benign | 192 | 0 | 180 | 0 | 0 | 9 | 3 |
| qwen14b | loose | SINGLE+G | V1 | 38 | 8 | 0 | 0 | 0 | 30 | 0 |
| qwen14b | loose | SINGLE+G | V2 | 48 | 16 | 0 | 0 | 0 | 32 | 0 |
| qwen14b | loose | SINGLE+G | V3 | 54 | 10 | 0 | 4 | 0 | 40 | 0 |
| qwen14b | loose | SINGLE+G | V4 | 52 | 48 | 0 | 2 | 0 | 2 | 0 |
| qwen14b | loose | SINGLE+G | V5 | 48 | 14 | 0 | 0 | 0 | 34 | 0 |
| qwen14b | loose | SINGLE+G | V6 | 48 | 40 | 0 | 2 | 0 | 6 | 0 |
| qwen14b | loose | SINGLE+G | benign | 192 | 182 | 0 | 0 | 2 | 8 | 0 |
| qwen14b | loose | SINGLE-UG * | V1 | 38 | 0 | 12 | 0 | 0 | 16 | 10 |
| qwen14b | loose | SINGLE-UG * | V2 | 48 | 0 | 22 | 0 | 0 | 6 | 20 |
| qwen14b | loose | SINGLE-UG * | V3 | 54 | 0 | 52 | 0 | 0 | 2 | 0 |
| qwen14b | loose | SINGLE-UG * | V4 | 52 | 0 | 50 | 0 | 0 | 2 | 0 |
| qwen14b | loose | SINGLE-UG * | V5 | 48 | 0 | 14 | 0 | 0 | 34 | 0 |
| qwen14b | loose | SINGLE-UG * | V6 | 48 | 0 | 40 | 0 | 0 | 6 | 2 |
| qwen14b | loose | SINGLE-UG * | benign | 192 | 0 | 186 | 0 | 0 | 6 | 0 |
| qwen14b | tight | MULTI-G | V1 | 38 | 0 | 0 | 0 | 0 | 38 | 0 |
| qwen14b | tight | MULTI-G | V2 | 48 | 0 | 0 | 0 | 0 | 48 | 0 |
| qwen14b | tight | MULTI-G | V3 | 54 | 0 | 0 | 0 | 0 | 54 | 0 |
| qwen14b | tight | MULTI-G | V4 | 52 | 0 | 0 | 0 | 0 | 52 | 0 |
| qwen14b | tight | MULTI-G | V5 | 48 | 2 | 0 | 0 | 0 | 46 | 0 |
| qwen14b | tight | MULTI-G | V6 | 48 | 4 | 0 | 0 | 0 | 44 | 0 |
| qwen14b | tight | MULTI-G | benign | 192 | 3 | 0 | 0 | 1 | 188 | 0 |
| qwen14b | tight | MULTI-UG | V1 | 38 | 0 | 0 | 0 | 0 | 38 | 0 |
| qwen14b | tight | MULTI-UG | V2 | 48 | 0 | 0 | 0 | 0 | 48 | 0 |
| qwen14b | tight | MULTI-UG | V3 | 54 | 0 | 0 | 0 | 0 | 54 | 0 |
| qwen14b | tight | MULTI-UG | V4 | 52 | 0 | 0 | 0 | 0 | 52 | 0 |
| qwen14b | tight | MULTI-UG | V5 | 48 | 0 | 2 | 0 | 0 | 46 | 0 |
| qwen14b | tight | MULTI-UG | V6 | 48 | 0 | 4 | 0 | 0 | 44 | 0 |
| qwen14b | tight | MULTI-UG | benign | 192 | 0 | 4 | 0 | 0 | 188 | 0 |
| qwen14b | tight | SINGLE+G | V1 | 38 | 2 | 0 | 10 | 0 | 26 | 0 |
| qwen14b | tight | SINGLE+G | V2 | 48 | 4 | 0 | 18 | 0 | 26 | 0 |
| qwen14b | tight | SINGLE+G | V3 | 54 | 2 | 0 | 29 | 0 | 23 | 0 |
| qwen14b | tight | SINGLE+G | V4 | 52 | 30 | 0 | 2 | 0 | 20 | 0 |
| qwen14b | tight | SINGLE+G | V5 | 48 | 12 | 0 | 0 | 0 | 36 | 0 |
| qwen14b | tight | SINGLE+G | V6 | 48 | 22 | 0 | 2 | 0 | 24 | 0 |
| qwen14b | tight | SINGLE+G | benign | 192 | 99 | 0 | 0 | 5 | 88 | 0 |
| qwen14b | tight | SINGLE-UG * | V1 | 38 | 0 | 6 | 0 | 0 | 24 | 8 |
| qwen14b | tight | SINGLE-UG * | V2 | 48 | 0 | 8 | 0 | 0 | 26 | 14 |
| qwen14b | tight | SINGLE-UG * | V3 | 54 | 0 | 31 | 0 | 0 | 23 | 0 |
| qwen14b | tight | SINGLE-UG * | V4 | 52 | 0 | 32 | 0 | 0 | 20 | 0 |
| qwen14b | tight | SINGLE-UG * | V5 | 48 | 0 | 12 | 0 | 0 | 36 | 0 |
| qwen14b | tight | SINGLE-UG * | V6 | 48 | 0 | 24 | 0 | 0 | 24 | 0 |
| qwen14b | tight | SINGLE-UG * | benign | 192 | 0 | 103 | 0 | 0 | 88 | 1 |