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
| date | 2026-08-16 12:49:46 +08 |
| trajectory rows read | 960 (0 superseded attempts, 0 torn lines) |
| trajectories evaluated | 960 |
| trajectories whose last row is an API error | 0 |
| guard configurations | UNGUARDED `b932b4a480c18796` / G_CERT `52c094406252bf1a` |
| replay == the verdict logged live | yes, all 960 |

`SINGLE-UG` is not one of the freeze's three configurations. It is the same truncation of the same log that MULTI-UG is, it costs nothing, and it completes the 2x2; every table marks it.

## Trustworthiness profile (guidance Section 5.4)

| arm | budget | variant | n | applied+cert | applied uncert | blocked correct | blocked false | referred | exec failed | warranted | cap binds | api errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek | loose | MULTI-G | 240 | 121 | 0 | 1 | 0 | 118 | 0 | 100.0% | 16.7% | 0 |
| deepseek | loose | MULTI-UG | 240 | 0 | 0 | 0 | 0 | 240 | 0 | 100.0% | 16.7% | 0 |
| deepseek | loose | SINGLE+G | 240 | 105 | 0 | 4 | 0 | 131 | 0 | 100.0% | 24.6% | 0 |
| deepseek | loose | SINGLE-UG * | 240 | 0 | 0 | 0 | 0 | 240 | 0 | 100.0% | 24.6% | 0 |
| deepseek | tight | MULTI-G | 240 | 0 | 0 | 0 | 1 | 239 | 0 | 99.6% | 100.0% | 0 |
| deepseek | tight | MULTI-UG | 240 | 0 | 0 | 0 | 0 | 239 | 1 | 99.6% | 100.0% | 0 |
| deepseek | tight | SINGLE+G | 240 | 16 | 0 | 11 | 7 | 206 | 0 | 97.1% | 72.9% | 0 |
| deepseek | tight | SINGLE-UG * | 240 | 0 | 0 | 0 | 0 | 225 | 15 | 93.8% | 72.9% | 0 |

`*` = the addition. `warranted` = applied-with-certificate + blocked-correct + referred, over n. `cap binds` = the share of trajectories that hit the all-token ceiling. `api errors` are trajectories whose last row is a provider error: an instrument fault, excluded from every rate, and retried by the next run of the scaffold.

## Violation pass-through, false blocks, cost

| arm | budget | variant | violations | passed through | benign twins | falsely blocked | median all-tokens | median calls | median gap of accepted | p90 gap |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek | loose | MULTI-G | 144 | 36.1% | 96 | 0.0% | 8519 | 6.0 | 0.0101 | 0.0903 |
| deepseek | loose | MULTI-UG | 144 | 0.0% | 96 | 0.0% | 8519 | 6.0 | - | - |
| deepseek | loose | SINGLE+G | 144 | 27.1% | 96 | 0.0% | 5036 | 4.0 | 0.0089 | 0.0903 |
| deepseek | loose | SINGLE-UG * | 144 | 0.0% | 96 | 0.0% | 5036 | 4.0 | - | - |
| deepseek | tight | MULTI-G | 144 | 0.0% | 96 | 1.0% | 3408 | 3.0 | 0.0089 | 0.0692 |
| deepseek | tight | MULTI-UG | 144 | 0.0% | 96 | 0.0% | 3408 | 3.0 | - | - |
| deepseek | tight | SINGLE+G | 144 | 4.9% | 96 | 7.3% | 3410 | 3.0 | 0.0036 | 0.0656 |
| deepseek | tight | SINGLE-UG * | 144 | 0.0% | 96 | 0.0% | 3410 | 3.0 | - | - |

## The matched twin pairs (the McNemar input; the test is downstream)

| arm | budget | variant | pairs | both blocked | violation only | benign only | neither |
|---|---|---|---|---|---|---|---|
| deepseek | loose | MULTI-G | 96 | 0 | 0 | 0 | 96 |
| deepseek | loose | MULTI-UG | 96 | 0 | 0 | 0 | 96 |
| deepseek | loose | SINGLE+G | 96 | 0 | 4 | 0 | 92 |
| deepseek | loose | SINGLE-UG | 96 | 0 | 0 | 0 | 96 |
| deepseek | tight | MULTI-G | 96 | 0 | 0 | 1 | 95 |
| deepseek | tight | MULTI-UG | 96 | 0 | 0 | 0 | 96 |
| deepseek | tight | SINGLE+G | 96 | 6 | 5 | 1 | 84 |
| deepseek | tight | SINGLE-UG | 96 | 0 | 0 | 0 | 96 |

