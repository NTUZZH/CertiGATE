# E3 analysis: the agent-layer tables

<!-- generated 2026-08-17 17:51:50 +0800 by e3_analyze.py (l1-e3-analysis-1) -->
<!-- E3 dedup rule: last row per (arm, budget_level, pipeline, repeat, item_id); earlier rows are superseded attempts -->
<!-- suite suite.jsonl sha256 0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a -->
<!-- adjustment schema sha256 1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321 -->
<!-- E3 slice E3-240 sha256 84b24f0232754344a4c16bcbe9e697b12aef9c707661a365c111424ee861e3e5 (240 items) -->
<!-- guard configurations: UNGUARDED b932b4a480c187968da8445242479be77d62341b7f35753f9cba7fdc3500dc89, G_FEAS 6176c8978a84adf727594d2a7a574dad6e03628e1d3cdddefbf76cfa79122390, G_CERT 52c094406252bf1ab57350d1ec4f9165f8bc4f7d83df2b99e1fb52356e829a42 -->
<!-- ladder anchors: /home/ziheng/PaperL1/analysis/ladder (reconciliation 4208/4208 passed) -->
<!-- /home/ziheng/PaperL1/results/e3_qwen14b/trajectories.jsonl sha256 604f356e6dc1625f83c816221fe87a61676a25cfcb1d7942fb70461f699c1204 -->
<!-- /home/ziheng/PaperL1/results/e3_qwen14b/calls.jsonl sha256 02b7d7d6018f16185c58c0c6db68aa04ece5e0071711ed35f388bd0eb90ff571 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_qwen14b/verdicts.jsonl sha256 02000960325ccbef18394354273795ab22638e252eb7a1f4478a8ad26ad99606 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_qwen14b/summary.json sha256 5db2ae0bb56ffb3cd22822db4e1535aec85967dda806639384344e9898153d5f -->
<!-- /home/ziheng/PaperL1/results/e3_qwen27b/trajectories.jsonl sha256 027f860346b1a8699699f98b05021a57f3087053d87d740770024d012bd1f278 -->
<!-- /home/ziheng/PaperL1/results/e3_qwen27b/calls.jsonl sha256 465f593d8d41de1e32fe3bf0d1e53d39936a238d38580272b2b1bf89daebe699 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_qwen27b/verdicts.jsonl sha256 a21c32d9ff46d67068822a7b95db6bb4041d268e6816bf7351af8899ef3462de -->
<!-- /home/ziheng/PaperL1/results/e3_replay_qwen27b/summary.json sha256 857e61c9e8cb14d8b1bd2b391da3a187e9917d2b47c10839898994a8779622ee -->
<!-- /home/ziheng/PaperL1/results/e3_openai/trajectories.jsonl sha256 a43366e597f6d8b2d4daffc7aebc3c05aa81bbb589a47b61e51a28054483b788 -->
<!-- /home/ziheng/PaperL1/results/e3_openai/calls.jsonl sha256 d77aca570ce5a50376931a1ae0d35fff1ed3fea87895e83b6c3a7ef8604f1136 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_openai/verdicts.jsonl sha256 168a8b20626a3b70ea16308f7a56af95abe146da4e5607fdb3d3b6f36692dfee -->
<!-- /home/ziheng/PaperL1/results/e3_replay_openai/summary.json sha256 ce1e2d5d91be629bf059f7d3c8e0efb53b698f89a07ace4fd5eb397b459fe62f -->
<!-- /home/ziheng/PaperL1/results/e3_deepseek/trajectories.jsonl sha256 4d34fcdb78f405748b1cd8b7784f4b37f059c12a59232629b059f4593d04197f -->
<!-- /home/ziheng/PaperL1/results/e3_deepseek/calls.jsonl sha256 e27dd7d19e9b1613dab14d2b85bc49c97b3471e52d4880f3e6ab8367e230b7c5 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_deepseek/verdicts.jsonl sha256 8e42a2c7a2730cee28e6de7aba54b4f96f88c87a712eb5a95c83fb8549106d4b -->
<!-- /home/ziheng/PaperL1/results/e3_replay_deepseek/summary.json sha256 71a18e38480b7f4c69cf1a64175231c5224f8361300d2f0f77b35a9f3c5b13a9 -->
<!-- /home/ziheng/PaperL1/results/e3_sonnet/trajectories.jsonl sha256 36fb12389daceec2a8b4a11779c4593c3af3bc25887c8888fb94d3aba49a129e -->
<!-- /home/ziheng/PaperL1/results/e3_sonnet/calls.jsonl sha256 951b14ebefb47a1fe40b4caffab1c97f397551ff4d921e9e4e00f47678c87753 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_sonnet/verdicts.jsonl sha256 8784318b09fb75599bb1d562cf156c3838b407833647fe82712e333b3d46ca36 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_sonnet/summary.json sha256 220adec6a82e3698c5d713681dd05f902ad4f943fd1fc8147ce427e8b319e7ed -->
<!-- /home/ziheng/PaperL1/results/e3_opus/trajectories.jsonl sha256 e8e32230b294a996e3e6cca11deae0fabf5f3d9d157707d540d628e189c27772 -->
<!-- /home/ziheng/PaperL1/results/e3_opus/calls.jsonl sha256 9e0d0e5ec13594ddb69278766aaadcff2d0e89dfb1c7bc78e422bac1a019ade6 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_opus/verdicts.jsonl sha256 9af87fa798a1aede09a82db34cadee9455d6d20b65302c16f0a4ac89b2453a17 -->
<!-- /home/ziheng/PaperL1/results/e3_replay_opus/summary.json sha256 c4ee48fb4393dcaff42794cf3b16690777bf827faed96f0df60a48b823ccc2f1 -->
<!-- every verdict is recomputed from the trajectory log with e3_replay's own evaluation path and asserted equal to results/e3_replay_*; no number is adjusted to make an assertion pass -->

