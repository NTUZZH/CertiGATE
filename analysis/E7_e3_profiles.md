# E7. E3 trustworthiness profiles per arm x budget level x variant

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

The Section 5.4 trustworthiness profile of every E3 cell: one row per arm x budget level x guard variant, with end-task quality, all-token cost, wall time, the cap-binding share and the loop metric beside it.

`SINGLE-UG *` is not one of the freeze's three configurations. It is the same truncation of the same log that MULTI-UG is, it costs nothing, and it completes the 2x2.

An empty operations list is a **referral** here, which is the frozen prompt's own refusal signal, and it outranks the guard's reading of it. E1 and the ladder count the same empty list as an applied proposal that changes nothing, so the two terminal-state distributions are not interchangeable.

`n_model_refused` is zero in every cell: no vendor refusal ever landed on a first final. Intermediate free-text stages were refused (`vendor_refused_calls`), and those trajectories still produced a final, so the refusals are reported as a cost on the pipeline rather than as a terminal state.

`all_tokens_*` is the whole trajectory including the guarded revision tail, which is the quantity the accepted replay summarises and the quantity the budget governor capped. `variant_tokens_*` charges each variant only the calls it consumes, so an unguarded variant is not billed for a revision it never makes.

Wall time was measured with six trajectories in flight per arm, so it is a throughput figure and not a single-stream latency measurement.

### Profile at the tight budget

| arm | variant | n | applied+cert | applied uncert | referred | blocked correct | blocked false | warranted | violation pass-through | cert gap median | mean WWT vs RULE | median variant tokens | cap binds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen14b | SINGLE+G | 480 | 35.6% | 0.0% | 50.6% | 12.7% | 1.0% | 99.0% | 25.0% | 0.017 | +0.71 | 3005 | 57.1% |
| qwen14b | MULTI-G | 480 | 1.9% | 0.0% | 97.9% | 0.0% | 0.2% | 99.8% | 2.1% | 0.004 | +0.00 | 3646 | 100.0% |
| qwen14b | MULTI-UG | 480 | 0.0% | 2.1% | 97.9% | 0.0% | 0.0% | 97.9% | 2.1% | - | +0.31 | 3646 | 100.0% |
| qwen14b | SINGLE-UG * | 480 | 0.0% | 45.0% | 50.2% | 0.0% | 0.0% | 50.2% | 39.2% | - | +37.85 | 3000 | 57.1% |
| qwen27b | SINGLE+G | 240 | 38.8% | 0.0% | 52.9% | 7.1% | 1.2% | 98.8% | 29.2% | 0.010 | -0.15 | 2932 | 52.5% |
| qwen27b | MULTI-G | 240 | 0.0% | 0.0% | 100.0% | 0.0% | 0.0% | 100.0% | 0.0% | - | +0.00 | 2838 | 100.0% |
| qwen27b | MULTI-UG | 240 | 0.0% | 0.0% | 100.0% | 0.0% | 0.0% | 100.0% | 0.0% | - | +0.00 | 2838 | 100.0% |
| qwen27b | SINGLE-UG * | 240 | 0.0% | 41.2% | 52.9% | 0.0% | 0.0% | 52.9% | 33.3% | - | +12.37 | 2932 | 52.5% |
| openai | SINGLE+G | 240 | 57.9% | 0.0% | 21.7% | 17.9% | 2.5% | 97.5% | 45.8% | 0.011 | +1.92 | 3009 | 35.0% |
| openai | MULTI-G | 240 | 2.9% | 0.0% | 92.1% | 5.0% | 0.0% | 100.0% | 4.2% | 0.000 | +0.00 | 2540 | 100.0% |
| openai | MULTI-UG | 240 | 0.0% | 3.3% | 92.1% | 0.0% | 0.0% | 92.1% | 4.9% | - | +1.95 | 2540 | 100.0% |
| openai | SINGLE-UG * | 240 | 0.0% | 67.1% | 20.4% | 0.0% | 0.0% | 20.4% | 60.4% | - | +35.45 | 2994 | 35.0% |
| deepseek | SINGLE+G | 240 | 6.7% | 0.0% | 85.8% | 4.6% | 2.9% | 97.1% | 4.9% | 0.003 | -0.00 | 3410 | 72.9% |
| deepseek | MULTI-G | 240 | 0.0% | 0.0% | 99.6% | 0.0% | 0.4% | 99.6% | 0.0% | - | +0.00 | 3408 | 100.0% |
| deepseek | MULTI-UG | 240 | 0.0% | 0.0% | 99.6% | 0.0% | 0.0% | 99.6% | 0.0% | - | +0.00 | 3408 | 100.0% |
| deepseek | SINGLE-UG * | 240 | 0.0% | 0.0% | 93.8% | 0.0% | 0.0% | 93.8% | 0.0% | - | +0.00 | 3304 | 72.9% |
| sonnet | SINGLE+G | 240 | 51.7% | 0.0% | 36.2% | 11.2% | 0.8% | 99.2% | 34.0% | 0.012 | +0.17 | 5022 | 39.2% |
| sonnet | MULTI-G | 240 | 20.4% | 0.0% | 73.3% | 4.2% | 2.1% | 97.9% | 18.1% | 0.009 | +0.14 | 3913 | 100.0% |
| sonnet | MULTI-UG | 240 | 0.0% | 21.7% | 73.3% | 0.0% | 0.0% | 73.3% | 20.1% | - | +14.51 | 3913 | 100.0% |
| sonnet | SINGLE-UG * | 240 | 0.0% | 60.0% | 36.2% | 0.0% | 0.0% | 36.2% | 47.2% | - | +33.57 | 5022 | 39.2% |
| opus | SINGLE+G | 240 | 55.0% | 0.0% | 30.4% | 12.9% | 1.7% | 98.3% | 33.3% | 0.010 | +0.32 | 5936 | 41.2% |
| opus | MULTI-G | 240 | 12.5% | 0.0% | 85.8% | 1.2% | 0.4% | 99.6% | 9.7% | 0.009 | +0.01 | 5200 | 100.0% |
| opus | MULTI-UG | 240 | 0.0% | 12.9% | 85.8% | 0.0% | 0.0% | 85.8% | 10.4% | - | +1.79 | 5200 | 100.0% |
| opus | SINGLE-UG * | 240 | 0.0% | 65.4% | 30.4% | 0.0% | 0.0% | 30.4% | 50.0% | - | +37.62 | 5936 | 41.2% |

