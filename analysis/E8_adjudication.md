# E8. SINGLE+G vs MULTI-G and MULTI-G vs MULTI-UG at matched budgets

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

SINGLE+G against MULTI-G on identical items at a matched all-token budget, and MULTI-G against MULTI-UG, which is the guard's effect at a fixed architecture. Statistics only: this table reports the numbers and draws no conclusion from them.

Three exact McNemar tests and one paired Wilcoxon per arm x budget level x contrast. McNemar runs on the discordant pairs of a binary disposition (a false block on the 96 matched benign twins, a correct block on the 96 labelled violations, and a violation reaching the executed schedule on the same 96); the Wilcoxon runs on the per-item difference in weighted tardiness across all 240 items, where a blocked, referred or failed instruction leaves the baseline schedule standing.

The tests need one observation per item, so they run on repeat 0. The qwen14b arm's second repeat is reported beside it (`repeat_scope` `r1`, `in_primary_family` false) as a repeat-stability check and is outside the Holm family.

Two Holm corrections are given because the guidance pre-declares an agent-layer family without fixing its granularity: `p_holm_family` corrects one question asked across arms and budget levels, and `p_holm_agent_layer` corrects the whole primary family at once.

### SINGLE+G vs MULTI-G

| arm | budget | test | n | a-only / b-only | median diff over differing items (bh) | effect | direction | p | p Holm (question) | p Holm (family) |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen14b | tight | mcnemar_false_block | 96 | 3 / 0 | - | +0.0312 | SINGLE+G more often blocked false | 0.25 | 1 | 1 |
| qwen14b | tight | mcnemar_catch | 96 | 29 / 0 | - | +0.3021 | SINGLE+G more often blocked correct | 3.725e-09 | 4.47e-08 | 3.502e-07 |
| qwen14b | tight | mcnemar_violation_passthrough | 96 | 19 / 0 | - | +0.1979 | SINGLE+G more often passed through | 3.815e-06 | 3.815e-05 | 0.0003204 |
| qwen14b | tight | wilcoxon_quality | 240 | 5 / 4 | +0.342 | +0.4667 | MULTI-G lower weighted tardiness on the 9 differing item(s) (4 lower for SINGLE+G, 5 lower for MULTI-G) | 0.2383 | 1 | 1 |
| qwen14b | loose | mcnemar_false_block | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| qwen14b | loose | mcnemar_catch | 96 | 1 / 0 | - | +0.0104 | SINGLE+G more often blocked correct | 1 | 1 | 1 |
| qwen14b | loose | mcnemar_violation_passthrough | 96 | 1 / 5 | - | -0.0417 | MULTI-G more often passed through | 0.2188 | 1 | 1 |
| qwen14b | loose | wilcoxon_quality | 240 | 4 / 10 | -0.718 | -0.4000 | SINGLE+G lower weighted tardiness on the 14 differing item(s) (10 lower for SINGLE+G, 4 lower for MULTI-G) | 0.1991 | 1 | 1 |
| qwen27b | tight | mcnemar_false_block | 96 | 3 / 0 | - | +0.0312 | SINGLE+G more often blocked false | 0.25 | 1 | 1 |
| qwen27b | tight | mcnemar_catch | 96 | 17 / 0 | - | +0.1771 | SINGLE+G more often blocked correct | 1.526e-05 | 0.0001373 | 0.001265 |
| qwen27b | tight | mcnemar_violation_passthrough | 96 | 20 / 0 | - | +0.2083 | SINGLE+G more often passed through | 1.907e-06 | 2.098e-05 | 0.000164 |
| qwen27b | tight | wilcoxon_quality | 240 | 7 / 8 | -0.049 | -0.1833 | SINGLE+G lower weighted tardiness on the 15 differing item(s) (8 lower for SINGLE+G, 7 lower for MULTI-G) | 0.5519 | 1 | 1 |
| qwen27b | loose | mcnemar_false_block | 96 | 0 / 2 | - | -0.0208 | MULTI-G more often blocked false | 0.5 | 1 | 1 |
| qwen27b | loose | mcnemar_catch | 96 | 3 / 10 | - | -0.0729 | MULTI-G more often blocked correct | 0.09229 | 0.5537 | 1 |
| qwen27b | loose | mcnemar_violation_passthrough | 96 | 3 / 1 | - | +0.0208 | SINGLE+G more often passed through | 0.625 | 1 | 1 |
| qwen27b | loose | wilcoxon_quality | 240 | 0 / 1 | -177.500 | -1.0000 | SINGLE+G lower weighted tardiness on the 1 differing item(s) (1 lower for SINGLE+G, 0 lower for MULTI-G) | 1 | 1 | 1 |
| openai | tight | mcnemar_false_block | 96 | 6 / 0 | - | +0.0625 | SINGLE+G more often blocked false | 0.03125 | 0.375 | 1 |
| openai | tight | mcnemar_catch | 96 | 35 / 2 | - | +0.3438 | SINGLE+G more often blocked correct | 1.024e-08 | 1.127e-07 | 9.425e-07 |
| openai | tight | mcnemar_violation_passthrough | 96 | 36 / 0 | - | +0.3750 | SINGLE+G more often passed through | 2.91e-11 | 3.492e-10 | 2.794e-09 |
| openai | tight | wilcoxon_quality | 240 | 10 / 6 | +0.363 | +0.3088 | MULTI-G lower weighted tardiness on the 16 differing item(s) (6 lower for SINGLE+G, 10 lower for MULTI-G) | 0.2929 | 1 | 1 |
| openai | loose | mcnemar_false_block | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| openai | loose | mcnemar_catch | 96 | 0 / 2 | - | -0.0208 | MULTI-G more often blocked correct | 0.5 | 1 | 1 |
| openai | loose | mcnemar_violation_passthrough | 96 | 6 / 4 | - | +0.0208 | SINGLE+G more often passed through | 0.7539 | 1 | 1 |
| openai | loose | wilcoxon_quality | 240 | 1 / 5 | -2.315 | -0.8095 | SINGLE+G lower weighted tardiness on the 6 differing item(s) (5 lower for SINGLE+G, 1 lower for MULTI-G) | 0.09375 | 1 | 1 |
| deepseek | tight | mcnemar_false_block | 96 | 7 / 1 | - | +0.0625 | SINGLE+G more often blocked false | 0.07031 | 0.7734 | 1 |
| deepseek | tight | mcnemar_catch | 96 | 11 / 0 | - | +0.1146 | SINGLE+G more often blocked correct | 0.0009766 | 0.006836 | 0.07324 |
| deepseek | tight | mcnemar_violation_passthrough | 96 | 4 / 0 | - | +0.0417 | SINGLE+G more often passed through | 0.125 | 0.875 | 1 |
| deepseek | tight | wilcoxon_quality | 240 | 1 / 1 | -0.469 | -0.3333 | SINGLE+G lower weighted tardiness on the 2 differing item(s) (1 lower for SINGLE+G, 1 lower for MULTI-G) | 1 | 1 | 1 |
| deepseek | loose | mcnemar_false_block | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| deepseek | loose | mcnemar_catch | 96 | 4 / 0 | - | +0.0417 | SINGLE+G more often blocked correct | 0.125 | 0.625 | 1 |
| deepseek | loose | mcnemar_violation_passthrough | 96 | 5 / 12 | - | -0.0729 | MULTI-G more often passed through | 0.1435 | 0.875 | 1 |
| deepseek | loose | wilcoxon_quality | 240 | 5 / 4 | +0.559 | +0.3333 | MULTI-G lower weighted tardiness on the 9 differing item(s) (4 lower for SINGLE+G, 5 lower for MULTI-G) | 0.4258 | 1 | 1 |
| sonnet | tight | mcnemar_false_block | 96 | 1 / 4 | - | -0.0312 | MULTI-G more often blocked false | 0.375 | 1 | 1 |
| sonnet | tight | mcnemar_catch | 96 | 20 / 1 | - | +0.1979 | SINGLE+G more often blocked correct | 2.098e-05 | 0.0001678 | 0.001699 |
| sonnet | tight | mcnemar_violation_passthrough | 96 | 17 / 3 | - | +0.1458 | SINGLE+G more often passed through | 0.002577 | 0.02061 | 0.1907 |
| sonnet | tight | wilcoxon_quality | 240 | 4 / 11 | -0.772 | -0.5667 | SINGLE+G lower weighted tardiness on the 15 differing item(s) (11 lower for SINGLE+G, 4 lower for MULTI-G) | 0.05414 | 0.6497 | 1 |
| sonnet | loose | mcnemar_false_block | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| sonnet | loose | mcnemar_catch | 96 | 0 / 2 | - | -0.0208 | MULTI-G more often blocked correct | 0.5 | 1 | 1 |
| sonnet | loose | mcnemar_violation_passthrough | 96 | 5 / 5 | - | +0.0000 | no difference (5 = 5) | 1 | 1 | 1 |
| sonnet | loose | wilcoxon_quality | 240 | 2 / 4 | -0.766 | -0.7143 | SINGLE+G lower weighted tardiness on the 6 differing item(s) (4 lower for SINGLE+G, 2 lower for MULTI-G) | 0.1562 | 1 | 1 |
| opus | tight | mcnemar_false_block | 96 | 3 / 0 | - | +0.0312 | SINGLE+G more often blocked false | 0.25 | 1 | 1 |
| opus | tight | mcnemar_catch | 96 | 27 / 0 | - | +0.2812 | SINGLE+G more often blocked correct | 1.49e-08 | 1.49e-07 | 1.356e-06 |
| opus | tight | mcnemar_violation_passthrough | 96 | 26 / 3 | - | +0.2396 | SINGLE+G more often passed through | 1.524e-05 | 0.0001371 | 0.001265 |
| opus | tight | wilcoxon_quality | 240 | 6 / 8 | -0.049 | -0.0857 | SINGLE+G lower weighted tardiness on the 14 differing item(s) (8 lower for SINGLE+G, 6 lower for MULTI-G) | 0.796 | 1 | 1 |
| opus | loose | mcnemar_false_block | 96 | 0 / 1 | - | -0.0104 | MULTI-G more often blocked false | 1 | 1 | 1 |
| opus | loose | mcnemar_catch | 96 | 0 / 1 | - | -0.0104 | MULTI-G more often blocked correct | 1 | 1 | 1 |
| opus | loose | mcnemar_violation_passthrough | 96 | 2 / 2 | - | +0.0000 | no difference (2 = 2) | 1 | 1 | 1 |
| opus | loose | wilcoxon_quality | 240 | 1 / 0 | +24.254 | +1.0000 | MULTI-G lower weighted tardiness on the 1 differing item(s) (0 lower for SINGLE+G, 1 lower for MULTI-G) | 1 | 1 | 1 |