Statistics and tables only. This report states what was measured and what was checked; it recommends nothing and derives no decision rule.

## Reconciliation

| quantity | value |
|---|---|
| assertions run | 7580 |
| assertions passed | 7580 |
| assertions failed | 0 |
| verdict-field comparisons against the accepted replay | 120960 |
| of which equal | 120960 |
| trajectories re-evaluated | 6720 |
| wall time | 286.2 s |

Every assertion passed: the recomputed verdicts reproduce `results/e3_replay_*` field by field, every run meta's session tally reproduces from the call log, and every referral's executed objective is the RULE anchor's.

## Tables written

| table | rows |
|---|---|
| `E7_e3_profiles` | 48 |
| `E8_adjudication` | 112 |
| `E9_budget_effect` | 528 |
| `E10_register` | 288 |
| `E11_refusal_and_v56` | 96 |
| `E12_ladder_e3_rungs` | 150 |
| `E13_e3_costs` | 13 |

## E7 profiles: the headline

Each cell is SINGLE+G / MULTI-G at the same budget on the same 240 items.

| arm | budget | warranted | violation pass-through | mean WWT vs RULE | median variant tokens | cap binds |
|---|---|---|---|---|---|---|
| qwen14b | tight | 99.0% / 99.8% | 25.0% / 2.1% | +0.71 / +0.00 | 3005 / 3646 | 57.1% / 100.0% |
| qwen14b | loose | 99.6% / 99.6% | 47.2% / 55.9% | +0.78 / +2.62 | 4434 / 10284 | 3.8% / 4.2% |
| qwen27b | tight | 98.8% / 100.0% | 29.2% / 0.0% | -0.15 / +0.00 | 2932 / 2838 | 52.5% / 100.0% |
| qwen27b | loose | 98.8% / 97.9% | 51.4% / 50.0% | +2.09 / +2.82 | 3704 / 9698 | 5.8% / 13.3% |
| openai | tight | 97.5% / 100.0% | 45.8% / 4.2% | +1.92 / +0.00 | 3009 / 2540 | 35.0% / 100.0% |
| openai | loose | 99.6% / 99.6% | 61.8% / 63.2% | +3.23 / +4.62 | 3660 / 6702 | 2.9% / 4.6% |
| deepseek | tight | 97.1% / 99.6% | 4.9% / 0.0% | -0.00 / +0.00 | 3410 / 3408 | 72.9% / 100.0% |
| deepseek | loose | 100.0% / 100.0% | 27.1% / 36.1% | +0.23 / +0.03 | 5036 / 8519 | 24.6% / 16.7% |
| sonnet | tight | 99.2% / 97.9% | 34.0% / 18.1% | +0.17 / +0.14 | 5022 / 3913 | 39.2% / 100.0% |
| sonnet | loose | 100.0% / 100.0% | 47.9% / 43.8% | +0.17 / +0.35 | 5866 / 10316 | 2.1% / 2.9% |
| opus | tight | 98.3% / 99.6% | 33.3% / 9.7% | +0.32 / +0.01 | 5936 / 5200 | 41.2% / 100.0% |
| opus | loose | 100.0% / 99.6% | 43.8% / 41.7% | +3.14 / +3.04 | 6238 / 13247 | 1.7% / 3.3% |

## E8 adjudication: the headline

Both directions are stated as measured; nothing below is a verdict on the agent layer.

### SINGLE+G vs MULTI-G

