# E13. E3 actual cost, reconciled against the run metas

<!-- generated 2026-08-17 17:51:50 +0800 by e3_analyze.py (l1-e3-analysis-1) -->
<!-- E3 dedup rule: last row per (arm, budget_level, pipeline, repeat, item_id); earlier rows are superseded attempts -->
<!-- suite suite.jsonl sha256 0a0b471f4d04ba035dd12388c919c75a9b7aee6db52bf153f6295f185530908a -->
<!-- adjustment schema sha256 1115fa83d8910ed18a4fa1a421e80aaf4629f4c91fc22f83c81ba32c3fa39321 -->
<!-- E3 slice E3-240 sha256 84b24f0232754344a4c16bcbe9e697b12aef9c707661a365c111424ee861e3e5 (240 items) -->
<!-- guard configurations: UNGUARDED b932b4a480c187968da8445242479be77d62341b7f35753f9cba7fdc3500dc89, G_FEAS 6176c8978a84adf727594d2a7a574dad6e03628e1d3cdddefbf76cfa79122390, G_CERT 52c094406252bf1ab57350d1ec4f9165f8bc4f7d83df2b99e1fb52356e829a42 -->
<!-- ladder anchors: <project>/analysis/ladder (reconciliation 4208/4208 passed) -->
<!-- <project>/results/e3_qwen14b/trajectories.jsonl sha256 75996f6c940e5732d516d353da7f7a483088916893396becfa070b7e79159d73 -->
<!-- <project>/results/e3_qwen14b/calls.jsonl sha256 1b975a312ce9ed24306d0a7fe69d8f977bb79af682d6ae04a19a3d32341d2cba -->
<!-- <project>/results/e3_replay_qwen14b/verdicts.jsonl sha256 d4a7de38e598b24bbb7e10c5b8c745b29fa547a158005962f65f99a9209d290a -->
<!-- <project>/results/e3_replay_qwen14b/summary.json sha256 5db2ae0bb56ffb3cd22822db4e1535aec85967dda806639384344e9898153d5f -->
<!-- <project>/results/e3_qwen27b/trajectories.jsonl sha256 c6a03147f7d1cd9f5f92e38ebb329b0bc558a2d089bf49bda32a6693ca1e6f8f -->
<!-- <project>/results/e3_qwen27b/calls.jsonl sha256 966faf1abe0557ff7b5c6d3b42e9396e9689235a8dbd15f47e036961978bb3c7 -->
<!-- <project>/results/e3_replay_qwen27b/verdicts.jsonl sha256 c932d3122723f50857c1ce4f78de3ac983a936df1e69e6b316fb0f458667aca6 -->
<!-- <project>/results/e3_replay_qwen27b/summary.json sha256 857e61c9e8cb14d8b1bd2b391da3a187e9917d2b47c10839898994a8779622ee -->
<!-- <project>/results/e3_openai/trajectories.jsonl sha256 b8ce912fe2bcb1eca2340e150ec38946b3fd27ce6cd7a543dfa653fd8d99a89c -->
<!-- <project>/results/e3_openai/calls.jsonl sha256 d77aca570ce5a50376931a1ae0d35fff1ed3fea87895e83b6c3a7ef8604f1136 -->
<!-- <project>/results/e3_replay_openai/verdicts.jsonl sha256 168a8b20626a3b70ea16308f7a56af95abe146da4e5607fdb3d3b6f36692dfee -->
<!-- <project>/results/e3_replay_openai/summary.json sha256 ce1e2d5d91be629bf059f7d3c8e0efb53b698f89a07ace4fd5eb397b459fe62f -->
<!-- <project>/results/e3_deepseek/trajectories.jsonl sha256 fd95a9e6caca201f58f4fb27e4d665d46664d7aa5987e6254d5f9fcde95dbeca -->
<!-- <project>/results/e3_deepseek/calls.jsonl sha256 e27dd7d19e9b1613dab14d2b85bc49c97b3471e52d4880f3e6ab8367e230b7c5 -->
<!-- <project>/results/e3_replay_deepseek/verdicts.jsonl sha256 8e42a2c7a2730cee28e6de7aba54b4f96f88c87a712eb5a95c83fb8549106d4b -->
<!-- <project>/results/e3_replay_deepseek/summary.json sha256 71a18e38480b7f4c69cf1a64175231c5224f8361300d2f0f77b35a9f3c5b13a9 -->
<!-- <project>/results/e3_sonnet/trajectories.jsonl sha256 3343dc4737fa2630ce32c582a8dacc606f5fc9bb941cb7431d923d08f50dc7c4 -->
<!-- <project>/results/e3_sonnet/calls.jsonl sha256 951b14ebefb47a1fe40b4caffab1c97f397551ff4d921e9e4e00f47678c87753 -->
<!-- <project>/results/e3_replay_sonnet/verdicts.jsonl sha256 8784318b09fb75599bb1d562cf156c3838b407833647fe82712e333b3d46ca36 -->
<!-- <project>/results/e3_replay_sonnet/summary.json sha256 220adec6a82e3698c5d713681dd05f902ad4f943fd1fc8147ce427e8b319e7ed -->
<!-- <project>/results/e3_opus/trajectories.jsonl sha256 ad125d716133164b3487648128b0448486b548bafc29d84e9a4c19ac186eac96 -->
<!-- <project>/results/e3_opus/calls.jsonl sha256 9e0d0e5ec13594ddb69278766aaadcff2d0e89dfb1c7bc78e422bac1a019ade6 -->
<!-- <project>/results/e3_replay_opus/verdicts.jsonl sha256 9af87fa798a1aede09a82db34cadee9455d6d20b65302c16f0a4ac89b2453a17 -->
<!-- <project>/results/e3_replay_opus/summary.json sha256 c4ee48fb4393dcaff42794cf3b16690777bf827faed96f0df60a48b823ccc2f1 -->
<!-- every verdict is recomputed from the trajectory log with e3_replay's own evaluation path and asserted equal to results/e3_replay_*; no number is adjusted to make an assertion pass -->