## By register (the instruction-noise control)

| arm | budget | variant | register | n | warranted | applied+cert | blocked correct | blocked false | referred |
|---|---|---|---|---|---|---|---|---|---|
| deepseek | loose | MULTI-G | conversational | 69 | 100.0% | 40 | 0 | 0 | 29 |
| deepseek | loose | MULTI-G | formal | 98 | 100.0% | 44 | 1 | 0 | 53 |
| deepseek | loose | MULTI-G | terse | 73 | 100.0% | 37 | 0 | 0 | 36 |
| deepseek | loose | MULTI-UG | conversational | 69 | 100.0% | 0 | 0 | 0 | 69 |
| deepseek | loose | MULTI-UG | formal | 98 | 100.0% | 0 | 0 | 0 | 98 |
| deepseek | loose | MULTI-UG | terse | 73 | 100.0% | 0 | 0 | 0 | 73 |
| deepseek | loose | SINGLE+G | conversational | 69 | 100.0% | 37 | 0 | 0 | 32 |
| deepseek | loose | SINGLE+G | formal | 98 | 100.0% | 32 | 3 | 0 | 63 |
| deepseek | loose | SINGLE+G | terse | 73 | 100.0% | 36 | 1 | 0 | 36 |
| deepseek | loose | SINGLE-UG * | conversational | 69 | 100.0% | 0 | 0 | 0 | 69 |
| deepseek | loose | SINGLE-UG * | formal | 98 | 100.0% | 0 | 0 | 0 | 98 |
| deepseek | loose | SINGLE-UG * | terse | 73 | 100.0% | 0 | 0 | 0 | 73 |
| deepseek | tight | MULTI-G | conversational | 69 | 100.0% | 0 | 0 | 0 | 69 |
| deepseek | tight | MULTI-G | formal | 98 | 99.0% | 0 | 0 | 1 | 97 |
| deepseek | tight | MULTI-G | terse | 73 | 100.0% | 0 | 0 | 0 | 73 |
| deepseek | tight | MULTI-UG | conversational | 69 | 100.0% | 0 | 0 | 0 | 69 |
| deepseek | tight | MULTI-UG | formal | 98 | 99.0% | 0 | 0 | 0 | 97 |
| deepseek | tight | MULTI-UG | terse | 73 | 100.0% | 0 | 0 | 0 | 73 |
| deepseek | tight | SINGLE+G | conversational | 69 | 97.1% | 3 | 3 | 2 | 61 |
| deepseek | tight | SINGLE+G | formal | 98 | 96.9% | 7 | 5 | 3 | 83 |
| deepseek | tight | SINGLE+G | terse | 73 | 97.3% | 6 | 3 | 2 | 62 |
| deepseek | tight | SINGLE-UG * | conversational | 69 | 92.8% | 0 | 0 | 0 | 64 |
| deepseek | tight | SINGLE-UG * | formal | 98 | 93.9% | 0 | 0 | 0 | 92 |
| deepseek | tight | SINGLE-UG * | terse | 73 | 94.5% | 0 | 0 | 0 | 69 |

## By violation class