| arm | budget | test | n | a-only / b-only | median diff over differing items (bh) | direction | p (raw) | p Holm (question) | p Holm (agent-layer family) |
|---|---|---|---|---|---|---|---|---|---|
| qwen14b | tight | mcnemar_false_block | 96 | 3 / 0 |  | SINGLE+G more often blocked false | 0.25 | 1 | 1 |
| qwen14b | tight | mcnemar_catch | 96 | 29 / 0 |  | SINGLE+G more often blocked correct | 3.72529e-09 | 4.47035e-08 | 3.50177e-07 |
| qwen14b | tight | mcnemar_violation_passthrough | 96 | 19 / 0 |  | SINGLE+G more often passed through | 3.8147e-06 | 3.8147e-05 | 0.000320435 |
| qwen14b | tight | wilcoxon_quality | 240 | 5 / 4 | 0.3424 | MULTI-G lower weighted tardiness on the 9 differing item(s) (4 lower for SINGLE+G, 5 lower for MULTI-G) | 0.238281 | 1 | 1 |
| qwen14b | loose | mcnemar_false_block | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| qwen14b | loose | mcnemar_catch | 96 | 1 / 0 |  | SINGLE+G more often blocked correct | 1 | 1 | 1 |
| qwen14b | loose | mcnemar_violation_passthrough | 96 | 1 / 5 |  | MULTI-G more often passed through | 0.21875 | 1 | 1 |
| qwen14b | loose | wilcoxon_quality | 240 | 4 / 10 | -0.7176 | SINGLE+G lower weighted tardiness on the 14 differing item(s) (10 lower for SINGLE+G, 4 lower for MULTI-G) | 0.199097 | 1 | 1 |
| qwen27b | tight | mcnemar_false_block | 96 | 3 / 0 |  | SINGLE+G more often blocked false | 0.25 | 1 | 1 |
| qwen27b | tight | mcnemar_catch | 96 | 17 / 0 |  | SINGLE+G more often blocked correct | 1.52588e-05 | 0.000137329 | 0.00126462 |
| qwen27b | tight | mcnemar_violation_passthrough | 96 | 20 / 0 |  | SINGLE+G more often passed through | 1.90735e-06 | 2.09808e-05 | 0.000164032 |
| qwen27b | tight | wilcoxon_quality | 240 | 7 / 8 | -0.0492 | SINGLE+G lower weighted tardiness on the 15 differing item(s) (8 lower for SINGLE+G, 7 lower for MULTI-G) | 0.55188 | 1 | 1 |
| qwen27b | loose | mcnemar_false_block | 96 | 0 / 2 |  | MULTI-G more often blocked false | 0.5 | 1 | 1 |
| qwen27b | loose | mcnemar_catch | 96 | 3 / 10 |  | MULTI-G more often blocked correct | 0.0922852 | 0.553711 | 1 |
| qwen27b | loose | mcnemar_violation_passthrough | 96 | 3 / 1 |  | SINGLE+G more often passed through | 0.625 | 1 | 1 |
| qwen27b | loose | wilcoxon_quality | 240 | 0 / 1 | -177.5000 | SINGLE+G lower weighted tardiness on the 1 differing item(s) (1 lower for SINGLE+G, 0 lower for MULTI-G) | 1 | 1 | 1 |
| openai | tight | mcnemar_false_block | 96 | 6 / 0 |  | SINGLE+G more often blocked false | 0.03125 | 0.375 | 1 |
| openai | tight | mcnemar_catch | 96 | 35 / 2 |  | SINGLE+G more often blocked correct | 1.02445e-08 | 1.1269e-07 | 9.42498e-07 |
| openai | tight | mcnemar_violation_passthrough | 96 | 36 / 0 |  | SINGLE+G more often passed through | 2.91038e-11 | 3.49246e-10 | 2.79397e-09 |
| openai | tight | wilcoxon_quality | 240 | 10 / 6 | 0.3630 | MULTI-G lower weighted tardiness on the 16 differing item(s) (6 lower for SINGLE+G, 10 lower for MULTI-G) | 0.292908 | 1 | 1 |
| openai | loose | mcnemar_false_block | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| openai | loose | mcnemar_catch | 96 | 0 / 2 |  | MULTI-G more often blocked correct | 0.5 | 1 | 1 |
| openai | loose | mcnemar_violation_passthrough | 96 | 6 / 4 |  | SINGLE+G more often passed through | 0.753906 | 1 | 1 |
| openai | loose | wilcoxon_quality | 240 | 1 / 5 | -2.3152 | SINGLE+G lower weighted tardiness on the 6 differing item(s) (5 lower for SINGLE+G, 1 lower for MULTI-G) | 0.09375 | 1 | 1 |
| deepseek | tight | mcnemar_false_block | 96 | 7 / 1 |  | SINGLE+G more often blocked false | 0.0703125 | 0.773438 | 1 |
| deepseek | tight | mcnemar_catch | 96 | 11 / 0 |  | SINGLE+G more often blocked correct | 0.000976562 | 0.00683594 | 0.0732422 |
| deepseek | tight | mcnemar_violation_passthrough | 96 | 4 / 0 |  | SINGLE+G more often passed through | 0.125 | 0.875 | 1 |
| deepseek | tight | wilcoxon_quality | 240 | 1 / 1 | -0.4688 | SINGLE+G lower weighted tardiness on the 2 differing item(s) (1 lower for SINGLE+G, 1 lower for MULTI-G) | 1 | 1 | 1 |
| deepseek | loose | mcnemar_false_block | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| deepseek | loose | mcnemar_catch | 96 | 4 / 0 |  | SINGLE+G more often blocked correct | 0.125 | 0.625 | 1 |
| deepseek | loose | mcnemar_violation_passthrough | 96 | 5 / 12 |  | MULTI-G more often passed through | 0.143463 | 0.875 | 1 |
| deepseek | loose | wilcoxon_quality | 240 | 5 / 4 | 0.5592 | MULTI-G lower weighted tardiness on the 9 differing item(s) (4 lower for SINGLE+G, 5 lower for MULTI-G) | 0.425781 | 1 | 1 |
| sonnet | tight | mcnemar_false_block | 96 | 1 / 4 |  | MULTI-G more often blocked false | 0.375 | 1 | 1 |
| sonnet | tight | mcnemar_catch | 96 | 20 / 1 |  | SINGLE+G more often blocked correct | 2.09808e-05 | 0.000167847 | 0.00169945 |
| sonnet | tight | mcnemar_violation_passthrough | 96 | 17 / 3 |  | SINGLE+G more often passed through | 0.00257683 | 0.0206146 | 0.190685 |
| sonnet | tight | wilcoxon_quality | 240 | 4 / 11 | -0.7720 | SINGLE+G lower weighted tardiness on the 15 differing item(s) (11 lower for SINGLE+G, 4 lower for MULTI-G) | 0.0541382 | 0.649658 | 1 |
| sonnet | loose | mcnemar_false_block | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| sonnet | loose | mcnemar_catch | 96 | 0 / 2 |  | MULTI-G more often blocked correct | 0.5 | 1 | 1 |
| sonnet | loose | mcnemar_violation_passthrough | 96 | 5 / 5 |  | no difference (5 = 5) | 1 | 1 | 1 |
| sonnet | loose | wilcoxon_quality | 240 | 2 / 4 | -0.7660 | SINGLE+G lower weighted tardiness on the 6 differing item(s) (4 lower for SINGLE+G, 2 lower for MULTI-G) | 0.15625 | 1 | 1 |
| opus | tight | mcnemar_false_block | 96 | 3 / 0 |  | SINGLE+G more often blocked false | 0.25 | 1 | 1 |
| opus | tight | mcnemar_catch | 96 | 27 / 0 |  | SINGLE+G more often blocked correct | 1.49012e-08 | 1.49012e-07 | 1.35601e-06 |
| opus | tight | mcnemar_violation_passthrough | 96 | 26 / 3 |  | SINGLE+G more often passed through | 1.52364e-05 | 0.000137128 | 0.00126462 |
| opus | tight | wilcoxon_quality | 240 | 6 / 8 | -0.0492 | SINGLE+G lower weighted tardiness on the 14 differing item(s) (8 lower for SINGLE+G, 6 lower for MULTI-G) | 0.796021 | 1 | 1 |
| opus | loose | mcnemar_false_block | 96 | 0 / 1 |  | MULTI-G more often blocked false | 1 | 1 | 1 |
| opus | loose | mcnemar_catch | 96 | 0 / 1 |  | MULTI-G more often blocked correct | 1 | 1 | 1 |
| opus | loose | mcnemar_violation_passthrough | 96 | 2 / 2 |  | no difference (2 = 2) | 1 | 1 | 1 |
| opus | loose | wilcoxon_quality | 240 | 1 / 0 | 24.2536 | MULTI-G lower weighted tardiness on the 1 differing item(s) (0 lower for SINGLE+G, 1 lower for MULTI-G) | 1 | 1 | 1 |

