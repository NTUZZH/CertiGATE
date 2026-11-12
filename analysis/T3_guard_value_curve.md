# T3. Guard value against proposer capability

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

Constrained mode only, pooled over repeats, ordered along the capability gradient. V3 separation is the share of quality violations the feasibility guard passed and the certificate refused, so it measures what certification adds over the guard the field already builds. The V4-V6 columns are the proposer's own errors that the guard has to catch: a mistranslation, an action on an ambiguous instruction, and a successful injection.

| tier | arm | think | V3 separation | V3 gap median | V3 gap max | V4 blocks | V5 blocks | V6 blocks | benign false blocks (G-CERT) | translation exact |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | qwen3-14b | - | 82.3% (543/660) | 0.524 | 52.0 | 6.1% | 7.0% | 12.0% | 4.4% | 59.3% |
| 2 | qwen3.6-27b-fp8 | - | 87.0% (574/660) | 0.603 | 172.2 | 2.7% | 4.0% | 5.0% | 5.5% | 73.3% |
| 3 | glm-4-9b | - | 72.7% (160/220) | 0.456 | 52.0 | 4.1% | 19.5% | 14.0% | 8.0% | 60.8% |
| 4 | openai | - | 78.9% (347/440) | 0.502 | 78.3 | 3.0% | 17.8% | 4.8% | 3.9% | 65.4% |
| 5 | deepseek | non_think | 0.2% (1/440) | 0.048 | 0.3 | 93.4% | 6.5% | 84.5% | 97.2% | 0.0% |
| 5 | deepseek | think_high | 0.0% (0/440) | - | - | 99.1% | 22.8% | 91.2% | 99.4% | 0.0% |
| 6 | sonnet | disabled | 85.9% (378/440) | 0.586 | 172.2 | 2.7% | 3.5% | 3.2% | 3.8% | 70.4% |
| 7 | opus | default | 90.5% (398/440) | 0.619 | 172.2 | 2.7% | 3.5% | 3.0% | 3.9% | 72.4% |
| 7 | opus | disabled | 90.0% (396/440) | 0.619 | 172.2 | 2.7% | 3.5% | 3.0% | 5.0% | 72.6% |
| 8 | sol | none | 82.3% (181/220) | 0.585 | 172.2 | 7.7% | 3.5% | 3.0% | 8.6% | 69.1% |

Coverage boundaries carried, not averaged away: glm-4-9b = SPOT-CHECK: open-side second family; both modes x 1 repeat; sol = SPOT-CHECK: M_constrained x effort-none x 1 repeat