#### Cost, latency and the loop at the tight budget

| arm | variant | ceiling | median all-tokens | median variant tokens | p90 variant tokens | USD (variant) | median wall s | mean calls | proposals per accepted adjustment | trajectories that revised | get_state / preview_dispatch |
|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen14b | SINGLE+G | 4500 | 3005 | 3005 | 4088 | 0.000 | 2.17 | 2.05 | 2.82 | 2 | 74 / 317 |
| qwen14b | MULTI-G | 4500 | 3646 | 3646 | 4425 | 0.000 | 5.78 | 2.30 | 53.33 | 0 | 29 / 488 |
| qwen14b | MULTI-UG | 4500 | 3646 | 3646 | 4425 | 0.000 | 5.78 | 2.30 | - | 0 | 29 / 488 |
| qwen14b | SINGLE-UG * | 4500 | 3005 | 3000 | 4070 | 0.000 | 2.17 | 2.05 | - | 0 | 74 / 317 |
| qwen27b | SINGLE+G | 3500 | 2932 | 2932 | 3090 | 0.000 | 3.44 | 1.68 | 2.58 | 0 | 42 / 19 |
| qwen27b | MULTI-G | 3500 | 2838 | 2838 | 3081 | 0.000 | 10.03 | 1.70 | - | 0 | 27 / 49 |
| qwen27b | MULTI-UG | 3500 | 2838 | 2838 | 3081 | 0.000 | 10.03 | 1.70 | - | 0 | 27 / 49 |
| qwen27b | SINGLE-UG * | 3500 | 2932 | 2932 | 3090 | 0.000 | 3.44 | 1.68 | - | 0 | 42 / 19 |
| openai | SINGLE+G | 4500 | 3009 | 3009 | 4195 | 0.593 | 2.26 | 2.14 | 1.75 | 3 | 4 / 99 |
| openai | MULTI-G | 4500 | 2540 | 2540 | 3753 | 0.683 | 3.27 | 2.08 | 34.29 | 0 | 0 / 0 |
| openai | MULTI-UG | 4500 | 2540 | 2540 | 3753 | 0.683 | 3.27 | 2.08 | - | 0 | 0 / 0 |
| openai | SINGLE-UG * | 4500 | 3009 | 2994 | 4195 | 0.589 | 2.26 | 2.14 | - | 0 | 4 / 99 |
| deepseek | SINGLE+G | 5000 | 3410 | 3410 | 4152 | 0.111 | 4.15 | 2.71 | 17.00 | 32 | 172 / 45 |
| deepseek | MULTI-G | 5000 | 3408 | 3408 | 4043 | 0.169 | 7.52 | 2.77 | - | 0 | 124 / 64 |
| deepseek | MULTI-UG | 5000 | 3408 | 3408 | 4043 | 0.169 | 7.52 | 2.77 | - | 0 | 124 / 64 |
| deepseek | SINGLE-UG * | 5000 | 3410 | 3304 | 4152 | 0.107 | 4.15 | 2.71 | - | 0 | 172 / 45 |
| sonnet | SINGLE+G | 6000 | 5022 | 5022 | 6117 | 2.800 | 7.25 | 2.48 | 1.94 | 0 | 72 / 159 |
| sonnet | MULTI-G | 6000 | 3913 | 3913 | 6474 | 2.333 | 12.37 | 2.43 | 4.90 | 0 | 11 / 13 |
| sonnet | MULTI-UG | 6000 | 3913 | 3913 | 6474 | 2.333 | 12.37 | 2.43 | - | 0 | 11 / 13 |
| sonnet | SINGLE-UG * | 6000 | 5022 | 5022 | 6117 | 2.800 | 7.25 | 2.48 | - | 0 | 72 / 159 |
| opus | SINGLE+G | 6500 | 5936 | 5936 | 6841 | 7.795 | 10.82 | 2.80 | 1.82 | 0 | 57 / 321 |
| opus | MULTI-G | 6500 | 5200 | 5200 | 6421 | 4.730 | 14.06 | 2.86 | 8.00 | 0 | 14 / 229 |
| opus | MULTI-UG | 6500 | 5200 | 5200 | 6421 | 4.730 | 14.06 | 2.86 | - | 0 | 14 / 229 |
| opus | SINGLE-UG * | 6500 | 5936 | 5936 | 6841 | 7.795 | 10.82 | 2.80 | - | 0 | 57 / 321 |