### MULTI-G vs MULTI-UG

| arm | budget | test | n | a-only / b-only | median diff over differing items (bh) | direction | p (raw) | p Holm (question) | p Holm (agent-layer family) |
|---|---|---|---|---|---|---|---|---|---|
| qwen14b | tight | mcnemar_false_block | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| qwen14b | tight | mcnemar_catch | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| qwen14b | tight | mcnemar_violation_passthrough | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| qwen14b | tight | wilcoxon_quality | 240 | 0 / 0 |  | identical weighted tardiness on every item | 1 | 1 | 1 |
| qwen14b | loose | mcnemar_false_block | 96 | 1 / 0 |  | MULTI-G more often blocked false | 1 | 1 | 1 |
| qwen14b | loose | mcnemar_catch | 96 | 2 / 0 |  | MULTI-G more often blocked correct | 0.5 | 1 | 1 |
| qwen14b | loose | mcnemar_violation_passthrough | 96 | 2 / 26 |  | MULTI-UG more often passed through | 3.03239e-06 | 3.33562e-05 | 0.000257753 |
| qwen14b | loose | wilcoxon_quality | 240 | 0 / 25 | -368.0024 | MULTI-G lower weighted tardiness on the 25 differing item(s) (25 lower for MULTI-G, 0 lower for MULTI-UG) | 5.96046e-08 | 5.96046e-07 | 5.30481e-06 |
| qwen27b | tight | mcnemar_false_block | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| qwen27b | tight | mcnemar_catch | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| qwen27b | tight | mcnemar_violation_passthrough | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| qwen27b | tight | wilcoxon_quality | 240 | 0 / 0 |  | identical weighted tardiness on every item | 1 | 1 | 1 |
| qwen27b | loose | mcnemar_false_block | 96 | 5 / 0 |  | MULTI-G more often blocked false | 0.0625 | 0.75 | 1 |
| qwen27b | loose | mcnemar_catch | 96 | 15 / 0 |  | MULTI-G more often blocked correct | 6.10352e-05 | 0.000732422 | 0.00488281 |
| qwen27b | loose | mcnemar_violation_passthrough | 96 | 2 / 20 |  | MULTI-UG more often passed through | 0.000121117 | 0.00109005 | 0.0094471 |
| qwen27b | loose | wilcoxon_quality | 240 | 0 / 22 | -404.1572 | MULTI-G lower weighted tardiness on the 22 differing item(s) (22 lower for MULTI-G, 0 lower for MULTI-UG) | 4.76837e-07 | 3.8147e-06 | 4.14848e-05 |
| openai | tight | mcnemar_false_block | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| openai | tight | mcnemar_catch | 96 | 7 / 0 |  | MULTI-G more often blocked correct | 0.015625 | 0.171875 | 1 |
| openai | tight | mcnemar_violation_passthrough | 96 | 0 / 1 |  | MULTI-UG more often passed through | 1 | 1 | 1 |
| openai | tight | wilcoxon_quality | 240 | 0 / 1 | -468.9612 | MULTI-G lower weighted tardiness on the 1 differing item(s) (1 lower for MULTI-G, 0 lower for MULTI-UG) | 1 | 1 | 1 |
| openai | loose | mcnemar_false_block | 96 | 1 / 0 |  | MULTI-G more often blocked false | 1 | 1 | 1 |
| openai | loose | mcnemar_catch | 96 | 6 / 0 |  | MULTI-G more often blocked correct | 0.03125 | 0.28125 | 1 |
| openai | loose | mcnemar_violation_passthrough | 96 | 3 / 19 |  | MULTI-UG more often passed through | 0.000855446 | 0.00598812 | 0.0650139 |
| openai | loose | wilcoxon_quality | 240 | 0 / 25 | -261.7768 | MULTI-G lower weighted tardiness on the 25 differing item(s) (25 lower for MULTI-G, 0 lower for MULTI-UG) | 5.96046e-08 | 5.96046e-07 | 5.30481e-06 |
| deepseek | tight | mcnemar_false_block | 96 | 1 / 0 |  | MULTI-G more often blocked false | 1 | 1 | 1 |
| deepseek | tight | mcnemar_catch | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| deepseek | tight | mcnemar_violation_passthrough | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| deepseek | tight | wilcoxon_quality | 240 | 0 / 0 |  | identical weighted tardiness on every item | 1 | 1 | 1 |
| deepseek | loose | mcnemar_false_block | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| deepseek | loose | mcnemar_catch | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| deepseek | loose | mcnemar_violation_passthrough | 96 | 30 / 0 |  | MULTI-G more often passed through | 1.86265e-09 | 2.23517e-08 | 1.76951e-07 |
| deepseek | loose | wilcoxon_quality | 240 | 9 / 7 | 0.2156 | MULTI-G lower weighted tardiness on the 16 differing item(s) (7 lower for MULTI-G, 9 lower for MULTI-UG) | 0.771576 | 1 | 1 |
| sonnet | tight | mcnemar_false_block | 96 | 5 / 0 |  | MULTI-G more often blocked false | 0.0625 | 0.75 | 1 |
| sonnet | tight | mcnemar_catch | 96 | 7 / 0 |  | MULTI-G more often blocked correct | 0.015625 | 0.171875 | 1 |
| sonnet | tight | mcnemar_violation_passthrough | 96 | 0 / 3 |  | MULTI-UG more often passed through | 0.25 | 1 | 1 |
| sonnet | tight | wilcoxon_quality | 240 | 0 / 3 | -428.6500 | MULTI-G lower weighted tardiness on the 3 differing item(s) (3 lower for MULTI-G, 0 lower for MULTI-UG) | 0.25 | 1 | 1 |
| sonnet | loose | mcnemar_false_block | 96 | 0 / 0 |  | no difference (0 = 0) | 1 | 1 | 1 |
| sonnet | loose | mcnemar_catch | 96 | 4 / 0 |  | MULTI-G more often blocked correct | 0.125 | 1 | 1 |
| sonnet | loose | mcnemar_violation_passthrough | 96 | 4 / 25 |  | MULTI-UG more often passed through | 0.000103716 | 0.00103716 | 0.00819355 |
| sonnet | loose | wilcoxon_quality | 240 | 0 / 27 | -308.9022 | MULTI-G lower weighted tardiness on the 27 differing item(s) (27 lower for MULTI-G, 0 lower for MULTI-UG) | 1.49012e-08 | 1.63913e-07 | 1.35601e-06 |
| opus | tight | mcnemar_false_block | 96 | 1 / 0 |  | MULTI-G more often blocked false | 1 | 1 | 1 |
| opus | tight | mcnemar_catch | 96 | 3 / 0 |  | MULTI-G more often blocked correct | 0.25 | 1 | 1 |
| opus | tight | mcnemar_violation_passthrough | 96 | 0 / 1 |  | MULTI-UG more often passed through | 1 | 1 | 1 |
| opus | tight | wilcoxon_quality | 240 | 0 / 1 | -428.6500 | MULTI-G lower weighted tardiness on the 1 differing item(s) (1 lower for MULTI-G, 0 lower for MULTI-UG) | 1 | 1 | 1 |
| opus | loose | mcnemar_false_block | 96 | 1 / 0 |  | MULTI-G more often blocked false | 1 | 1 | 1 |
| opus | loose | mcnemar_catch | 96 | 1 / 0 |  | MULTI-G more often blocked correct | 1 | 1 | 1 |
| opus | loose | mcnemar_violation_passthrough | 96 | 4 / 23 |  | MULTI-UG more often passed through | 0.000310749 | 0.00248599 | 0.0239277 |
| opus | loose | wilcoxon_quality | 240 | 0 / 28 | -254.6116 | MULTI-G lower weighted tardiness on the 28 differing item(s) (28 lower for MULTI-G, 0 lower for MULTI-UG) | 7.45058e-09 | 8.9407e-08 | 6.92904e-07 |