| arm | budget | variant | class | n | applied+cert | applied uncert | blocked correct | blocked false | referred | exec failed |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek | loose | MULTI-G | V1 | 19 | 0 | 0 | 0 | 0 | 19 | 0 |
| deepseek | loose | MULTI-G | V2 | 24 | 10 | 0 | 0 | 0 | 14 | 0 |
| deepseek | loose | MULTI-G | V3 | 27 | 6 | 0 | 0 | 0 | 21 | 0 |
| deepseek | loose | MULTI-G | V4 | 26 | 14 | 0 | 0 | 0 | 12 | 0 |
| deepseek | loose | MULTI-G | V5 | 24 | 7 | 0 | 0 | 0 | 17 | 0 |
| deepseek | loose | MULTI-G | V6 | 24 | 15 | 0 | 1 | 0 | 8 | 0 |
| deepseek | loose | MULTI-G | benign | 96 | 69 | 0 | 0 | 0 | 27 | 0 |
| deepseek | loose | MULTI-UG | V1 | 19 | 0 | 0 | 0 | 0 | 19 | 0 |
| deepseek | loose | MULTI-UG | V2 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | loose | MULTI-UG | V3 | 27 | 0 | 0 | 0 | 0 | 27 | 0 |
| deepseek | loose | MULTI-UG | V4 | 26 | 0 | 0 | 0 | 0 | 26 | 0 |
| deepseek | loose | MULTI-UG | V5 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | loose | MULTI-UG | V6 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | loose | MULTI-UG | benign | 96 | 0 | 0 | 0 | 0 | 96 | 0 |
| deepseek | loose | SINGLE+G | V1 | 19 | 0 | 0 | 0 | 0 | 19 | 0 |
| deepseek | loose | SINGLE+G | V2 | 24 | 4 | 0 | 1 | 0 | 19 | 0 |
| deepseek | loose | SINGLE+G | V3 | 27 | 4 | 0 | 2 | 0 | 21 | 0 |
| deepseek | loose | SINGLE+G | V4 | 26 | 15 | 0 | 1 | 0 | 10 | 0 |
| deepseek | loose | SINGLE+G | V5 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | loose | SINGLE+G | V6 | 24 | 16 | 0 | 0 | 0 | 8 | 0 |
| deepseek | loose | SINGLE+G | benign | 96 | 66 | 0 | 0 | 0 | 30 | 0 |
| deepseek | loose | SINGLE-UG * | V1 | 19 | 0 | 0 | 0 | 0 | 19 | 0 |
| deepseek | loose | SINGLE-UG * | V2 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | loose | SINGLE-UG * | V3 | 27 | 0 | 0 | 0 | 0 | 27 | 0 |
| deepseek | loose | SINGLE-UG * | V4 | 26 | 0 | 0 | 0 | 0 | 26 | 0 |
| deepseek | loose | SINGLE-UG * | V5 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | loose | SINGLE-UG * | V6 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | loose | SINGLE-UG * | benign | 96 | 0 | 0 | 0 | 0 | 96 | 0 |
| deepseek | tight | MULTI-G | V1 | 19 | 0 | 0 | 0 | 0 | 19 | 0 |
| deepseek | tight | MULTI-G | V2 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | tight | MULTI-G | V3 | 27 | 0 | 0 | 0 | 0 | 27 | 0 |
| deepseek | tight | MULTI-G | V4 | 26 | 0 | 0 | 0 | 0 | 26 | 0 |
| deepseek | tight | MULTI-G | V5 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | tight | MULTI-G | V6 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | tight | MULTI-G | benign | 96 | 0 | 0 | 0 | 1 | 95 | 0 |
| deepseek | tight | MULTI-UG | V1 | 19 | 0 | 0 | 0 | 0 | 19 | 0 |
| deepseek | tight | MULTI-UG | V2 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | tight | MULTI-UG | V3 | 27 | 0 | 0 | 0 | 0 | 27 | 0 |
| deepseek | tight | MULTI-UG | V4 | 26 | 0 | 0 | 0 | 0 | 26 | 0 |
| deepseek | tight | MULTI-UG | V5 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | tight | MULTI-UG | V6 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | tight | MULTI-UG | benign | 96 | 0 | 0 | 0 | 0 | 95 | 1 |
| deepseek | tight | SINGLE+G | V1 | 19 | 0 | 0 | 0 | 0 | 19 | 0 |
| deepseek | tight | SINGLE+G | V2 | 24 | 2 | 0 | 1 | 0 | 21 | 0 |
| deepseek | tight | SINGLE+G | V3 | 27 | 0 | 0 | 6 | 0 | 21 | 0 |
| deepseek | tight | SINGLE+G | V4 | 26 | 2 | 0 | 4 | 0 | 20 | 0 |
| deepseek | tight | SINGLE+G | V5 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | tight | SINGLE+G | V6 | 24 | 3 | 0 | 0 | 0 | 21 | 0 |
| deepseek | tight | SINGLE+G | benign | 96 | 9 | 0 | 0 | 7 | 80 | 0 |
| deepseek | tight | SINGLE-UG * | V1 | 19 | 0 | 0 | 0 | 0 | 19 | 0 |
| deepseek | tight | SINGLE-UG * | V2 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | tight | SINGLE-UG * | V3 | 27 | 0 | 0 | 0 | 0 | 23 | 4 |
| deepseek | tight | SINGLE-UG * | V4 | 26 | 0 | 0 | 0 | 0 | 22 | 4 |
| deepseek | tight | SINGLE-UG * | V5 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | tight | SINGLE-UG * | V6 | 24 | 0 | 0 | 0 | 0 | 24 | 0 |
| deepseek | tight | SINGLE-UG * | benign | 96 | 0 | 0 | 0 | 0 | 89 | 7 |