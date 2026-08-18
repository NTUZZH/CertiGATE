# T2. The enforcement ladder

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

The enforcement axis, ordered by what the wire actually enforces: `none` (M_free, no enforcement field), `json_object` (reply with a JSON object, no schema; DeepSeek's only constrained mode), and the two real schema enforcements, `json_schema` (provider-side strict outputs) and `xgrammar` (local grammar-guided decoding). Shape drift is the share of completions that do not parse as a proposal about this instance; the silent no-op column is what that drift costs when nothing gates, because the lenient repair drops the operations it cannot read and executes what remains, which is often nothing.

| enforcement | arm | mode | think | items | JSON invalid | wrong shape | schema valid | G-CERT blocked at schema | UNGUARDED silent no-op | benign translation exact |
|---|---|---|---|---|---|---|---|---|---|---|
| none | qwen3-14b | M_free | - | 6000 | 6.58% | 85.72% | 7.70% | 92.3% | 92.8% | 0.0% |
| none | qwen3.6-27b-fp8 | M_free | - | 6000 | 0.00% | 89.30% | 10.70% | 89.3% | 99.5% | 0.0% |
| none | glm-4-9b | M_free | - | 2000 | 98.60% | 1.40% | 0.00% | 100.0% | 99.5% | 0.0% |
| none | openai | M_free | - | 4000 | 0.00% | 95.08% | 4.92% | 95.1% | 99.6% | 0.2% |
| none | deepseek | M_free | non_think | 4000 | 0.00% | 82.75% | 17.25% | 82.8% | 99.8% | 0.0% |
| none | deepseek | M_free | think_high | 4000 | 1.12% | 84.50% | 14.37% | 85.6% | 98.9% | 0.0% |
| none | sonnet | M_free | disabled | 4000 | 9.18% | 78.35% | 12.47% | 87.5% | 99.5% | 0.0% |
| none | opus | M_free | default | 4000 | 0.10% | 18.20% | 6.48% | 18.3% | 23.6% | 1.0% |
| none | opus | M_free | disabled | 4000 | 0.25% | 14.80% | 6.95% | 15.2% | 17.7% | 4.1% |
| json_object | deepseek | M_constrained | non_think | 4000 | 0.00% | 80.77% | 19.23% | 80.8% | 100.0% | 0.0% |
| json_object | deepseek | M_constrained | think_high | 4000 | 1.90% | 83.60% | 14.50% | 85.5% | 97.8% | 0.0% |
| xgrammar | qwen3-14b | M_constrained | - | 6000 | 0.37% | 0.00% | 99.63% | 6.7% | 7.1% | 59.3% |
| xgrammar | qwen3.6-27b-fp8 | M_constrained | - | 6000 | 0.00% | 0.00% | 100.00% | 5.5% | 10.5% | 73.3% |
| xgrammar | glm-4-9b | M_constrained | - | 2000 | 0.00% | 0.00% | 100.00% | 9.2% | 1.4% | 60.8% |
| json_schema | openai | M_constrained | - | 4000 | 0.00% | 0.00% | 100.00% | 7.2% | 3.8% | 65.4% |
| json_schema | sonnet | M_constrained | disabled | 4000 | 0.00% | 0.00% | 100.00% | 4.5% | 15.8% | 70.4% |
| json_schema | opus | M_constrained | default | 4000 | 0.00% | 0.00% | 99.95% | 1.8% | 23.9% | 72.4% |
| json_schema | opus | M_constrained | disabled | 4000 | 0.00% | 0.00% | 99.95% | 3.5% | 20.9% | 72.6% |
| json_schema | sol | M_constrained | none | 2000 | 1.55% | 0.00% | 98.45% | 4.2% | 20.4% | 69.1% |

