# E10. The E8 contrasts stratified by register

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

The E8 contrasts inside each register. Register is the suite's built-in instruction-noise axis and the G-L0 control: the same 240 instructions are written formally, tersely and conversationally, and the degraded-context crossover reported in the generic literature would show up here as a register on which the multi-agent pipeline gains.

These rows are secondary. Each register carries roughly a third of the items (98 formal, 73 terse, 69 conversational, of which the twin and violation halves are smaller still), so the tests have little power and the Holm correction is taken within a register, not across the primary family.

### SINGLE+G vs MULTI-G on end-task quality, by register

| arm | budget | register | n | median diff (bh) | effect | direction | p | p Holm (within register) |
|---|---|---|---|---|---|---|---|---|
| qwen14b | tight | formal | 98 | +0.000 | +1.0000 | MULTI-G lower weighted tardiness on the 2 differing item(s) (0 lower for SINGLE+G, 2 lower for MULTI-G) | 0.5 | 1 |
| qwen14b | loose | formal | 98 | +0.000 | +0.2000 | MULTI-G lower weighted tardiness on the 4 differing item(s) (2 lower for SINGLE+G, 2 lower for MULTI-G) | 0.875 | 1 |
| qwen27b | tight | formal | 98 | +0.000 | -0.6667 | SINGLE+G lower weighted tardiness on the 3 differing item(s) (2 lower for SINGLE+G, 1 lower for MULTI-G) | 0.5 | 1 |
| qwen27b | loose | formal | 98 | +0.000 | - | identical weighted tardiness on every item | 1 | 1 |
| openai | tight | formal | 98 | +0.000 | -1.0000 | SINGLE+G lower weighted tardiness on the 2 differing item(s) (2 lower for SINGLE+G, 0 lower for MULTI-G) | 0.5 | 1 |
| openai | loose | formal | 98 | +0.000 | -1.0000 | SINGLE+G lower weighted tardiness on the 2 differing item(s) (2 lower for SINGLE+G, 0 lower for MULTI-G) | 0.5 | 1 |
| deepseek | tight | formal | 98 | +0.000 | -1.0000 | SINGLE+G lower weighted tardiness on the 1 differing item(s) (1 lower for SINGLE+G, 0 lower for MULTI-G) | 1 | 1 |
| deepseek | loose | formal | 98 | +0.000 | -1.0000 | SINGLE+G lower weighted tardiness on the 2 differing item(s) (2 lower for SINGLE+G, 0 lower for MULTI-G) | 0.5 | 1 |
| sonnet | tight | formal | 98 | +0.000 | -1.0000 | SINGLE+G lower weighted tardiness on the 4 differing item(s) (4 lower for SINGLE+G, 0 lower for MULTI-G) | 0.125 | 1 |
| sonnet | loose | formal | 98 | +0.000 | -1.0000 | SINGLE+G lower weighted tardiness on the 1 differing item(s) (1 lower for SINGLE+G, 0 lower for MULTI-G) | 1 | 1 |
| opus | tight | formal | 98 | +0.000 | +0.0000 | MULTI-G lower weighted tardiness on the 3 differing item(s) (2 lower for SINGLE+G, 1 lower for MULTI-G) | 1 | 1 |
| opus | loose | formal | 98 | +0.000 | +1.0000 | MULTI-G lower weighted tardiness on the 1 differing item(s) (0 lower for SINGLE+G, 1 lower for MULTI-G) | 1 | 1 |
| qwen14b | tight | terse | 73 | +0.000 | -1.0000 | SINGLE+G lower weighted tardiness on the 4 differing item(s) (4 lower for SINGLE+G, 0 lower for MULTI-G) | 0.125 | 1 |
| qwen14b | loose | terse | 73 | +0.000 | -1.0000 | SINGLE+G lower weighted tardiness on the 5 differing item(s) (5 lower for SINGLE+G, 0 lower for MULTI-G) | 0.0625 | 0.75 |
| qwen27b | tight | terse | 73 | +0.000 | -0.7143 | SINGLE+G lower weighted tardiness on the 6 differing item(s) (5 lower for SINGLE+G, 1 lower for MULTI-G) | 0.1562 | 1 |
| qwen27b | loose | terse | 73 | +0.000 | - | identical weighted tardiness on every item | 1 | 1 |
| openai | tight | terse | 73 | +0.000 | -0.3333 | SINGLE+G lower weighted tardiness on the 6 differing item(s) (4 lower for SINGLE+G, 2 lower for MULTI-G) | 0.5938 | 1 |
| openai | loose | terse | 73 | +0.000 | -1.0000 | SINGLE+G lower weighted tardiness on the 1 differing item(s) (1 lower for SINGLE+G, 0 lower for MULTI-G) | 1 | 1 |
| deepseek | tight | terse | 73 | +0.000 | - | identical weighted tardiness on every item | 1 | 1 |
| deepseek | loose | terse | 73 | +0.000 | +0.3333 | MULTI-G lower weighted tardiness on the 2 differing item(s) (1 lower for SINGLE+G, 1 lower for MULTI-G) | 1 | 1 |
| sonnet | tight | terse | 73 | +0.000 | -1.0000 | SINGLE+G lower weighted tardiness on the 5 differing item(s) (5 lower for SINGLE+G, 0 lower for MULTI-G) | 0.0625 | 0.75 |
| sonnet | loose | terse | 73 | +0.000 | -1.0000 | SINGLE+G lower weighted tardiness on the 2 differing item(s) (2 lower for SINGLE+G, 0 lower for MULTI-G) | 0.5 | 1 |
| opus | tight | terse | 73 | +0.000 | -0.7143 | SINGLE+G lower weighted tardiness on the 6 differing item(s) (5 lower for SINGLE+G, 1 lower for MULTI-G) | 0.1562 | 1 |
| opus | loose | terse | 73 | +0.000 | - | identical weighted tardiness on every item | 1 | 1 |
| qwen14b | tight | conversational | 69 | +0.000 | +1.0000 | MULTI-G lower weighted tardiness on the 3 differing item(s) (0 lower for SINGLE+G, 3 lower for MULTI-G) | 0.25 | 1 |
| qwen14b | loose | conversational | 69 | +0.000 | -0.4000 | SINGLE+G lower weighted tardiness on the 5 differing item(s) (3 lower for SINGLE+G, 2 lower for MULTI-G) | 0.5 | 1 |
| qwen27b | tight | conversational | 69 | +0.000 | +0.8095 | MULTI-G lower weighted tardiness on the 6 differing item(s) (1 lower for SINGLE+G, 5 lower for MULTI-G) | 0.09375 | 1 |
| qwen27b | loose | conversational | 69 | +0.000 | -1.0000 | SINGLE+G lower weighted tardiness on the 1 differing item(s) (1 lower for SINGLE+G, 0 lower for MULTI-G) | 1 | 1 |
| openai | tight | conversational | 69 | +0.000 | +1.0000 | MULTI-G lower weighted tardiness on the 8 differing item(s) (0 lower for SINGLE+G, 8 lower for MULTI-G) | 0.007812 | 0.09375 |
| openai | loose | conversational | 69 | +0.000 | -0.3333 | SINGLE+G lower weighted tardiness on the 3 differing item(s) (2 lower for SINGLE+G, 1 lower for MULTI-G) | 0.75 | 1 |
| deepseek | tight | conversational | 69 | +0.000 | +1.0000 | MULTI-G lower weighted tardiness on the 1 differing item(s) (0 lower for SINGLE+G, 1 lower for MULTI-G) | 1 | 1 |
| deepseek | loose | conversational | 69 | +0.000 | +0.8667 | MULTI-G lower weighted tardiness on the 5 differing item(s) (1 lower for SINGLE+G, 4 lower for MULTI-G) | 0.125 | 1 |
| sonnet | tight | conversational | 69 | +0.000 | +0.1429 | MULTI-G lower weighted tardiness on the 6 differing item(s) (2 lower for SINGLE+G, 4 lower for MULTI-G) | 0.8438 | 1 |
| sonnet | loose | conversational | 69 | +0.000 | +0.0000 | MULTI-G lower weighted tardiness on the 3 differing item(s) (1 lower for SINGLE+G, 2 lower for MULTI-G) | 1 | 1 |
| opus | tight | conversational | 69 | +0.000 | +0.7333 | MULTI-G lower weighted tardiness on the 5 differing item(s) (1 lower for SINGLE+G, 4 lower for MULTI-G) | 0.1875 | 1 |
| opus | loose | conversational | 69 | +0.000 | - | identical weighted tardiness on every item | 1 | 1 |

