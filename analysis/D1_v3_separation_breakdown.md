# D1. V3 separation by arm, register and template family (diagnostic)

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

Diagnostic input for the pending translation-difference audit of the mini arm's V3 separation, which sits below both smaller open arms (decision record, 2026-08-12). Nothing here is a conclusion.

V3 separation requires two things at once: the proposal must pass the feasibility guard, and the certificate must then refuse it. A proposal that never reproduces the damaging instruction is not separated either, so the gold-match column is reported beside the separation column: it says whether the arm translated the V3 instruction as the ground truth does, which is the quantity the audit needs.

| arm | cut | value | think | V3 items | separation | gold match exact | unseparated: accepted | unseparated: feas-blocked |
|---|---|---|---|---|---|---|---|---|
| qwen3-14b | all | all | - | 660 | 82.3% | 37.7% | 114 | 0 |
| qwen3-14b | register | conversational | - | 192 | 73.4% | 37.5% | 51 | 0 |
| qwen3-14b | register | formal | - | 276 | 81.5% | 35.9% | 48 | 0 |
| qwen3-14b | register | terse | - | 192 | 92.2% | 40.6% | 15 | 0 |
| qwen3.6-27b-fp8 | all | all | - | 660 | 87.0% | 38.0% | 83 | 3 |
| qwen3.6-27b-fp8 | register | conversational | - | 192 | 76.6% | 39.1% | 45 | 0 |
| qwen3.6-27b-fp8 | register | formal | - | 276 | 89.1% | 34.8% | 27 | 3 |
| qwen3.6-27b-fp8 | register | terse | - | 192 | 94.3% | 41.7% | 11 | 0 |
| glm-4-9b | all | all | - | 220 | 72.7% | 38.2% | 54 | 4 |
| glm-4-9b | register | conversational | - | 64 | 64.1% | 40.6% | 23 | 0 |
| glm-4-9b | register | formal | - | 92 | 78.3% | 41.3% | 17 | 2 |
| glm-4-9b | register | terse | - | 64 | 73.4% | 31.2% | 14 | 2 |
| openai | all | all | - | 440 | 78.9% | 36.8% | 91 | 2 |
| openai | register | conversational | - | 128 | 75.0% | 41.4% | 32 | 0 |
| openai | register | formal | - | 184 | 80.4% | 33.2% | 34 | 2 |
| openai | register | terse | - | 128 | 80.5% | 37.5% | 25 | 0 |
| deepseek | all | all | non_think | 440 | 0.2% | 0.0% | 2 | 0 |
| deepseek | all | all | think_high | 440 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | conversational | non_think | 128 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | conversational | think_high | 128 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | formal | non_think | 184 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | formal | think_high | 184 | 0.0% | 0.0% | 0 | 0 |
| deepseek | register | terse | non_think | 128 | 0.8% | 0.0% | 2 | 0 |
| deepseek | register | terse | think_high | 128 | 0.0% | 0.0% | 0 | 0 |
| sonnet | all | all | disabled | 440 | 85.9% | 35.2% | 60 | 2 |
| sonnet | register | conversational | disabled | 128 | 77.3% | 42.2% | 29 | 0 |
| sonnet | register | formal | disabled | 184 | 89.1% | 36.4% | 18 | 2 |
| sonnet | register | terse | disabled | 128 | 89.8% | 26.6% | 13 | 0 |
| opus | all | all | default | 440 | 90.5% | 38.4% | 42 | 0 |
| opus | all | all | disabled | 440 | 90.0% | 38.0% | 44 | 0 |
| opus | register | conversational | default | 128 | 85.9% | 40.6% | 18 | 0 |
| opus | register | conversational | disabled | 128 | 85.9% | 40.6% | 18 | 0 |
| opus | register | formal | default | 184 | 89.1% | 40.8% | 20 | 0 |
| opus | register | formal | disabled | 184 | 88.0% | 39.7% | 22 | 0 |
| opus | register | terse | default | 128 | 96.9% | 32.8% | 4 | 0 |
| opus | register | terse | disabled | 128 | 96.9% | 32.8% | 4 | 0 |
| sol | all | all | none | 220 | 82.3% | 38.2% | 26 | 3 |
| sol | register | conversational | none | 64 | 71.9% | 40.6% | 14 | 0 |
| sol | register | formal | none | 92 | 82.6% | 34.8% | 10 | 3 |
| sol | register | terse | none | 64 | 92.2% | 40.6% | 2 | 0 |