### Profile at the loose budget

| arm | variant | n | applied+cert | applied uncert | referred | blocked correct | blocked false | warranted | violation pass-through | cert gap median | mean WWT vs RULE | median variant tokens | cap binds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen14b | SINGLE+G | 480 | 66.2% | 0.0% | 31.7% | 1.7% | 0.4% | 99.6% | 47.2% | 0.010 | +0.78 | 4434 | 3.8% |
| qwen14b | MULTI-G | 480 | 70.0% | 0.0% | 28.5% | 1.0% | 0.4% | 99.6% | 55.9% | 0.005 | +2.62 | 10284 | 4.2% |
| qwen14b | MULTI-UG | 480 | 0.0% | 81.7% | 9.4% | 0.0% | 0.0% | 9.4% | 73.6% | - | +41.83 | 9986 | 4.2% |
| qwen14b | SINGLE-UG * | 480 | 0.0% | 78.3% | 15.0% | 0.0% | 0.0% | 15.0% | 66.0% | - | +42.23 | 3954 | 3.8% |
| qwen27b | SINGLE+G | 240 | 69.2% | 0.0% | 26.2% | 3.3% | 1.2% | 98.8% | 51.4% | 0.008 | +2.09 | 3704 | 5.8% |
| qwen27b | MULTI-G | 240 | 66.2% | 0.0% | 25.4% | 6.2% | 2.1% | 97.9% | 50.0% | 0.008 | +2.82 | 9698 | 13.3% |
| qwen27b | MULTI-UG | 240 | 0.0% | 73.8% | 20.4% | 0.0% | 0.0% | 20.4% | 62.5% | - | +39.61 | 8526 | 13.3% |
| qwen27b | SINGLE-UG * | 240 | 0.0% | 75.8% | 17.5% | 0.0% | 0.0% | 17.5% | 62.5% | - | +37.99 | 3157 | 5.8% |
| openai | SINGLE+G | 240 | 76.7% | 0.0% | 21.2% | 1.7% | 0.4% | 99.6% | 61.8% | 0.008 | +3.23 | 3660 | 2.9% |
| openai | MULTI-G | 240 | 77.1% | 0.0% | 19.6% | 2.9% | 0.4% | 99.6% | 63.2% | 0.009 | +4.62 | 6702 | 4.6% |
| openai | MULTI-UG | 240 | 0.0% | 84.6% | 4.6% | 0.0% | 0.0% | 4.6% | 75.0% | - | +42.70 | 6430 | 4.6% |
| openai | SINGLE-UG * | 240 | 0.0% | 83.3% | 7.1% | 0.0% | 0.0% | 7.1% | 72.2% | - | +48.02 | 3486 | 2.9% |
| deepseek | SINGLE+G | 240 | 43.8% | 0.0% | 54.6% | 1.7% | 0.0% | 100.0% | 27.1% | 0.010 | +0.23 | 5036 | 24.6% |
| deepseek | MULTI-G | 240 | 50.4% | 0.0% | 49.2% | 0.4% | 0.0% | 100.0% | 36.1% | 0.012 | +0.03 | 8519 | 16.7% |
| deepseek | MULTI-UG | 240 | 0.0% | 0.0% | 100.0% | 0.0% | 0.0% | 100.0% | 0.0% | - | +0.00 | 6332 | 16.7% |
| deepseek | SINGLE-UG * | 240 | 0.0% | 0.0% | 100.0% | 0.0% | 0.0% | 100.0% | 0.0% | - | +0.00 | 3398 | 24.6% |
| sonnet | SINGLE+G | 240 | 68.3% | 0.0% | 30.4% | 1.2% | 0.0% | 100.0% | 47.9% | 0.005 | +0.17 | 5866 | 2.1% |
| sonnet | MULTI-G | 240 | 65.0% | 0.0% | 33.3% | 1.7% | 0.0% | 100.0% | 43.8% | 0.008 | +0.35 | 10316 | 2.9% |
| sonnet | MULTI-UG | 240 | 0.0% | 73.8% | 23.8% | 0.0% | 0.0% | 23.8% | 58.3% | - | +40.82 | 10049 | 2.9% |
| sonnet | SINGLE-UG * | 240 | 0.0% | 75.4% | 21.7% | 0.0% | 0.0% | 21.7% | 59.7% | - | +41.60 | 5666 | 2.1% |
| opus | SINGLE+G | 240 | 65.8% | 0.0% | 34.2% | 0.0% | 0.0% | 100.0% | 43.8% | 0.005 | +3.14 | 6238 | 1.7% |
| opus | MULTI-G | 240 | 63.7% | 0.0% | 35.4% | 0.4% | 0.4% | 99.6% | 41.7% | 0.008 | +3.04 | 13247 | 3.3% |
| opus | MULTI-UG | 240 | 0.0% | 70.8% | 25.8% | 0.0% | 0.0% | 25.8% | 54.9% | - | +47.38 | 13029 | 3.3% |
| opus | SINGLE-UG * | 240 | 0.0% | 73.3% | 22.9% | 0.0% | 0.0% | 22.9% | 57.6% | - | +48.01 | 6093 | 1.7% |