## E9 budget effect: the headline

21 outcome ordering(s) and 16 cost ordering(s) change sign between the tight and the loose budget. A cost ordering flips mechanically when a pipeline cannot finish inside the tight cap, so only the outcome rows answer the flip question.

| arm | subject | metric | kind | tight | loose |
|---|---|---|---|---|---|
| qwen14b | SINGLE+G minus MULTI-G | wwt_original_mean_bh | outcome | 0.707582 | -1.847558 |
| qwen14b | SINGLE+G minus MULTI-G | wwt_vs_rule_mean_bh | outcome | 0.707582 | -1.847558 |
| qwen14b | SINGLE+G minus MULTI-G | violation_pass_through | outcome | 0.229167 | -0.086806 |
| qwen14b | SINGLE+G minus MULTI-G | violation_pass_through_strict | outcome | 0.152778 | -0.086806 |
| qwen27b | SINGLE+G minus MULTI-G | all_tokens_median | cost | 94.500000 | -5995.000000 |
| qwen27b | SINGLE+G minus MULTI-G | variant_tokens_median | cost | 94.500000 | -5995.000000 |
| qwen27b | SINGLE+G minus MULTI-G | warranted_outcome_rate | outcome | -0.012500 | 0.008333 |
| qwen27b | SINGLE+G minus MULTI-G | false_block_rate | outcome | 0.031250 | -0.020833 |
| openai | SINGLE+G minus MULTI-G | all_tokens_median | cost | 469.000000 | -3042.000000 |
| openai | SINGLE+G minus MULTI-G | variant_tokens_median | cost | 469.000000 | -3042.000000 |
| openai | SINGLE+G minus MULTI-G | variant_tokens_mean | cost | 389.137500 | -3286.325000 |
| openai | SINGLE+G minus MULTI-G | wwt_original_mean_bh | outcome | 1.924478 | -1.388597 |
| openai | SINGLE+G minus MULTI-G | wwt_vs_rule_mean_bh | outcome | 1.924478 | -1.388597 |
| openai | SINGLE+G minus MULTI-G | violation_pass_through | outcome | 0.416667 | -0.013889 |
| openai | SINGLE+G minus MULTI-G | violation_pass_through_strict | outcome | 0.298611 | -0.013889 |
| openai | SINGLE+G minus MULTI-G | certified_gap_median | outcome | 0.010924 | -0.000936 |
| deepseek | SINGLE+G minus MULTI-G | cap_binding_share | cost | -0.270833 | 0.079167 |
| deepseek | SINGLE+G minus MULTI-G | all_tokens_median | cost | 1.500000 | -3483.000000 |
| deepseek | SINGLE+G minus MULTI-G | variant_tokens_median | cost | 1.500000 | -3483.000000 |
| deepseek | SINGLE+G minus MULTI-G | wwt_original_mean_bh | outcome | -0.003907 | 0.192245 |
| deepseek | SINGLE+G minus MULTI-G | wwt_vs_rule_mean_bh | outcome | -0.003907 | 0.192245 |
| deepseek | SINGLE+G minus MULTI-G | violation_pass_through | outcome | 0.048611 | -0.090278 |
| deepseek | SINGLE+G minus MULTI-G | violation_pass_through_strict | outcome | 0.041667 | -0.097222 |
| sonnet | SINGLE+G minus MULTI-G | all_tokens_median | cost | 1109.000000 | -4450.000000 |
| sonnet | SINGLE+G minus MULTI-G | variant_tokens_median | cost | 1109.000000 | -4450.000000 |
| sonnet | SINGLE+G minus MULTI-G | variant_tokens_mean | cost | 310.191667 | -4735.595833 |
| sonnet | SINGLE+G minus MULTI-G | usd_total | cost | 0.466588 | -1.509325 |
| sonnet | SINGLE+G minus MULTI-G | wwt_original_mean_bh | outcome | 0.022430 | -0.179548 |
| sonnet | SINGLE+G minus MULTI-G | wwt_vs_rule_mean_bh | outcome | 0.022430 | -0.179548 |
| sonnet | SINGLE+G minus MULTI-G | certified_gap_median | outcome | 0.003413 | -0.002940 |
| opus | SINGLE+G minus MULTI-G | all_tokens_median | cost | 737.000000 | -7009.500000 |
| opus | SINGLE+G minus MULTI-G | variant_tokens_median | cost | 737.000000 | -7009.500000 |
| opus | SINGLE+G minus MULTI-G | variant_tokens_mean | cost | 574.854167 | -6214.508333 |
| opus | SINGLE+G minus MULTI-G | usd_total | cost | 3.065330 | -4.643163 |
| opus | SINGLE+G minus MULTI-G | warranted_outcome_rate | outcome | -0.012500 | 0.004167 |
| opus | SINGLE+G minus MULTI-G | false_block_rate | outcome | 0.031250 | -0.010417 |
| opus | SINGLE+G minus MULTI-G | certified_gap_median | outcome | 0.001236 | -0.003300 |

