# T4. System-level trustworthiness profiles

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

Every instruction ends in exactly one terminal state (guidance Section 5.4). A block is *correct* when the item carries a violation label and *false* when it is a benign twin. `execution_failed` is the UNGUARDED arm's crash, which is not a refusal and is never counted as one; `unhandled` is the RULE row, where no instruction channel exists at all, so the instruction reaches a person with no record and the disposition carries no justification. Violation pass-through is the share of labelled violations that reach the executed schedule. The certified gap is conditional on the proposal having been applied. End-task quality is weighted tardiness scored against the *original* fields, the one yardstick no proposal can move.

This is a reporting convention over quantities already measured, not a new metric, and it carries no tunable weights.

| system | mode | think | applied+cert | applied uncert | referred | blocked ok | blocked false | exec failed | unhandled | violation pass-through | of which non-empty | cert gap median | warranted | mean WWT vs RULE | median WWT vs RULE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RULE | - | - | - | - | - | - | - | - | 100.0% | 0.0% | 0.0% | - | 0.0% | +0.00 bh | +0.00 bh |
| ORACLE | - | - | - | 64.2% | 25.8% | - | - | 10.0% | - | 40.4% | 40.4% | 0.017 | 25.8% | +37.22 bh | +51.30 bh |
| ORACLE+G_CERT | - | - | 52.8% | - | 25.8% | 20.4% | 1.1% | - | - | 23.0% | 23.0% | 0.010 | 99.0% | -0.65 bh | +0.00 bh |
| qwen3-14b / UNGUARDED | M_constrained | - | - | 90.0% | - | - | - | 10.0% | - | 83.6% | 72.1% | 0.016 | 0.0% | +55.68 bh | +55.38 bh |
| qwen3-14b / G_FEAS | M_constrained | - | - | 87.4% | - | 12.5% | 0.1% | - | - | 79.1% | 67.7% | 0.016 | 12.5% | +52.39 bh | +51.30 bh |
| qwen3-14b / G_CERT | M_constrained | - | 74.7% | - | - | 23.5% | 1.8% | - | - | 60.8% | 50.0% | 0.010 | 98.2% | -0.07 bh | +0.00 bh |
| qwen3.6-27b-fp8 / UNGUARDED | M_constrained | - | - | 88.5% | - | - | - | 11.5% | - | 82.8% | 65.3% | 0.016 | 0.0% | +1042.55 bh | +51.30 bh |
| qwen3.6-27b-fp8 / G_FEAS | M_constrained | - | - | 87.0% | - | 11.9% | 1.1% | - | - | 80.2% | 62.8% | 0.016 | 11.9% | +35.60 bh | +51.30 bh |
| qwen3.6-27b-fp8 / G_CERT | M_constrained | - | 75.2% | - | - | 22.6% | 2.2% | - | - | 62.4% | 45.6% | 0.010 | 97.8% | -0.13 bh | +0.00 bh |
| glm-4-9b / UNGUARDED | M_constrained | - | - | 85.5% | - | - | - | 14.4% | - | 79.1% | 76.8% | 0.014 | 0.0% | +39.30 bh | +51.30 bh |
| glm-4-9b / G_FEAS | M_constrained | - | - | 81.8% | - | 16.1% | 2.1% | - | - | 73.2% | 70.8% | 0.014 | 16.1% | +35.72 bh | +51.30 bh |
| glm-4-9b / G_CERT | M_constrained | - | 71.4% | - | - | 25.4% | 3.2% | - | - | 57.6% | 55.4% | 0.010 | 96.8% | +4.21 bh | +5.54 bh |
| openai / UNGUARDED | M_constrained | - | - | 87.7% | - | - | - | 12.3% | - | 80.3% | 74.4% | 0.014 | 0.0% | +536.48 bh | +51.30 bh |
| openai / G_FEAS | M_constrained | - | - | 85.9% | - | 13.6% | 0.5% | - | - | 77.3% | 71.4% | 0.014 | 13.6% | +32.88 bh | +51.30 bh |
| openai / G_CERT | M_constrained | - | 75.0% | - | - | 23.5% | 1.6% | - | - | 60.8% | 55.1% | 0.010 | 98.5% | -0.39 bh | +0.00 bh |
| deepseek / UNGUARDED | M_constrained | non_think | - | 100.0% | - | - | - | - | - | 100.0% | 0.0% | 0.010 | 0.0% | +0.00 bh | +0.00 bh |
| deepseek / UNGUARDED | M_constrained | think_high | - | 98.1% | - | - | - | 1.9% | - | 97.3% | 0.5% | 0.010 | 0.0% | +0.00 bh | +0.00 bh |
| deepseek / G_FEAS | M_constrained | non_think | - | 19.2% | - | 41.9% | 38.8% | - | - | 30.1% | 0.0% | 0.011 | 41.9% | +0.00 bh | +0.00 bh |
| deepseek / G_FEAS | M_constrained | think_high | - | 14.5% | - | 45.7% | 39.8% | - | - | 23.8% | 0.5% | 0.012 | 45.7% | +0.00 bh | +0.00 bh |
| deepseek / G_CERT | M_constrained | non_think | 18.6% | - | - | 42.5% | 38.9% | - | - | 29.2% | 0.0% | 0.010 | 61.1% | +0.00 bh | +0.00 bh |
| deepseek / G_CERT | M_constrained | think_high | 14.1% | - | - | 46.2% | 39.8% | - | - | 23.1% | 0.5% | 0.011 | 60.2% | +0.00 bh | +0.00 bh |
| sonnet / UNGUARDED | M_constrained | disabled | - | 92.5% | - | - | - | 7.4% | - | 88.4% | 62.2% | 0.016 | 0.0% | +43.28 bh | +51.30 bh |
| sonnet / G_FEAS | M_constrained | disabled | - | 91.0% | - | 8.5% | 0.5% | - | - | 85.9% | 59.7% | 0.016 | 8.5% | +34.46 bh | +51.30 bh |
| sonnet / G_CERT | M_constrained | disabled | 79.4% | - | - | 19.1% | 1.5% | - | - | 68.2% | 42.8% | 0.010 | 98.5% | -0.52 bh | +0.00 bh |
| opus / UNGUARDED | M_constrained | default | - | 98.5% | - | - | - | 1.4% | - | 98.4% | 59.0% | 0.016 | 0.0% | +42.60 bh | +51.30 bh |
| opus / UNGUARDED | M_constrained | disabled | - | 94.6% | - | - | - | 5.4% | - | 92.5% | 58.2% | 0.016 | 0.0% | +41.24 bh | +51.30 bh |
| opus / G_FEAS | M_constrained | default | - | 97.1% | - | 2.3% | 0.5% | - | - | 96.0% | 56.7% | 0.016 | 2.3% | +36.96 bh | +51.30 bh |
| opus / G_FEAS | M_constrained | disabled | - | 93.5% | - | 5.5% | 0.9% | - | - | 90.7% | 56.3% | 0.016 | 5.5% | +36.80 bh | +51.30 bh |
| opus / G_CERT | M_constrained | default | 84.8% | - | - | 13.6% | 1.6% | - | - | 77.2% | 39.0% | 0.010 | 98.4% | -0.55 bh | +0.00 bh |
| opus / G_CERT | M_constrained | disabled | 81.2% | - | - | 16.8% | 2.0% | - | - | 72.0% | 38.5% | 0.010 | 98.0% | -0.45 bh | +0.00 bh |
| sol / UNGUARDED | M_constrained | none | - | 93.5% | - | - | - | 6.5% | - | 93.0% | 59.2% | 0.016 | 0.0% | +41.90 bh | +51.30 bh |
| sol / G_FEAS | M_constrained | none | - | 91.8% | - | 5.9% | 2.4% | - | - | 90.2% | 56.4% | 0.016 | 5.9% | +35.93 bh | +51.30 bh |
| sol / G_CERT | M_constrained | none | 80.2% | - | - | 16.3% | 3.5% | - | - | 72.8% | 39.9% | 0.011 | 96.5% | -0.64 bh | +0.00 bh |

Two pass-through columns, because they answer different questions. The first counts every labelled violation the system applied; the second counts only those that executed at least one operation, and the gap between them is the silent no-op, where the instruction was accepted and then not carried out. The mean and the median executed tardiness are reported together because a handful of catastrophic schedules move the mean by hundreds of business hours while the median barely moves.

