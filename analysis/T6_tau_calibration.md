# T6. Certificate tolerance calibration

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

The certificate's tolerance tau enters the guard only as the final gap-vs-tau comparison, so the sweep is post-processing over the certificates already recorded: no replay and no model call. Every arm's curve is re-derived here with the accepted sweep's own functions, and every cell the accepted sweep already published is asserted equal to it.

The reported operating point is `tau_smallest`, the tightest gate meeting the benign false-block budget (the frozen 'largest tau' rule degenerates because the false-block rate is non-increasing in tau; decisions.md, 2026-08-12). The floor column is the share of benign twins blocked at the schema or feasibility stage, which no value of tau can move.

| arm | mode | think | V3 sep @0.05 | V3 sep @0.20 | V3 sep @0.50 | false blocks @0.20 | false-block floor | tau at fb<=5% | fb<=1% reachable | in accepted E2 sweep |
|---|---|---|---|---|---|---|---|---|---|---|
| deepseek | M_constrained | non_think | 0.2% | 0.2% | 0.0% | 97.2% | 97.1% |  | no | yes |
| deepseek | M_constrained | think_high | 0.0% | 0.0% | 0.0% | 99.4% | 99.4% |  | no | yes |
| deepseek | M_free | non_think | 0.0% | 0.0% | 0.0% | 97.9% | 97.8% |  | no | yes |
| deepseek | M_free | think_high | 0.0% | 0.0% | 0.0% | 99.5% | 99.5% |  | no | yes |
| glm-4-9b | M_constrained | - | 83.6% | 72.7% | 45.0% | 8.0% | 5.4% |  | no | yes |
| glm-4-9b | M_free | - | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | yes |
| openai | M_constrained | - | 89.1% | 78.9% | 50.0% | 3.9% | 1.2% | 0.15 | no | yes |
| openai | M_free | - | 0.0% | 0.0% | 0.0% | 99.5% | 99.5% |  | no | yes |
| opus | M_constrained | default | 98.6% | 90.5% | 58.6% | 3.9% | 1.3% | 0.15 | no | yes |
| opus | M_constrained | disabled | 98.4% | 90.0% | 58.4% | 5.0% | 2.4% | 0.2 | no | yes |
| opus | M_free | default | 0.2% | 0.2% | 0.2% | 28.1% | 28.1% |  | no | yes |
| opus | M_free | disabled | 1.6% | 1.6% | 1.4% | 23.1% | 22.9% |  | no | yes |
| qwen3-14b | M_constrained | - | 91.8% | 82.3% | 51.8% | 4.4% | 0.2% | 0.15 | 1.0 | yes |
| qwen3-14b | M_free | - | 0.0% | 0.0% | 0.0% | 99.3% | 99.3% |  | no | yes |
| qwen3.6-27b-fp8 | M_constrained | - | 95.6% | 87.0% | 57.3% | 5.5% | 2.9% | 0.3 | no | yes |
| qwen3.6-27b-fp8 | M_free | - | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | yes |
| sol | M_constrained | none | 90.9% | 82.3% | 52.7% | 8.6% | 6.0% |  | no | yes |
| sonnet | M_constrained | disabled | 95.2% | 85.9% | 55.9% | 3.8% | 1.2% | 0.15 | no | yes |
| sonnet | M_free | disabled | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% |  | no | yes |