### MULTI-G vs MULTI-UG

| arm | budget | test | n | a-only / b-only | median diff over differing items (bh) | effect | direction | p | p Holm (question) | p Holm (family) |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen14b | tight | mcnemar_false_block | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| qwen14b | tight | mcnemar_catch | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| qwen14b | tight | mcnemar_violation_passthrough | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| qwen14b | tight | wilcoxon_quality | 240 | 0 / 0 | - | - | identical weighted tardiness on every item | 1 | 1 | 1 |
| qwen14b | loose | mcnemar_false_block | 96 | 1 / 0 | - | +0.0104 | MULTI-G more often blocked false | 1 | 1 | 1 |
| qwen14b | loose | mcnemar_catch | 96 | 2 / 0 | - | +0.0208 | MULTI-G more often blocked correct | 0.5 | 1 | 1 |
| qwen14b | loose | mcnemar_violation_passthrough | 96 | 2 / 26 | - | -0.2500 | MULTI-UG more often passed through | 3.032e-06 | 3.336e-05 | 0.0002578 |
| qwen14b | loose | wilcoxon_quality | 240 | 0 / 25 | -368.002 | -1.0000 | MULTI-G lower weighted tardiness on the 25 differing item(s) (25 lower for MULTI-G, 0 lower for MULTI-UG) | 5.96e-08 | 5.96e-07 | 5.305e-06 |
| qwen27b | tight | mcnemar_false_block | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| qwen27b | tight | mcnemar_catch | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| qwen27b | tight | mcnemar_violation_passthrough | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| qwen27b | tight | wilcoxon_quality | 240 | 0 / 0 | - | - | identical weighted tardiness on every item | 1 | 1 | 1 |
| qwen27b | loose | mcnemar_false_block | 96 | 5 / 0 | - | +0.0521 | MULTI-G more often blocked false | 0.0625 | 0.75 | 1 |
| qwen27b | loose | mcnemar_catch | 96 | 15 / 0 | - | +0.1562 | MULTI-G more often blocked correct | 6.104e-05 | 0.0007324 | 0.004883 |
| qwen27b | loose | mcnemar_violation_passthrough | 96 | 2 / 20 | - | -0.1875 | MULTI-UG more often passed through | 0.0001211 | 0.00109 | 0.009447 |
| qwen27b | loose | wilcoxon_quality | 240 | 0 / 22 | -404.157 | -1.0000 | MULTI-G lower weighted tardiness on the 22 differing item(s) (22 lower for MULTI-G, 0 lower for MULTI-UG) | 4.768e-07 | 3.815e-06 | 4.148e-05 |
| openai | tight | mcnemar_false_block | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| openai | tight | mcnemar_catch | 96 | 7 / 0 | - | +0.0729 | MULTI-G more often blocked correct | 0.01562 | 0.1719 | 1 |
| openai | tight | mcnemar_violation_passthrough | 96 | 0 / 1 | - | -0.0104 | MULTI-UG more often passed through | 1 | 1 | 1 |
| openai | tight | wilcoxon_quality | 240 | 0 / 1 | -468.961 | -1.0000 | MULTI-G lower weighted tardiness on the 1 differing item(s) (1 lower for MULTI-G, 0 lower for MULTI-UG) | 1 | 1 | 1 |
| openai | loose | mcnemar_false_block | 96 | 1 / 0 | - | +0.0104 | MULTI-G more often blocked false | 1 | 1 | 1 |
| openai | loose | mcnemar_catch | 96 | 6 / 0 | - | +0.0625 | MULTI-G more often blocked correct | 0.03125 | 0.2812 | 1 |
| openai | loose | mcnemar_violation_passthrough | 96 | 3 / 19 | - | -0.1667 | MULTI-UG more often passed through | 0.0008554 | 0.005988 | 0.06501 |
| openai | loose | wilcoxon_quality | 240 | 0 / 25 | -261.777 | -1.0000 | MULTI-G lower weighted tardiness on the 25 differing item(s) (25 lower for MULTI-G, 0 lower for MULTI-UG) | 5.96e-08 | 5.96e-07 | 5.305e-06 |
| deepseek | tight | mcnemar_false_block | 96 | 1 / 0 | - | +0.0104 | MULTI-G more often blocked false | 1 | 1 | 1 |
| deepseek | tight | mcnemar_catch | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| deepseek | tight | mcnemar_violation_passthrough | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| deepseek | tight | wilcoxon_quality | 240 | 0 / 0 | - | - | identical weighted tardiness on every item | 1 | 1 | 1 |
| deepseek | loose | mcnemar_false_block | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| deepseek | loose | mcnemar_catch | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| deepseek | loose | mcnemar_violation_passthrough | 96 | 30 / 0 | - | +0.3125 | MULTI-G more often passed through | 1.863e-09 | 2.235e-08 | 1.77e-07 |
| deepseek | loose | wilcoxon_quality | 240 | 9 / 7 | +0.216 | -0.0882 | MULTI-G lower weighted tardiness on the 16 differing item(s) (7 lower for MULTI-G, 9 lower for MULTI-UG) | 0.7716 | 1 | 1 |
| sonnet | tight | mcnemar_false_block | 96 | 5 / 0 | - | +0.0521 | MULTI-G more often blocked false | 0.0625 | 0.75 | 1 |
| sonnet | tight | mcnemar_catch | 96 | 7 / 0 | - | +0.0729 | MULTI-G more often blocked correct | 0.01562 | 0.1719 | 1 |
| sonnet | tight | mcnemar_violation_passthrough | 96 | 0 / 3 | - | -0.0312 | MULTI-UG more often passed through | 0.25 | 1 | 1 |
| sonnet | tight | wilcoxon_quality | 240 | 0 / 3 | -428.650 | -1.0000 | MULTI-G lower weighted tardiness on the 3 differing item(s) (3 lower for MULTI-G, 0 lower for MULTI-UG) | 0.25 | 1 | 1 |
| sonnet | loose | mcnemar_false_block | 96 | 0 / 0 | - | +0.0000 | no difference (0 = 0) | 1 | 1 | 1 |
| sonnet | loose | mcnemar_catch | 96 | 4 / 0 | - | +0.0417 | MULTI-G more often blocked correct | 0.125 | 1 | 1 |
| sonnet | loose | mcnemar_violation_passthrough | 96 | 4 / 25 | - | -0.2188 | MULTI-UG more often passed through | 0.0001037 | 0.001037 | 0.008194 |
| sonnet | loose | wilcoxon_quality | 240 | 0 / 27 | -308.902 | -1.0000 | MULTI-G lower weighted tardiness on the 27 differing item(s) (27 lower for MULTI-G, 0 lower for MULTI-UG) | 1.49e-08 | 1.639e-07 | 1.356e-06 |
| opus | tight | mcnemar_false_block | 96 | 1 / 0 | - | +0.0104 | MULTI-G more often blocked false | 1 | 1 | 1 |
| opus | tight | mcnemar_catch | 96 | 3 / 0 | - | +0.0312 | MULTI-G more often blocked correct | 0.25 | 1 | 1 |
| opus | tight | mcnemar_violation_passthrough | 96 | 0 / 1 | - | -0.0104 | MULTI-UG more often passed through | 1 | 1 | 1 |
| opus | tight | wilcoxon_quality | 240 | 0 / 1 | -428.650 | -1.0000 | MULTI-G lower weighted tardiness on the 1 differing item(s) (1 lower for MULTI-G, 0 lower for MULTI-UG) | 1 | 1 | 1 |
| opus | loose | mcnemar_false_block | 96 | 1 / 0 | - | +0.0104 | MULTI-G more often blocked false | 1 | 1 | 1 |
| opus | loose | mcnemar_catch | 96 | 1 / 0 | - | +0.0104 | MULTI-G more often blocked correct | 1 | 1 | 1 |
| opus | loose | mcnemar_violation_passthrough | 96 | 4 / 23 | - | -0.1979 | MULTI-UG more often passed through | 0.0003107 | 0.002486 | 0.02393 |
| opus | loose | wilcoxon_quality | 240 | 0 / 28 | -254.612 | -1.0000 | MULTI-G lower weighted tardiness on the 28 differing item(s) (28 lower for MULTI-G, 0 lower for MULTI-UG) | 7.451e-09 | 8.941e-08 | 6.929e-07 |

