# T5. The as-is / to-be ladder

<!-- generated 2026-08-17 17:24:01 +0800 by paper_tables.py (l1-paper-tables-1) -->
<!-- dedup rule applied to the hosted raw logs before evaluation: last row per (mode, thinking, repeat, item_id); hosted logs only -->
<!-- suite suite.jsonl sha256 0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a -->
<!-- adjustment schema sha256 1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321 -->
<!-- ladder anchors: <project>/analysis/ladder (reconciliation 4208/4208 passed) -->
<!-- <project>/results/e1_eval_qwen14b/summary.json sha256 602461e5897a91db20e67a1ce0c9a9b8fa5f64c771a395434c4b9b5a9394d390 -->
<!-- <project>/results/e1_eval_qwen27b/summary.json sha256 8402b5dd527ed055e787c7d53aa4ab752695030909697189622134d1dc8b2a2b -->
<!-- <project>/results/e1_eval_glm9b/summary.json sha256 b655f1e92b0e048e52d6d7d6bcf445558df8b233a1abdf8babd4097edecd4bb8 -->
<!-- <project>/results/e1_eval_gpt54mini/summary.json sha256 dc1e4c9bfdc916c8057411124c8acb3cfeeb452b1e4b0642149c0cf555a560f6 -->
<!-- <project>/results/e1_eval_deepseek/summary.json sha256 5f362141b7f1dd5a32ae64bcbe53cbe30290477c0d294da957125290114a0b71 -->
<!-- <project>/results/e1_eval_sonnet5/summary.json sha256 65aab2232dfac88a58dfdb2f66baef11b63dd700e896b592e35c8bc5f5710d59 -->
<!-- <project>/results/e1_eval_opus5/summary.json sha256 8417125bd4df8b0f3666f30d2b6149411ab2ee3c5ad21a4e29b8a59b4c505309 -->
<!-- <project>/results/e1_eval_sol/summary.json sha256 28475fbf5fcd71348c20ad833353a61e1840912a1ccbcc6cbc8e504893058f4d -->
<!-- <project>/results/e2_tau_sweep/curves.csv sha256 e9ca179c57029c6ae23d0512f12da901884072192c96addff321de94bf04fc76 -->
<!-- rows are the accepted record; every overlapping cell is asserted equal to it -->

One ordered walk from the as-is configurations to the to-be ones on the same 2,000 instructions (guidance Section 5.1). RULE and ORACLE need no model call; the three guard rungs are replays over one logged translation per instruction. The two agent rungs are not yet measured and are printed as `pending E3` rather than left blank.

Read the increments in order: ORACLE over RULE is what instruction handling adds when a person does the translation perfectly; UNGUARDED over ORACLE is what the model loses against that ideal; G-FEAS is what the field's standard guard recovers; G-CERT is what certification adds on top.

The `items` column differs by rung and is not a coverage defect. RULE and ORACLE are deterministic, so one pass over the 2,000 instructions is the whole measurement; the model rungs pool their sampling repeats, so they carry 2,000 x the arm's repeat count. Every rate is a share of its own denominator.

### Ladder on Qwen3-14B (open, local, BF16) (M_constrained / -)

| step | items | applied+cert | applied uncert | blocked | violation pass-through | of which non-empty | warranted | cert gap median | mean WWT vs RULE | median WWT vs RULE |
|---|---|---|---|---|---|---|---|---|---|---|
| 1. RULE/SOLVER | 2000 | - | - | 0.0% | 0.0% | 0.0% | 0.0% | - | +0.00 bh | +0.00 bh |
| 2. ORACLE | 2000 | - | 64.2% | 0.0% | 40.4% | 40.4% | 25.8% | 0.017 | +37.22 bh | +51.30 bh |
| 3. UNGUARDED | 6000 | - | 90.0% | 0.0% | 83.6% | 72.1% | 0.0% | 0.016 | +55.68 bh | +55.38 bh |
| 4. G-FEAS | 6000 | - | 87.4% | 12.6% | 79.1% | 67.7% | 12.5% | 0.016 | +52.39 bh | +51.30 bh |
| 5. G-CERT | 6000 | 74.7% | - | 25.3% | 60.8% | 50.0% | 98.2% | 0.010 | -0.07 bh | +0.00 bh |
| 6. SINGLE+G | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |
| 7. MULTI | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |

### Ladder on Qwen3.6-27B-FP8 (open, local, quantized) (M_constrained / -)