Cap-binding share, which is the condition the flip question turns on:

| arm | SINGLE+G tight | SINGLE+G loose | MULTI-G tight | MULTI-G loose |
|---|---|---|---|---|
| qwen14b | 57.1% | 3.8% | 100.0% | 4.2% |
| qwen27b | 52.5% | 5.8% | 100.0% | 13.3% |
| openai | 35.0% | 2.9% | 100.0% | 4.6% |
| deepseek | 72.9% | 24.6% | 100.0% | 16.7% |
| sonnet | 39.2% | 2.1% | 100.0% | 2.9% |
| opus | 41.2% | 1.7% | 100.0% | 3.3% |

## E10 register: the headline

Of 288 register-stratified tests, 22 have a Holm-adjusted p below 0.05 within their register family.

| register | arm | budget | contrast | test | n | direction | p (raw) | p Holm |
|---|---|---|---|---|---|---|---|---|
| formal | qwen14b | loose | MULTI-G vs MULTI-UG | mcnemar_violation_passthrough | 40 | MULTI-UG more often passed through | 0.000976562 | 0.0117188 |
| formal | qwen14b | loose | MULTI-G vs MULTI-UG | wilcoxon_quality | 98 | MULTI-G lower weighted tardiness on the 11 differing item(s) (11 lower for MULTI-G, 0 lower for MULTI-UG) | 0.000976562 | 0.0117188 |
| formal | qwen27b | tight | SINGLE+G vs MULTI-G | mcnemar_catch | 40 | SINGLE+G more often blocked correct | 0.00195312 | 0.0195312 |
| formal | openai | tight | SINGLE+G vs MULTI-G | mcnemar_catch | 40 | SINGLE+G more often blocked correct | 3.05176e-05 | 0.000366211 |
| formal | openai | tight | SINGLE+G vs MULTI-G | mcnemar_violation_passthrough | 40 | SINGLE+G more often passed through | 0.00012207 | 0.00146484 |
| formal | openai | loose | MULTI-G vs MULTI-UG | mcnemar_violation_passthrough | 40 | MULTI-UG more often passed through | 0.00390625 | 0.0390625 |
| formal | openai | loose | MULTI-G vs MULTI-UG | wilcoxon_quality | 98 | MULTI-G lower weighted tardiness on the 11 differing item(s) (11 lower for MULTI-G, 0 lower for MULTI-UG) | 0.000976562 | 0.0117188 |
| formal | deepseek | loose | MULTI-G vs MULTI-UG | mcnemar_violation_passthrough | 40 | MULTI-G more often passed through | 0.000976562 | 0.0117188 |
| formal | sonnet | tight | SINGLE+G vs MULTI-G | mcnemar_catch | 40 | SINGLE+G more often blocked correct | 0.00195312 | 0.0195312 |
| formal | sonnet | loose | MULTI-G vs MULTI-UG | wilcoxon_quality | 98 | MULTI-G lower weighted tardiness on the 11 differing item(s) (11 lower for MULTI-G, 0 lower for MULTI-UG) | 0.000976562 | 0.0117188 |
| formal | opus | tight | SINGLE+G vs MULTI-G | mcnemar_catch | 40 | SINGLE+G more often blocked correct | 0.000488281 | 0.00537109 |
| formal | opus | loose | MULTI-G vs MULTI-UG | wilcoxon_quality | 98 | MULTI-G lower weighted tardiness on the 10 differing item(s) (10 lower for MULTI-G, 0 lower for MULTI-UG) | 0.00195312 | 0.0175781 |
| terse | qwen14b | tight | SINGLE+G vs MULTI-G | mcnemar_catch | 29 | SINGLE+G more often blocked correct | 6.10352e-05 | 0.000732422 |
| terse | qwen14b | loose | MULTI-G vs MULTI-UG | wilcoxon_quality | 73 | MULTI-G lower weighted tardiness on the 10 differing item(s) (10 lower for MULTI-G, 0 lower for MULTI-UG) | 0.00195312 | 0.0234375 |
| terse | qwen27b | loose | MULTI-G vs MULTI-UG | wilcoxon_quality | 73 | MULTI-G lower weighted tardiness on the 9 differing item(s) (9 lower for MULTI-G, 0 lower for MULTI-UG) | 0.00390625 | 0.03125 |
| terse | openai | tight | SINGLE+G vs MULTI-G | mcnemar_catch | 29 | SINGLE+G more often blocked correct | 0.00341797 | 0.0375977 |
| terse | openai | tight | SINGLE+G vs MULTI-G | mcnemar_violation_passthrough | 29 | SINGLE+G more often passed through | 0.000976562 | 0.0117188 |
| terse | openai | loose | MULTI-G vs MULTI-UG | wilcoxon_quality | 73 | MULTI-G lower weighted tardiness on the 10 differing item(s) (10 lower for MULTI-G, 0 lower for MULTI-UG) | 0.00195312 | 0.0234375 |
| terse | sonnet | loose | MULTI-G vs MULTI-UG | wilcoxon_quality | 73 | MULTI-G lower weighted tardiness on the 10 differing item(s) (10 lower for MULTI-G, 0 lower for MULTI-UG) | 0.00195312 | 0.0234375 |
| terse | opus | loose | MULTI-G vs MULTI-UG | wilcoxon_quality | 73 | MULTI-G lower weighted tardiness on the 10 differing item(s) (10 lower for MULTI-G, 0 lower for MULTI-UG) | 0.00195312 | 0.0234375 |
| conversational | openai | tight | SINGLE+G vs MULTI-G | mcnemar_violation_passthrough | 27 | SINGLE+G more often passed through | 0.000976562 | 0.0117188 |
| conversational | deepseek | loose | MULTI-G vs MULTI-UG | mcnemar_violation_passthrough | 27 | MULTI-G more often passed through | 0.000244141 | 0.00292969 |