Every call E3 billed, priced with `grid_e1_hosted.call_usd` at each arm's pinned price base, and reconciled against the session tallies each run meta printed. The call log carries superseded attempts and the resume sessions, so the recomputation sums over every logged call and the run-meta figure sums over every session; the two must agree to floating-point rounding, and `usd_delta` is that residual.

The two local arms cost electricity only and carry an explicit zero base rather than a blank.

| arm | scope | calls | all-tokens | USD (recomputed) | USD (run metas) | residual | price base |
|---|---|---|---|---|---|---|---|
| qwen14b | grid | 6280 | 11008108 | 0.000000 | 0.000000 | 0.00e+00 | local (electricity only) |
| qwen14b | calibration | 165 | 332023 | 0.000000 | 0.000000 | 0.00e+00 | local (electricity only) |
| qwen27b | grid | 2617 | 4588926 | 0.000000 | 0.000000 | 0.00e+00 | local (electricity only) |
| qwen27b | calibration | 137 | 258075 | 0.000000 | 0.000000 | 0.00e+00 | local (electricity only) |
| openai | grid | 2720 | 4398628 | 3.189965 | 3.189965 | -7.99e-15 | list |
| openai | calibration | 154 | 262672 | 0.187876 | 0.187876 | 8.33e-17 | list |
| deepseek | grid | 4388 | 6011211 | 0.634164 | 0.634164 | -1.11e-15 | list |
| deepseek | calibration | 213 | 314172 | 0.054059 | 0.054059 | -4.86e-17 | list |
| sonnet | grid | 2902 | 6615495 | 10.041007 | 10.041007 | -5.33e-15 | intro (through 2026-08-31) |
| sonnet | calibration | 169 | 394906 | 0.830226 | 0.830226 | 6.66e-16 | intro (through 2026-08-31) |
| opus | grid | 3425 | 7649762 | 24.525800 | 24.525800 | -3.55e-15 | list |
| opus | calibration | 183 | 427297 | 2.197781 | 2.197782 | -1.33e-15 | list |
| ALL | grid + calibration | 23353 | 42261275 | 41.660879 | 41.660879 | -1.42e-14 |  |