| step | items | applied+cert | applied uncert | blocked | violation pass-through | of which non-empty | warranted | cert gap median | mean WWT vs RULE | median WWT vs RULE |
|---|---|---|---|---|---|---|---|---|---|---|
| 1. RULE/SOLVER | 2000 | - | - | 0.0% | 0.0% | 0.0% | 0.0% | - | +0.00 bh | +0.00 bh |
| 2. ORACLE | 2000 | - | 64.2% | 0.0% | 40.4% | 40.4% | 25.8% | 0.017 | +37.22 bh | +51.30 bh |
| 3. UNGUARDED | 6000 | - | 88.5% | 0.0% | 82.8% | 65.3% | 0.0% | 0.016 | +1042.55 bh | +51.30 bh |
| 4. G-FEAS | 6000 | - | 87.0% | 13.0% | 80.2% | 62.8% | 11.9% | 0.016 | +35.60 bh | +51.30 bh |
| 5. G-CERT | 6000 | 75.2% | - | 24.8% | 62.4% | 45.6% | 97.8% | 0.010 | -0.13 bh | +0.00 bh |
| 6. SINGLE+G | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |
| 7. MULTI | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |

### Ladder on GLM-4-9B (open, local, SPOT-CHECK) (M_constrained / -)

| step | items | applied+cert | applied uncert | blocked | violation pass-through | of which non-empty | warranted | cert gap median | mean WWT vs RULE | median WWT vs RULE |
|---|---|---|---|---|---|---|---|---|---|---|
| 1. RULE/SOLVER | 2000 | - | - | 0.0% | 0.0% | 0.0% | 0.0% | - | +0.00 bh | +0.00 bh |
| 2. ORACLE | 2000 | - | 64.2% | 0.0% | 40.4% | 40.4% | 25.8% | 0.017 | +37.22 bh | +51.30 bh |
| 3. UNGUARDED | 2000 | - | 85.5% | 0.0% | 79.1% | 76.8% | 0.0% | 0.014 | +39.30 bh | +51.30 bh |
| 4. G-FEAS | 2000 | - | 81.8% | 18.2% | 73.2% | 70.8% | 16.1% | 0.014 | +35.72 bh | +51.30 bh |
| 5. G-CERT | 2000 | 71.4% | - | 28.6% | 57.6% | 55.4% | 96.8% | 0.010 | +4.21 bh | +5.54 bh |
| 6. SINGLE+G | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |
| 7. MULTI | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |

### Ladder on GPT-5.4-mini (closed, budget tier) (M_constrained / -)

| step | items | applied+cert | applied uncert | blocked | violation pass-through | of which non-empty | warranted | cert gap median | mean WWT vs RULE | median WWT vs RULE |
|---|---|---|---|---|---|---|---|---|---|---|
| 1. RULE/SOLVER | 2000 | - | - | 0.0% | 0.0% | 0.0% | 0.0% | - | +0.00 bh | +0.00 bh |
| 2. ORACLE | 2000 | - | 64.2% | 0.0% | 40.4% | 40.4% | 25.8% | 0.017 | +37.22 bh | +51.30 bh |
| 3. UNGUARDED | 4000 | - | 87.7% | 0.0% | 80.3% | 74.4% | 0.0% | 0.014 | +536.48 bh | +51.30 bh |
| 4. G-FEAS | 4000 | - | 85.9% | 14.1% | 77.3% | 71.4% | 13.6% | 0.014 | +32.88 bh | +51.30 bh |
| 5. G-CERT | 4000 | 75.0% | - | 25.1% | 60.8% | 55.1% | 98.5% | 0.010 | -0.39 bh | +0.00 bh |
| 6. SINGLE+G | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |
| 7. MULTI | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |

### Ladder on DeepSeek V4-Pro (open weights, hosted) (M_constrained / non_think)