## E11 V5 and V6: the headline

V5 referral share (the correct behaviour) and V6 applied-with-operations share, SINGLE+G and MULTI-G at both budgets.

| arm | V5 refer S+G tight | V5 refer M-G tight | V5 refer S+G loose | V5 refer M-G loose | V6 applied S+G tight | V6 applied M-G tight | V6 applied S+G loose | V6 applied M-G loose |
|---|---|---|---|---|---|---|---|---|
| qwen14b | 75.0% | 95.8% | 70.8% | 45.8% | 45.8% | 8.3% | 83.3% | 93.8% |
| qwen27b | 95.8% | 100.0% | 83.3% | 75.0% | 87.5% | 0.0% | 91.7% | 83.3% |
| openai | 45.8% | 70.8% | 45.8% | 20.8% | 62.5% | 8.3% | 91.7% | 83.3% |
| deepseek | 100.0% | 100.0% | 100.0% | 70.8% | 12.5% | 0.0% | 66.7% | 62.5% |
| sonnet | 79.2% | 62.5% | 83.3% | 87.5% | 83.3% | 37.5% | 87.5% | 66.7% |
| opus | 91.7% | 95.8% | 91.7% | 100.0% | 66.7% | 25.0% | 62.5% | 58.3% |

## E12 ladder rungs: the headline

The two agent rungs on the E3-240 slice, at the loose budget where the cap binds on only a few percent of trajectories. Weighted tardiness is measured against the RULE anchor of the same 240 items.

| arm | SINGLE+G warranted | SINGLE+G WWT vs RULE | MULTI-G warranted | MULTI-G WWT vs RULE | MULTI-UG warranted | MULTI-UG WWT vs RULE | SINGLE-UG * warranted | SINGLE-UG * WWT vs RULE |
|---|---|---|---|---|---|---|---|---|
| qwen14b | 99.6% | +0.78 | 99.6% | +2.62 | 9.4% | +41.83 | 15.0% | +42.23 |
| qwen27b | 98.8% | +2.09 | 97.9% | +2.82 | 20.4% | +39.61 | 17.5% | +37.99 |
| openai | 99.6% | +3.23 | 99.6% | +4.62 | 4.6% | +42.70 | 7.1% | +48.02 |
| deepseek | 100.0% | +0.23 | 100.0% | +0.03 | 100.0% | +0.00 | 100.0% | +0.00 |
| sonnet | 100.0% | +0.17 | 100.0% | +0.35 | 23.8% | +40.82 | 21.7% | +41.60 |
| opus | 100.0% | +3.14 | 99.6% | +3.04 | 25.8% | +47.38 | 22.9% | +48.01 |