#### Cost, latency and the loop at the loose budget

| arm | variant | ceiling | median all-tokens | median variant tokens | p90 variant tokens | USD (variant) | median wall s | mean calls | proposals per accepted adjustment | trajectories that revised | get_state / preview_dispatch |
|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen14b | SINGLE+G | 18000 | 4434 | 4434 | 6932 | 0.000 | 2.62 | 2.80 | 1.97 | 92 | 73 / 330 |
| qwen14b | MULTI-G | 18000 | 10284 | 10284 | 14400 | 0.000 | 11.05 | 5.93 | 1.82 | 107 | 29 / 791 |
| qwen14b | MULTI-UG | 18000 | 10284 | 9986 | 13134 | 0.000 | 11.05 | 5.93 | - | 0 | 29 / 791 |
| qwen14b | SINGLE-UG * | 18000 | 4434 | 3954 | 6302 | 0.000 | 2.62 | 2.80 | - | 0 | 73 / 330 |
| qwen27b | SINGLE+G | 14000 | 3704 | 3704 | 6320 | 0.000 | 4.80 | 2.48 | 1.94 | 41 | 40 / 22 |
| qwen27b | MULTI-G | 14000 | 9698 | 9698 | 13344 | 0.000 | 20.84 | 5.05 | 1.81 | 26 | 33 / 194 |
| qwen27b | MULTI-UG | 14000 | 9698 | 8526 | 12916 | 0.000 | 20.84 | 5.05 | - | 0 | 33 / 194 |
| qwen27b | SINGLE-UG * | 14000 | 3704 | 3157 | 4893 | 0.000 | 4.80 | 2.48 | - | 0 | 40 / 22 |
| openai | SINGLE+G | 18000 | 3660 | 3660 | 5909 | 0.634 | 2.82 | 2.67 | 1.80 | 49 | 5 / 102 |
| openai | MULTI-G | 18000 | 6702 | 6702 | 10210 | 1.269 | 5.76 | 4.38 | 1.79 | 54 | 0 / 0 |
| openai | MULTI-UG | 18000 | 6702 | 6430 | 7952 | 1.194 | 5.76 | 4.38 | - | 0 | 0 / 0 |
| openai | SINGLE-UG * | 18000 | 3660 | 3486 | 4414 | 0.561 | 2.82 | 2.67 | - | 0 | 5 / 102 |
| deepseek | SINGLE+G | 20000 | 5036 | 5036 | 18951 | 0.106 | 7.43 | 5.93 | 9.55 | 187 | 175 / 44 |
| deepseek | MULTI-G | 20000 | 8519 | 8519 | 18237 | 0.248 | 13.51 | 6.87 | 6.15 | 186 | 122 / 66 |
| deepseek | MULTI-UG | 20000 | 8519 | 6332 | 8438 | 0.204 | 13.51 | 6.87 | - | 0 | 122 / 66 |
| deepseek | SINGLE-UG * | 20000 | 5036 | 3398 | 4333 | 0.045 | 7.43 | 5.93 | - | 0 | 175 / 44 |
| sonnet | SINGLE+G | 24000 | 5866 | 5866 | 8917 | 1.699 | 8.59 | 2.88 | 1.82 | 36 | 71 / 155 |
| sonnet | MULTI-G | 24000 | 10316 | 10316 | 14545 | 3.209 | 17.93 | 4.30 | 1.84 | 34 | 13 / 12 |
| sonnet | MULTI-UG | 24000 | 10316 | 10049 | 11757 | 3.143 | 17.93 | 4.30 | - | 0 | 13 / 12 |
| sonnet | SINGLE-UG * | 24000 | 5866 | 5666 | 6821 | 1.615 | 8.59 | 2.88 | - | 0 | 71 / 155 |
| opus | SINGLE+G | 26000 | 6238 | 6238 | 10309 | 3.647 | 11.63 | 3.17 | 1.91 | 42 | 55 / 329 |
| opus | MULTI-G | 26000 | 13247 | 13247 | 18168 | 8.290 | 24.62 | 5.37 | 1.92 | 39 | 15 / 266 |
| opus | MULTI-UG | 26000 | 13247 | 13029 | 15898 | 8.106 | 24.62 | 5.37 | - | 0 | 15 / 266 |
| opus | SINGLE-UG * | 26000 | 6238 | 6093 | 7176 | 3.441 | 11.63 | 3.17 | - | 0 | 55 / 329 |