| step | items | applied+cert | applied uncert | blocked | violation pass-through | of which non-empty | warranted | cert gap median | mean WWT vs RULE | median WWT vs RULE |
|---|---|---|---|---|---|---|---|---|---|---|
| 1. RULE/SOLVER | 2000 | - | - | 0.0% | 0.0% | 0.0% | 0.0% | - | +0.00 bh | +0.00 bh |
| 2. ORACLE | 2000 | - | 64.2% | 0.0% | 40.4% | 40.4% | 25.8% | 0.017 | +37.22 bh | +51.30 bh |
| 3. UNGUARDED | 4000 | - | 100.0% | 0.0% | 100.0% | 0.0% | 0.0% | 0.010 | +0.00 bh | +0.00 bh |
| 4. G-FEAS | 4000 | - | 19.2% | 80.8% | 30.1% | 0.0% | 41.9% | 0.011 | +0.00 bh | +0.00 bh |
| 5. G-CERT | 4000 | 18.6% | - | 81.3% | 29.2% | 0.0% | 61.1% | 0.010 | +0.00 bh | +0.00 bh |
| 6. SINGLE+G | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |
| 7. MULTI | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |

### Ladder on Claude Sonnet 5 (closed) (M_constrained / disabled)

| step | items | applied+cert | applied uncert | blocked | violation pass-through | of which non-empty | warranted | cert gap median | mean WWT vs RULE | median WWT vs RULE |
|---|---|---|---|---|---|---|---|---|---|---|
| 1. RULE/SOLVER | 2000 | - | - | 0.0% | 0.0% | 0.0% | 0.0% | - | +0.00 bh | +0.00 bh |
| 2. ORACLE | 2000 | - | 64.2% | 0.0% | 40.4% | 40.4% | 25.8% | 0.017 | +37.22 bh | +51.30 bh |
| 3. UNGUARDED | 4000 | - | 92.5% | 0.0% | 88.4% | 62.2% | 0.0% | 0.016 | +43.28 bh | +51.30 bh |
| 4. G-FEAS | 4000 | - | 91.0% | 9.0% | 85.9% | 59.7% | 8.5% | 0.016 | +34.46 bh | +51.30 bh |
| 5. G-CERT | 4000 | 79.4% | - | 20.6% | 68.2% | 42.8% | 98.5% | 0.010 | -0.52 bh | +0.00 bh |
| 6. SINGLE+G | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |
| 7. MULTI | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |

### Ladder on Claude Opus 5 (closed, flagship) (M_constrained / default)

| step | items | applied+cert | applied uncert | blocked | violation pass-through | of which non-empty | warranted | cert gap median | mean WWT vs RULE | median WWT vs RULE |
|---|---|---|---|---|---|---|---|---|---|---|
| 1. RULE/SOLVER | 2000 | - | - | 0.0% | 0.0% | 0.0% | 0.0% | - | +0.00 bh | +0.00 bh |
| 2. ORACLE | 2000 | - | 64.2% | 0.0% | 40.4% | 40.4% | 25.8% | 0.017 | +37.22 bh | +51.30 bh |
| 3. UNGUARDED | 4000 | - | 98.5% | 0.0% | 98.4% | 59.0% | 0.0% | 0.016 | +42.60 bh | +51.30 bh |
| 4. G-FEAS | 4000 | - | 97.1% | 2.9% | 96.0% | 56.7% | 2.3% | 0.016 | +36.96 bh | +51.30 bh |
| 5. G-CERT | 4000 | 84.8% | - | 15.2% | 77.2% | 39.0% | 98.4% | 0.010 | -0.55 bh | +0.00 bh |
| 6. SINGLE+G | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |
| 7. MULTI | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |

### Ladder on GPT-5.6 Sol (closed, flagship spot-check) (M_constrained / none)

| step | items | applied+cert | applied uncert | blocked | violation pass-through | of which non-empty | warranted | cert gap median | mean WWT vs RULE | median WWT vs RULE |
|---|---|---|---|---|---|---|---|---|---|---|
| 1. RULE/SOLVER | 2000 | - | - | 0.0% | 0.0% | 0.0% | 0.0% | - | +0.00 bh | +0.00 bh |
| 2. ORACLE | 2000 | - | 64.2% | 0.0% | 40.4% | 40.4% | 25.8% | 0.017 | +37.22 bh | +51.30 bh |
| 3. UNGUARDED | 2000 | - | 93.5% | 0.0% | 93.0% | 59.2% | 0.0% | 0.016 | +41.90 bh | +51.30 bh |
| 4. G-FEAS | 2000 | - | 91.8% | 8.2% | 90.2% | 56.4% | 5.9% | 0.016 | +35.93 bh | +51.30 bh |
| 5. G-CERT | 2000 | 80.2% | - | 19.8% | 72.8% | 39.9% | 96.5% | 0.011 | -0.64 bh | +0.00 bh |
| 6. SINGLE+G | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |
| 7. MULTI | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 | pending E3 |

