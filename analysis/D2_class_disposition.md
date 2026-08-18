# D2. Blocked, declined or applied, per class (diagnostic)

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

A block rate is a joint measurement: the proposer has to produce the illegal operation before the guard can refuse it. On the schema and feasibility classes the stronger arms decline to act instead, returning an empty operation list, which is correct handling and leaves the guard nothing to block. Reading a falling V1 or V2 block rate as falling guard recall would be wrong, and this table is what prevents that reading: the last column, block plus decline, is what the pair actually achieves.

| arm | class | think | items | blocked by the guard | declined (empty proposal) | refused by the model | applied with operations | blocked, declined or refused |
|---|---|---|---|---|---|---|---|---|
| qwen3-14b | V1 | - | 480 | 66.7% | 8.5% | 0.0% | 24.8% | 75.2% |
| qwen3-14b | V2 | - | 600 | 65.3% | 4.7% | 0.0% | 30.0% | 70.0% |
| qwen3.6-27b-fp8 | V1 | - | 480 | 69.4% | 18.5% | 0.0% | 12.1% | 87.9% |
| qwen3.6-27b-fp8 | V2 | - | 600 | 62.2% | 17.2% | 0.0% | 20.7% | 79.3% |
| glm-4-9b | V1 | - | 160 | 71.2% | 1.9% | 0.0% | 26.9% | 73.1% |
| glm-4-9b | V2 | - | 200 | 76.5% | 0.5% | 0.0% | 23.0% | 77.0% |
| openai | V1 | - | 320 | 71.9% | 1.6% | 0.0% | 26.6% | 73.4% |
| openai | V2 | - | 400 | 64.5% | 7.5% | 0.0% | 28.0% | 72.0% |
| deepseek | V1 | non_think | 320 | 74.4% | 25.6% | 0.0% | 0.0% | 100.0% |
| deepseek | V1 | think_high | 320 | 77.8% | 22.2% | 0.0% | 0.0% | 100.0% |
| deepseek | V2 | non_think | 400 | 62.0% | 38.0% | 0.0% | 0.0% | 100.0% |
| deepseek | V2 | think_high | 400 | 66.2% | 33.8% | 0.0% | 0.0% | 100.0% |
| sonnet | V1 | disabled | 320 | 56.2% | 29.7% | 0.0% | 14.1% | 85.9% |
| sonnet | V2 | disabled | 400 | 41.2% | 30.2% | 0.0% | 28.5% | 71.5% |
| opus | V1 | default | 320 | 23.4% | 70.9% | 0.0% | 5.6% | 94.4% |
| opus | V1 | disabled | 320 | 45.0% | 44.7% | 0.0% | 10.3% | 89.7% |
| opus | V2 | default | 400 | 8.2% | 49.2% | 0.0% | 42.5% | 57.5% |
| opus | V2 | disabled | 400 | 23.0% | 39.0% | 0.0% | 38.0% | 62.0% |
| sol | V1 | none | 160 | 31.2% | 53.1% | 0.0% | 15.6% | 84.4% |
| sol | V2 | none | 200 | 26.0% | 39.5% | 0.0% | 34.5% | 65.5% |

