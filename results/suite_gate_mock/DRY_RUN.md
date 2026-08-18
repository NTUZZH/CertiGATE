# Suite acceptance gate (MOCK / DRY RUN)

================================================================================
FOUR LAUNCH QUESTIONS (global CLAUDE.md experiment rules), answered before the run
================================================================================
1. PURPOSE. The suite acceptance gate: does the certified stage catch proposals
   the feasibility stage passes? The number that decides it is the count of
   V3/V4 items with G_FEAS = applied and G_CERT = blocked. It gates every paid
   grid (guidance Section 8) and lands in the acceptance module's "Suite
   acceptance gate: V3/V4 separation shown on >= 1 model" row.
2. EXPECTED RESULT. Non-zero, concentrated in V3 (all 220 items degrade the
   schedule by construction, median 272 weighted business hours) and in the V4
   trap type reorder_direction_flipped (50 of the 55 quality-visible
   candidates). The other six V4 trap types are certificate-invisible by
   construction and are expected to contribute nothing: that is a finding to
   report, not a defect. If the count is zero the gate FAILS and no grid runs.
   If V3 separates but no V4 does, the gate passes on V3 and the V4 split is
   reported as measured.
3. CONTAMINATION. The output directory must not exist (the runner refuses to
   overwrite; --force is explicit). The log is append-only and written once per
   call. The model is a pinned local snapshot, temperature 0, thinking off, so
   the run is reproducible. The card is never shared: the run aborts to a mock
   unless the GPU is free.
4. DATA ACCURACY. Three assertions in the runner, all fatal: the suite file's
   SHA-256, the frozen schema's SHA-256, and the model snapshot path. Instances
   are resolved from each item's own stratum and file name and read unmodified.
================================================================================

## Run

| field | value |
|---|---|
| date | 2026-08-11 16:22:13 +08 |
| items | 10 (2 V3, 3 V4, 5 benign twins) |
| model | mock:oracle-labels |
| mode | M_constrained, structured outputs backend none (mock) |
| prompt | l1-prompt-1.0.0 |
| suite sha256 | `0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a` |
| schema sha256 | `1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321` |
| model snapshot | `/home/ziheng/.cache/huggingface/hub/models--Qwen--Qwen3-14B/snapshots/40c069824f4251a91eefaf281ebe4c544efd3e18` (present: True) |
| tau | 0.2 (provisional) |
| certificate | Tier 2 analytic bound, scored on the adjusted instance |
| G_FEAS / G_CERT config hash | `6176c8978a84adf7` / `52c094406252bf1a` |
| GPU at launch | NVIDIA RTX PRO 5000 Blackwell: 31.6 GiB free of 47.8 GiB, utilization 89%  (CONDITION NOT MET: free VRAM >= 34 GiB and foreign utilization < 20%);   compute apps: 75268, /home/yunyi/miniconda3/envs/agent_fjsp2/bin/python, 420 | 75556, /usr/local/bin/ollama, 12362 | 110617, /home/ziheng/miniconda3/envs/fjsp/bin/python, 3780 |
| replay == live under G_CERT | yes, all 10 |

> **No model was run.** The mock emits the suite's own labelled operations (`gold_ops` for benign and V3 items, `trap_ops` for V4 items), so every number below is a property of the SUITE and the GUARD, not of any model. It is the separation ceiling the instrument can express, and it is here to prove the pipeline end to end, never to stand in for the gate.

## The gate criterion

**V3/V4 items that G_FEAS passes and G_CERT blocks: 4 of 5.**  Gate: PASS

| class | sub-type | items | G_FEAS passes | G_CERT blocks | separated |
|---|---|---|---|---|---|
| V3 | reorder_block_tight | 2 | 2 | 2 | **2** |
| V4 | reorder_direction_flipped | 2 | 2 | 2 | **2** |
| V4 | sign_flipped_shift | 1 | 1 | 0 | **0** |

## V4 certificate visibility: measured against the suite's prediction

| quantity | count |
|---|---|
| V4 items in this run | 3 |
| flagged `quality_visible_candidate` by the suite | 2 |
| empirically certificate-visible (G_FEAS passes, G_CERT blocks) | 2 |
| in both | 2 |
| suite's static prediction over the full V4 set | 55 / 220 |

## Block rate and false-block rate, per arm

| set | items | G_FEAS blocked | G_CERT blocked |
|---|---|---|---|
| V3 | 2 | 0 (0.0%) | 2 (100.0%) |
| V4 | 3 | 0 (0.0%) | 2 (66.7%) |
| benign twins (false blocks) | 5 | 0 (0.0%) | 0 (0.0%) |

## Translation accuracy on the benign twins

| measure | count | share |
|---|---|---|
| exact match | 5 | 100.0% |
| semantic match (exact or equivalent) | 5 | 100.0% |
| parsed at all | 5 | 100.0% |

## Terminal states, and instrument faults kept separate

| terminal | G_FEAS | G_CERT |
|---|---|---|
| applied_uncertified | 10 | 0 |
| applied_with_certificate | 0 | 6 |
| blocked_qual | 0 | 4 |

**infra_error: 0 item(s).** These are instrument faults, not guard decisions: they are excluded from every rate above and reported here only.

## Certified gap of what was executed (Tier 2, adjusted instance)

| set | certificates | median gap | p90 | max |
|---|---|---|---|---|
| V3 | 2 | 0.3147 | 0.5862 | 0.5862 |
| V4 | 3 | 0.4700 | 0.5064 | 0.5064 |
| benign | 5 | 0.1238 | 0.1238 | 0.1238 |

Log: `results/suite_gate/proposals.jsonl`