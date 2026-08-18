# D1. V3 separation by arm, register and template family (diagnostic)

<!-- generated 2026-08-17 17:24:01 +0800 by paper_tables.py (l1-paper-tables-1) -->
<!-- dedup rule applied to the hosted raw logs before evaluation: last row per (mode, thinking, repeat, item_id); hosted logs only -->
<!-- suite suite.jsonl sha256 0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a -->
<!-- adjustment schema sha256 1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321 -->
<!-- ladder anchors: /home/ziheng/PaperL1/analysis/ladder (reconciliation 4208/4208 passed) -->
<!-- /home/ziheng/PaperL1/results/e1_eval_qwen14b/summary.json sha256 793c76b07b492ef0fd70878913b6c90449fa7d884edd530817eaf98c1c51c1c8 -->
<!-- /home/ziheng/PaperL1/results/e1_eval_qwen27b/summary.json sha256 78745e80ca0550e27d754b70e2e8f8bd7d33a6ba11b419852ec4c05a9c5a57d5 -->
<!-- /home/ziheng/PaperL1/results/e1_eval_glm9b/summary.json sha256 bb806173f35bcd5013b1a9b77223f0d2e16346375670a6dca65dbb8859099724 -->
<!-- /home/ziheng/PaperL1/results/e1_eval_gpt54mini/summary.json sha256 5da1e6beba8ac75283ee1e5f9352c2fff80eb08fe74f590e551b35b5364fa028 -->
<!-- /home/ziheng/PaperL1/results/e1_eval_deepseek/summary.json sha256 574ebad8772fe47ec758487469231be95f2e457399fa619ad553b571dc8ee8f9 -->
<!-- /home/ziheng/PaperL1/results/e1_eval_sonnet5/summary.json sha256 e50203a3a4474af675a4ed1e397c52ecd1f1b057502f21987d01ec6e8878e4f6 -->
<!-- /home/ziheng/PaperL1/results/e1_eval_opus5/summary.json sha256 d1ab21e2a71280e44d8eed9feda0f8031e4c3160d17fd995414d6a1398ae4f15 -->
<!-- /home/ziheng/PaperL1/results/e1_eval_sol/summary.json sha256 fa3ae6264fcdfbd3b311ad59a8ed88bc8540176adea8b4b043b2fecf5086379d -->
<!-- /home/ziheng/PaperL1/results/e2_tau_sweep/curves.csv sha256 e9ca179c57029c6ae23d0512f12da901884072192c96addff321de94bf04fc76 -->
<!-- rows are the accepted record; every overlapping cell is asserted equal to it -->

Diagnostic input for the pending translation-difference audit of the mini arm's V3 separation, which sits below both smaller open arms (decisions.md, 2026-08-12). Nothing here is a conclusion.

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

