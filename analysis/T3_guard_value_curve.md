# T3. Guard value against proposer capability

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