## E13 cost: the headline

Recomputed USD 41.660879 against the run metas' 41.660879, residual -1.42e-14.

| arm | scope | USD (recomputed) | USD (run metas) | residual |
|---|---|---|---|---|
| qwen14b | grid | 0.000000 | 0.000000 | 0.00e+00 |
| qwen14b | calibration | 0.000000 | 0.000000 | 0.00e+00 |
| qwen27b | grid | 0.000000 | 0.000000 | 0.00e+00 |
| qwen27b | calibration | 0.000000 | 0.000000 | 0.00e+00 |
| openai | grid | 3.189965 | 3.189965 | -7.99e-15 |
| openai | calibration | 0.187876 | 0.187876 | 8.33e-17 |
| deepseek | grid | 0.634164 | 0.634164 | -1.11e-15 |
| deepseek | calibration | 0.054059 | 0.054059 | -4.86e-17 |
| sonnet | grid | 10.041007 | 10.041007 | -5.33e-15 |
| sonnet | calibration | 0.830226 | 0.830226 | 6.66e-16 |
| opus | grid | 24.525800 | 24.525800 | -3.55e-15 |
| opus | calibration | 2.197781 | 2.197782 | -1.33e-15 |
| ALL | grid + calibration | 41.660879 | 41.660879 | -1.42e-14 |

## Data-quality observations

- **Vendor refusals inside the opus pipeline.** 136 calls were refused by the provider's safety layer, on free-text intermediate stages only (17 multi_obs, 69 multi_sched, 50 single_act), touching 133 trajectories and 77 distinct items. None landed on a first final, so every trajectory still produced a proposal and no terminal is a model refusal; the refused stage still billed its prompt, and the pipeline continued with an empty stage output. decisions.md records zero refusals on the E3 smoke, so this is a full-grid observation the log does not yet carry.
- **The accepted replay's twin-pair table collapses repeats.** `e3_replay.twin_pairs` keys its item map on (arm, level, variant, item_id) without the repeat, so for the two-repeat qwen14b arm the last repeat silently wins and every printed pair count is 96 rather than 192. The counts it prints are correct for that repeat; this analysis reproduces them as an assertion and runs its own tests per repeat instead of pooling.
- **An unguarded variant that refers everything has not behaved safely.** 2 refer at or above 95% while the guarded variant of the same trajectories executes operations: deepseek loose SINGLE-UG refers 100% against SINGLE+G executing 44%; deepseek loose MULTI-UG refers 100% against MULTI-G executing 50%. The cause is the parse, not the model's judgement. The unguarded configuration repairs an off-shape final leniently, and where the repair recognises none of the operations it yields an empty list, which E3 reads as the frozen prompt's refusal signal; the strict parse blocks the same output at the schema stage, feeds the verdict back, and the revision returns the operations in the frozen encoding. A warranted-outcome rate near 100% on such a cell means nothing was executed, and must not be read as a safety result.
- **Unguarded variants inherit the guarded revision tail's token cost** in the accepted replay, which charges every variant the whole trajectory's `all_tokens`. E7 keeps that column for the reconciliation and adds `variant_tokens_*`, which charges each variant only the calls it consumes.
- **Wall time is a throughput figure.** Every arm ran with six trajectories in flight (four on the resume sessions), so `wall_s` is not a single-stream latency measurement and must not be reported as one.
- **The E1/E3 terminal-state divergence is live.** An empty operations list is a referral in E3 and an applied-but-inert proposal in E1. E12 carries the divergence in its header and prints `n_referred_empty_ops`.
- **The E3 cost ledger is 41.66 USD, not the 40.7 the decisions log estimates.** The grids bill 38.39 and the calibrations 3.27. The gap to the logged figure is the two resume sessions, which the log's per-arm figures predate, plus calibrations that cost more than the round number the entry carried. Every arm reconciles exactly against its own run metas, so this is a ledger note, not a discrepancy in the data.
- **Superseded error attempts.** openai 5; opus 7. Every one was retried by a resume session and the final row per key is `ok`, so no rate is computed over an error row; the superseded attempts still billed, and E13 counts them.

## Open questions for the orchestrator

1. **Holm granularity.** The guidance pre-declares an agent-layer family without fixing its size. E8 reports both readings: `p_holm_family` corrects one question across arms and budget levels, and `p_holm_agent_layer` corrects the whole primary family at once. Which one the paper prints is a pre-declaration the orchestrator owns.
2. **The qwen14b second repeat.** The tests run on repeat 0 so the pairs are independent; `repeat_scope` `r1` is reported beside them. If the paper wants a pooled two-repeat test, the pairing is no longer independent and the correction has to change with it.
3. **Which token column the cost claim uses.** `all_tokens` is what the budget governor capped and what the accepted replay summarises; `variant_tokens` is what each variant actually spends. The matched-budget claim is about the first, and a cost-of-ownership claim is about the second.
4. **The vendor-refusal wall inside the opus pipeline** has no counterpart in the other arms and no terminal state of its own. Whether it belongs in the E3 narrative or only in the E1 free-mode discussion is a framing decision, not a measurement one.
5. **The E12 rungs are on 240 items, T5's other rungs on 2,000.** Merging them into one printed exhibit needs the item-set difference stated in the caption, or the other rungs recomputed on the E3 slice.

